"""The agent: model, prompt, tools and subagents. MDA finds everything else by file name.

Docs:
- https://docs.langchain.com/langsmith/python/managed-deep-agents-agent-definition
- https://docs.langchain.com/langsmith/python/managed-deep-agents-subagents
"""

import os
from pathlib import Path

from managed_deepagents import ManagedServerRuntime, define_deep_agent

from dreaming import DREAMING
from heartbeat import HEARTBEAT
from middleware.per_user_schedules import PerUserSchedulesMiddleware
from slack_conversation import install
from tools.reset import clear_me
from tools.schedules import cancel_schedule, list_schedules, schedule

# Read at import: the async factory can't block on file reads.
HERE = Path(__file__).parent
INSTRUCTIONS = (HERE / "instructions.md").read_text().strip()


async def agent(runtime: ManagedServerRuntime):
    install()
    return define_deep_agent(
        # mda reads the name and the subagents' name/async without running this file.
        name="persistent-agent",
        # LLM Gateway by default, so LANGSMITH_API_KEY is the only key.
        model=os.environ.get("AGENT_MODEL", "langsmith:anthropic/claude-opus-5-5"),
        instructions=INSTRUCTIONS,
        # Every person gets these, created on their DM, as them.
        middleware=[PerUserSchedulesMiddleware(schedules=[HEARTBEAT, DREAMING])],
        tools=[
            schedule,
            list_schedules,
            cancel_schedule,
            clear_me,
        ],
        subagents=[
            {
                "name": "clone",
                "description": "A copy of you that starts with this conversation.",
                "system_prompt": INSTRUCTIONS,
                "async": True,
                "mode": "fork",
            },
            {
                "name": "researcher",
                "description": "Investigates one question in depth: connected tools, the web, the browser.",
                "system_prompt": "Answer the question you are given. Check sources rather than guessing, and cite them.",
                "async": True,
            },
            {
                "name": "reviewer",
                "description": "Reviews a draft, plan or change with fresh eyes before it goes out.",
                "system_prompt": "Find what is wrong, missing or unsupported in what you are given. Cite evidence.",
                "async": True,
            },
        ],
    )
