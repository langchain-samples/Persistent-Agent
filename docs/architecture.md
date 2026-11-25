# How Persistent Agent works

The details behind the [README](../README.md): which mechanism does what, how each person gets
their own assistant, and what to know before changing the Slack integration.

## Which mechanism does what

| Mechanism | Purpose | Where it lives |
|---|---|---|
| **Skill** | How to do a kind of work. | Shared `skills/<name>/SKILL.md`, read when relevant. |
| **Playbook** | A skill for a repeatable job, run once or adopted on a schedule. | A skill whose description starts with "Playbook:". |
| **Playbook settings** | One person's preferences and state for a playbook they adopted. | `/memories/user/playbooks/<name>.md` |
| **Scheduled task** | Recurring work and its timing. | A user-owned MDA schedule; playbook schedules are tagged `playbook=<name>`. |
| **Check-in** | A single later follow-up. | A one-time schedule in the same conversation. |
| **Goal** | An outcome with a finish line. | `/memories/user/goals/<slug>.md` |
| **Heartbeat** | Advances active goals hourly and reports real progress or blockers. | One hourly schedule per person. |
| **Memory buffer** | Dated, attributed notes worth remembering. | `/memories/user/buffer.md`, appended during DM work. |
| **Dreaming** | Consolidates the buffer into long-term memory nightly. | One daily schedule per person. |
| **Background subagent** | Long work now, while the conversation continues. | An async task that reports back. |

For example, "get this meeting booked" becomes a goal advanced by the heartbeat; "brief me every
morning" adopts a playbook with personal settings and a scheduled task; "I prefer five bullets"
becomes a buffered note that dreaming files into memory.

## Everyone's own assistant

- **[Memory](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory)** (`/memories/user/`) loads only in that person's DMs.
- **[Schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules)** run as the person and only they can see or cancel them. Check-ins asked for in a shared channel belong to the agent instead, so anyone there can see or cancel them.
- **Integrations** use the accounts that person connected, and their [browser](https://docs.langchain.com/langsmith/python/managed-deep-agents-browser-use) keeps their logins.

## Heartbeat and dreaming

`PerUserSchedulesMiddleware` (`middleware/per_user_schedules.py`) runs before the model on a
person's DM and makes sure they have exactly one hourly heartbeat and one nightly dreaming
schedule, owned by them. It creates them just in time because they must run as that person,
whose identity is only available on their own request. Existing schedules are left as they are,
including paused ones, and duplicates from concurrent DMs are removed. `heartbeat.py` and
`dreaming.py` hold each schedule's prompt and timing; `agent.py` lists them.

The heartbeat continues the person's DM. It follows the goals skill: it advances active goals
within existing approvals, rarely offers relevant help, and otherwise replies `[quiet]`, which
is never posted. No goal gets its own polling schedule.

Dreaming runs at 02:00 America/Los_Angeles in a fresh thread and always stays quiet. It merges
the buffer into `/memories/user/AGENTS.md` and topic files, deduplicates, resolves clear
corrections and removes only the notes it saved. It never touches goals or reads traces.

## Playbooks

Three are built in: **Morning Brief**, **Weekly Planner** and **Watchlist**. Because they're
skills, the agent runs one when someone asks ("brief me on my day"). Adopting one, per
[the playbooks skill](../skills/playbooks/SKILL.md), creates that person's settings file and a
schedule tagged `playbook=<name>`. The skill stays shared: improve it and redeploy, and everyone
who adopted it gets the change with their settings intact. New shared playbooks are new skills,
added through code review.

## Slack

- **Watch mode:** in channels it hears every message. Set `trigger_mode="mention"` in
  `channels/slack.py` to answer only mentions.
- **Continuous DMs:** messages and thread replies in a DM share one conversation. Answers post at
  the top level unless the person replies in a thread.
- **Links:** MDA shows browser handoff and connect-app links only in Studio, so
  `slack_conversation.py` delivers them in Slack, only to the person they belong to. The model
  writes `{browser_link}` where the link goes and never sees the link itself.

This relies on private delivery hooks in `managed-deepagents==0.10.5`. Check them when upgrading
the SDK; `tests/test_slack_conversation.py` fails if they change.

## Background work

For long work it starts [async subagents](https://docs.langchain.com/langsmith/python/managed-deep-agents-subagents)
and keeps talking: `researcher` investigates one question in depth, `reviewer` checks a report or
plan before it goes out, `general-purpose` takes other self-contained tasks, and `clone` starts
with the conversation so far.

## Project structure

| Path | What it is |
|---|---|
| [`agent.py`](../agent.py) | The model, tools, subagents and which schedules every person gets. |
| [`instructions.md`](../instructions.md) | The system prompt. Start here to change how it behaves. |
| [`heartbeat.py`](../heartbeat.py), [`dreaming.py`](../dreaming.py) | Each person's hourly heartbeat and nightly dreaming. |
| [`middleware/per_user_schedules.py`](../middleware/per_user_schedules.py) | Gives each person their own schedules on their DM. |
| [`slack_conversation.py`](../slack_conversation.py) | Continuous DMs and browser and connect-app links in Slack. |
| [`skills/`](../skills/) | Onboarding, goals, dreaming and the three playbooks. |
| [`tools/`](../tools/) | Scheduling, `!clear`, schedule ownership and the Tool Gateway. |
| [`channels/slack.py`](../channels/slack.py) | The Slack bot and its icon (`channels/assets/icon.png`, 512×512). |
| [`memory.py`](../memory.py) | Personal memory, mounted only in one-on-one conversations. |
| [`browser.py`](../browser.py) | A browser per person. |
| [`identity.py`](../identity.py) | Who may call the deployment directly. |
| [`sandbox/`](../sandbox/__init__.py) | A filesystem and shell per thread. |

## Customize

- **Behavior:** edit `instructions.md` and the skills, then redeploy.
- **New playbooks:** add `skills/<name>/SKILL.md` with a description starting "Playbook:".
- **Another schedule for everyone:** add a `PersonalSchedule` file like `heartbeat.py` and list it
  in `agent.py`.
- **Approvals:** add `interrupt_on={"tool_name": True}` in `agent.py` to require a yes before a
  tool runs.
- **Accounts for unattended runs:** set `TOOLS_PROFILE` to a LangSmith profile with its own
  logins and a teammate's permissions, not an admin's.
- **Model:** direct Anthropic Opus by default. Set `AGENT_MODEL` and its provider key in
  `.env`; see [Model options](../README.md#model-options) for OpenAI or the LLM Gateway.
- **Dreaming time:** change the cron and timezone in `dreaming.py`.
- **[Local development](https://docs.langchain.com/langsmith/python/managed-deep-agents-local-development):**
  `uv run mda dev` runs it with LangSmith Studio.

## Tests and lint

```bash
uv run python -m unittest discover -s tests
uv run ruff check .
uv run ruff format --check .
```

They run offline, with no keys.

## Troubleshooting

- **It says it can't reach your apps:** check `TOOLS_MCP_URL` is your kit's MCP URL, then redeploy.
- **`Cannot change target.agent_id on an existing channel`:** the Slack app is tied to the
  agent's `name` in `agent.py`. Deploy with the name the app was created with, or recreate the
  Slack app.
- **`Slack channel icon must be 512x512px`:** resize `channels/assets/icon.png`.

## Security notes

- `!clear` uses the pinned SDK's private memory backend and isn't transactional with other
  running conversations, which can write new memory after the reset.
