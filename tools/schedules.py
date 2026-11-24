"""Schedules: one tool to follow up later or run something on repeat.

`schedule` covers a one-time follow-up ("check back in 2 hours"), recurring work ("every
Monday at 9"). Goals live in memory and use the separate hourly heartbeat.
Each schedule belongs to the person who asked and runs as them. A one-time follow-up in a
shared channel belongs to the agent instead, so anyone there can see or cancel it.

Docs: https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules
"""

import re
from datetime import datetime, timedelta, timezone

from langchain.tools import tool
from managed_deepagents import ManagedDeepAgentRuntime, ScheduleNotFoundError

from tools.owner import owner, private

_PLAYBOOK = re.compile(r"[a-z0-9][a-z0-9-]*")


@tool
async def schedule(
    task: str,
    runtime: ManagedDeepAgentRuntime,
    in_minutes: int | None = None,
    cron: str | None = None,
    tz: str = "UTC",
    playbook: str | None = None,
) -> str:
    """Run a task later, once or on repeat. Give exactly one of in_minutes or cron.

    task: what to do when it runs, written to stand on its own. Track goals in memory,
        not with a polling schedule per goal.
    in_minutes: run once, this many minutes from now, in this conversation.
    cron: run on repeat (5-field cron, at most hourly); each run starts a new message.
    tz: the person's IANA timezone for cron, such as America/Los_Angeles.
    playbook: for an adopted playbook, its settings file name under
        /memories/user/playbooks/ without .md, such as morning-brief.
    """
    if (in_minutes is None) == (cron is None):
        return "Give exactly one of in_minutes or cron."
    if playbook is not None and (cron is None or not _PLAYBOOK.fullmatch(playbook)):
        return "A playbook needs a cron and a lowercase name like morning-brief."
    if in_minutes is not None:
        # A follow-up in a shared conversation is the agent's; in a DM, the person's.
        item = await runtime.schedules.create(
            owner=owner(runtime) if private(runtime) else {"type": "agent"},
            at=datetime.now(timezone.utc) + timedelta(minutes=in_minutes),
            new_thread=False,
            prompt=task,
        )
    else:
        item = await runtime.schedules.create(
            owner=owner(runtime),
            cron=cron,
            timezone=tz,
            new_thread=True,
            prompt=task,
            metadata={"kind": "playbook", "playbook": playbook} if playbook else {},
        )
    return f"Scheduled {item['id']}."


def _line(schedule: dict) -> str:
    when = schedule.get("cron") or schedule.get("at")
    paused = " (paused)" if schedule["paused"] else ""
    metadata = schedule.get("metadata") or {}
    tag = (
        f" [playbook {metadata.get('playbook')}]"
        if metadata.get("kind") == "playbook"
        else ""
    )
    return f"{schedule['id']} {when}{paused}{tag}: {schedule.get('prompt', '')}"


def _here(schedule: dict, runtime: ManagedDeepAgentRuntime) -> bool:
    """A one-time follow-up the agent owns because it was asked for in this conversation."""
    return (
        bool(schedule.get("at")) and schedule["thread"].get("id") == runtime.thread.id
    )


@tool
async def list_schedules(runtime: ManagedDeepAgentRuntime) -> str:
    """List this person's schedules, or in a shared conversation, its follow-ups."""
    who = owner(runtime)
    if who["type"] == "user" and not private(runtime):
        page = await runtime.schedules.list(owner={"type": "agent"}, limit=100)
        here = [_line(s) for s in page["items"] if _here(s, runtime)]
        return "\n".join(["Their own schedules are private: ask in a DM.", *here])
    items = (await runtime.schedules.list(owner=who, limit=100))["items"]
    lines = [_line(s) for s in items]
    return "\n".join(lines) or "No schedules."


@tool
async def cancel_schedule(schedule_id: str, runtime: ManagedDeepAgentRuntime) -> str:
    """Cancel one of this person's schedules, or a follow-up in this conversation."""
    try:
        await runtime.schedules.delete(schedule_id, owner=owner(runtime))
    except ScheduleNotFoundError:
        agent = {"type": "agent"}
        try:
            found = await runtime.schedules.get(schedule_id, owner=agent)
        except ScheduleNotFoundError:
            return f"No schedule {schedule_id} of yours."
        if not _here(found, runtime):
            return f"No schedule {schedule_id} of yours."
        await runtime.schedules.delete(schedule_id, owner=agent)
    return f"Cancelled {schedule_id}."
