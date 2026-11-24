"""Reset personal schedules and memory using the pinned MDA runtime's private API."""

from importlib import import_module

from langchain.tools import tool
from managed_deepagents import ManagedDeepAgentRuntime
from managed_deepagents._memory.user_memory import UserMemoryBackend

from tools.owner import owner, private


def _user_memory() -> UserMemoryBackend:
    """Resolve the compiler-owned memory configuration, retaining SDK access checks."""
    entry = import_module("_mda_entry")
    repo = getattr(entry, "_context_repo", None)
    root = getattr(entry, "_context_root", None) if not repo else None
    if not repo and not root:
        raise RuntimeError("Reset requires MDA's compiled memory configuration.")
    return UserMemoryBackend(
        deploy_handle=repo or "local", filesystem_root=root, run_config=None
    )


@tool
async def clear_me(runtime: ManagedDeepAgentRuntime) -> str:
    """For !clear: cancel the current person's schedules and erase their memory."""
    if owner(runtime)["type"] != "user" or not private(runtime):
        return "Only in your authenticated one-on-one DM."
    memory = _user_memory()
    files = await memory.als("/")
    if files.error or files.entries is None:
        raise RuntimeError("Couldn't read personal memory; reset did not complete.")
    count = 0
    while schedules := (
        await runtime.schedules.list(owner={"type": "user"}, limit=100)
    )["items"]:
        for schedule in schedules:
            await runtime.schedules.delete(schedule["id"], owner={"type": "user"})
            count += 1
    for file in files.entries:
        result = await memory.adelete(file["path"])
        if result.error:
            raise RuntimeError(
                "Couldn't delete personal memory; reset did not complete."
            )
    remaining = await _user_memory().als("/")
    if remaining.error or remaining.entries != []:
        raise RuntimeError(
            "Couldn't verify empty personal memory; reset did not complete."
        )
    return f"Cancelled {count} schedules and cleared your personal memory."
