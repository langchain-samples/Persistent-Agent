"""Per-user schedules, created just in time on each person's Slack DM.

`per_user_schedules` is middleware that runs before the model on a person's
one-on-one DM. For each schedule it's given, it makes sure that person has exactly
one, owned by them so it runs with their memory and apps, and that it matches the
code: a redeploy that changes a prompt, cron or timezone reaches everyone on their
next DM. Whether a schedule is paused stays the person's choice. Each person is
checked at most once per `recheck_seconds` in a process, so most DMs cost nothing.

Which schedules every person gets is up to the caller: see agent.py.
"""

import asyncio
import time
from collections.abc import Iterable
from dataclasses import dataclass
from weakref import WeakValueDictionary

from langchain.agents.middleware import AgentMiddleware, AgentState, before_agent
from langgraph.config import get_config
from managed_deepagents import ManagedRuntime, ScheduleNotFoundError

from slack_conversation import continuous_dm, is_trusted_schedule_delivery_run
from tools import owner as ownership

OWNER = {"type": "user"}


@dataclass(frozen=True)
class PersonalSchedule:
    """One schedule every person gets, identified by `key` in its metadata."""

    key: str
    cron: str
    timezone: str
    prompt: str
    new_thread: bool = False


#: When each person was last confirmed up to date, per process.
_VERIFIED: dict[str, float] = {}
_LOCKS: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


def forget(person_id: str) -> None:
    """Check this person again on their next DM, e.g. after `!clear` removed theirs."""
    _VERIFIED.pop(person_id, None)


async def _all(runtime: ManagedRuntime) -> list[dict]:
    """This person's schedules, every page."""
    items, offset = [], 0
    while True:
        page = await runtime.schedules.list(owner=OWNER, limit=100, offset=offset)
        items.extend(page["items"])
        offset = page["next_offset"]
        if offset is None:
            return items


def _changes(schedule: dict, spec: PersonalSchedule) -> dict:
    """What to patch so a schedule matches the code; never its paused state."""
    wanted = {"cron": spec.cron, "timezone": spec.timezone, "prompt": spec.prompt}
    return {key: value for key, value in wanted.items() if schedule.get(key) != value}


async def _ensure(runtime: ManagedRuntime, spec: PersonalSchedule, items: list[dict]):
    """Leave exactly one schedule for `spec`, matching the code."""
    mine = sorted(
        (s for s in items if (s.get("metadata") or {}).get("kind") == spec.key),
        key=lambda s: s["id"],
    )
    keep, duplicates = (mine[0], mine[1:]) if mine else (None, [])
    if keep is not None and keep.get("new_thread", spec.new_thread) != spec.new_thread:
        # new_thread can't be patched: replace the schedule, keeping it paused if it was.
        duplicates, paused = [keep, *duplicates], keep.get("paused", False)
        keep = await _create(runtime, spec, paused=paused)
    elif keep is None:
        keep = await _create(runtime, spec)
    elif patch := _changes(keep, spec):
        await runtime.schedules.update(keep["id"], patch, owner=OWNER)
    for duplicate in duplicates:
        try:
            await runtime.schedules.delete(duplicate["id"], owner=OWNER)
        except ScheduleNotFoundError:
            pass


async def _create(runtime: ManagedRuntime, spec: PersonalSchedule, *, paused=False):
    return await runtime.schedules.create(
        owner=OWNER,
        cron=spec.cron,
        timezone=spec.timezone,
        new_thread=spec.new_thread,
        prompt=spec.prompt,
        metadata={"kind": spec.key},
        paused=paused,
    )


def per_user_schedules(
    specs: Iterable[PersonalSchedule], *, recheck_seconds: float = 3600
) -> AgentMiddleware:
    """Middleware giving each person one of each schedule, from their own DM."""
    specs = tuple(specs)

    @before_agent(name="per_user_schedules")
    async def ensure(state: AgentState, runtime: ManagedRuntime) -> None:
        principal = runtime.server_info.principal if runtime.server_info else None
        if (
            principal is None
            or principal.kind != "person"
            or not ownership.private(runtime)
        ):
            return
        config = get_config()
        if is_trusted_schedule_delivery_run(
            config.get("configurable"), config.get("metadata")
        ):
            return
        thread = ownership.current_run_thread(runtime, config.get("configurable"))
        if not config.get("configurable", {}).get("thread_id") or (
            continuous_dm(thread.origin) is None
        ):
            return
        if time.monotonic() - _VERIFIED.get(principal.id, -recheck_seconds) < (
            recheck_seconds
        ):
            return
        async with _LOCKS.setdefault(principal.id, asyncio.Lock()):
            # Another DM may have finished the check while this one waited.
            if time.monotonic() - _VERIFIED.get(principal.id, -recheck_seconds) < (
                recheck_seconds
            ):
                return
            items = await _all(runtime)
            for spec in specs:
                await _ensure(runtime, spec, items)
            _VERIFIED[principal.id] = time.monotonic()

    return ensure
