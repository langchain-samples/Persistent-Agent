"""Per-user schedules, created just in time on each person's Slack DM."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from weakref import WeakValueDictionary

from langchain.agents.middleware import AgentMiddleware, AgentState
from langgraph.config import get_config
from managed_deepagents import ManagedRuntime, ScheduleNotFoundError
from typing_extensions import override

from slack_conversation import continuous_dm, is_trusted_schedule_delivery_run
from tools import owner as ownership

USER = {"type": "user"}

# One lock per person, so their concurrent DMs set up one at a time instead of both
# creating. Weak: an entry lasts only while a DM holds it. Module-level, so it holds
# however many times the middleware is built.
_LOCKS: WeakValueDictionary[str, asyncio.Lock] = WeakValueDictionary()


@dataclass(frozen=True)
class PersonalSchedule:
    """A schedule every person gets.

    Attributes:
        key: Identifies the schedule; stored as `metadata["kind"]` to find it again.
        cron: Standard 5-field cron expression.
        timezone: IANA timezone the cron runs in.
        prompt: What each run is asked to do.
        new_thread: Start a new thread each run instead of continuing the DM.
    """

    key: str
    cron: str
    timezone: str
    prompt: str
    new_thread: bool = False


class PerUserSchedulesMiddleware(AgentMiddleware):
    """Gives each person their own copy of a set of schedules.

    Before the model runs on a person's one-on-one Slack DM, this middleware makes
    sure they have exactly one of each schedule: it creates any that are missing,
    owned by that person so each run has their memory and apps, and deletes
    duplicates. Existing schedules are otherwise left as they are, including paused
    ones. Channels, group DMs, scheduled runs and runs without a person are skipped.

    Schedules are created just in time because they must run as their person, whose
    identity is only available on that person's own request.

    Async only: the schedules API is async.

    Example:
        ```python
        from managed_deepagents import define_deep_agent

        from middleware.per_user_schedules import (
            PersonalSchedule,
            PerUserSchedulesMiddleware,
        )

        heartbeat = PersonalSchedule("heartbeat", "0 * * * *", "UTC", "Check on goals.")

        agent = define_deep_agent(
            name="assistant",
            middleware=[PerUserSchedulesMiddleware(schedules=[heartbeat])],
        )
        ```
    """

    def __init__(self, *, schedules: Sequence[PersonalSchedule]) -> None:
        """Initialize the per-user schedules middleware.

        Args:
            schedules: The schedules every person gets. Keys must be unique.

        Raises:
            ValueError: If `schedules` is empty or two share a key.
        """
        super().__init__()
        if not schedules:
            msg = "At least one schedule must be specified"
            raise ValueError(msg)
        keys = [schedule.key for schedule in schedules]
        if len(set(keys)) != len(keys):
            msg = f"Schedule keys must be unique, got: {keys}"
            raise ValueError(msg)
        self.schedules = tuple(schedules)

    @override
    async def abefore_agent(
        self, state: AgentState, runtime: ManagedRuntime
    ) -> dict[str, Any] | None:
        """Create this person's missing schedules and remove duplicates.

        Args:
            state: The current agent state. Unused.
            runtime: The managed runtime, for the caller and the schedules API.

        Returns:
            `None`: the agent state is unchanged.
        """
        if (person := _persons_dm(runtime)) is None:
            return None
        async with _LOCKS.setdefault(person, asyncio.Lock()):
            existing = await _list(runtime)
            for schedule in self.schedules:
                await _ensure_one(runtime, schedule, existing)
        return None


def _persons_dm(runtime: ManagedRuntime) -> str | None:
    """The person's ID if this run is them talking in their own DM, else `None`."""
    person = runtime.server_info.principal if runtime.server_info else None
    if person is None or person.kind != "person" or not ownership.private(runtime):
        return None
    config = get_config()
    configurable = config.get("configurable") or {}
    if is_trusted_schedule_delivery_run(configurable, config.get("metadata")):
        return None  # a scheduled run, not the person
    if not configurable.get("thread_id"):
        return None
    origin = ownership.current_run_thread(runtime, configurable).origin
    if continuous_dm(origin) is None:
        return None
    return person.id


async def _list(runtime: ManagedRuntime) -> list[dict]:
    """This person's schedules, every page."""
    items, offset = [], 0
    while offset is not None:
        page = await runtime.schedules.list(owner=USER, limit=100, offset=offset)
        items += page["items"]
        offset = page["next_offset"]
    return items


def _kind(schedule: dict) -> str | None:
    return (schedule.get("metadata") or {}).get("kind")


async def _ensure_one(
    runtime: ManagedRuntime, schedule: PersonalSchedule, existing: list[dict]
) -> None:
    """Create `schedule` if this person has none; delete any duplicates."""
    matches = sorted(
        (s for s in existing if _kind(s) == schedule.key), key=lambda s: s["id"]
    )
    if not matches:
        await runtime.schedules.create(
            owner=USER,
            cron=schedule.cron,
            timezone=schedule.timezone,
            new_thread=schedule.new_thread,
            prompt=schedule.prompt,
            metadata={"kind": schedule.key},
        )
    for duplicate in matches[1:]:  # another process raced us; keep the oldest
        try:
            await runtime.schedules.delete(duplicate["id"], owner=USER)
        except ScheduleNotFoundError:
            pass
