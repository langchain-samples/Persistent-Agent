"""Per-user schedules, created just in time on each person's Slack DM.

`per_user_schedules` is middleware that runs before the model on a person's
one-on-one DM. For each schedule it's given, it makes sure that person has exactly
one, owned by them so it runs with their memory and apps. Existing schedules are
left as they are, including paused ones. Which schedules every person gets is up
to the caller: see agent.py.
"""

import asyncio
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


_LOCKS: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


async def _all(runtime: ManagedRuntime) -> list[dict]:
    """This person's schedules, every page."""
    items, offset = [], 0
    while True:
        page = await runtime.schedules.list(owner=OWNER, limit=100, offset=offset)
        items.extend(page["items"])
        offset = page["next_offset"]
        if offset is None:
            return items


async def _ensure(runtime: ManagedRuntime, spec: PersonalSchedule, items: list[dict]):
    """Leave exactly one schedule for `spec`: create it if missing, drop duplicates."""
    mine = sorted(
        (s for s in items if (s.get("metadata") or {}).get("kind") == spec.key),
        key=lambda s: s["id"],
    )
    if not mine:
        await runtime.schedules.create(
            owner=OWNER,
            cron=spec.cron,
            timezone=spec.timezone,
            new_thread=spec.new_thread,
            prompt=spec.prompt,
            metadata={"kind": spec.key},
        )
    for duplicate in mine[1:]:
        try:
            await runtime.schedules.delete(duplicate["id"], owner=OWNER)
        except ScheduleNotFoundError:
            pass


def per_user_schedules(specs: Iterable[PersonalSchedule]) -> AgentMiddleware:
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
        async with _LOCKS.setdefault(principal.id, asyncio.Lock()):
            items = await _all(runtime)
            for spec in specs:
                await _ensure(runtime, spec, items)

    return ensure
