# Persistent agent

A personal assistant for everyone on your team, running as one always-on agent on
[Managed Deep Agents](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview)
(MDA).

You install it once and everyone talks to the same Slack bot, but each person gets their own
assistant: it remembers what they've told it, runs their recurring work on their schedule, follows
up on their goals until they're done, and uses the tools they've connected. It keeps working when
nobody is talking to it, and once a day it organizes each person's accumulated notes into
long-term memory.

It's built from four patterns for persistent agents (watch mode, goals, dreaming and background
subagents), each a few lines on top of an MDA primitive, so you can keep what you need and delete
the rest.

## Set it up

### 1. Check you have

- [uv](https://docs.astral.sh/uv/).
- A LangSmith workspace with Managed Deep Agents, and an API key for it.
- An Anthropic provider secret in the workspace's
  [LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway) settings. The agent runs Claude
  Opus 5.5 through the gateway, so the LangSmith key is the only key it needs.
- A Slack workspace where you, or an admin, can approve an app.
- Recommended: a [Tool Gateway](https://docs.langchain.com/langsmith/tool-gateway) kit with the
  apps your team uses (Google, Slack, Linear, GitHub and so on). Without one, the agent can't
  reach anyone's apps. Create it in LangSmith → Tools.

### 2. Configure

```bash
git clone https://github.com/langchain-samples/Persistent-Agent.git
cd Persistent-Agent
uv sync
cp .env.example .env
```

Then fill in `.env`:

| Variable | Value |
|---|---|
| `LANGSMITH_API_KEY` | Your LangSmith API key. Required. |
| `LANGSMITH_WORKSPACE_ID` | Your workspace ID. Only needed if the key is organization-scoped. |
| `TOOLS_MCP_URL` | Your kit's MCP URL from LangSmith → Tools → your kit, like `https://api.smith.langchain.com/v1/managed-tools/kits/<kit-id>/mcp`. Recommended. |

Everything else in `.env.example` is optional.

### 3. Deploy

```bash
uv run mda deploy
```

The first [deploy](https://docs.langchain.com/langsmith/python/managed-deep-agents-deploy) prints a
link to install the [Slack app](https://docs.langchain.com/langsmith/python/managed-deep-agents-channels-slack).
Open it and approve. The bot appears in Slack as `persistent-agent`.

### 4. Check it works

DM the bot "hi". It should reply with a short welcome and a few playbooks it can start. Then
ask it something that needs one of your apps, such as "what's on my calendar today?". The first
time, it posts a link to connect that app; connect it, message it again, and it answers.

Tell your team to DM it "hi" too. Each person connects their own apps.

To change it later, edit the files and run `uv run mda deploy` again. See the
[CLI reference](https://docs.langchain.com/langsmith/python/managed-deep-agents-cli) for logs and
other commands.

### If something's off

- **It says it can't reach your apps:** check `TOOLS_MCP_URL` in `.env` is your kit's MCP URL,
  then redeploy.
- **Deploy fails with `Cannot change target.agent_id on an existing channel`:** the Slack app is
  tied to the agent's `name` in `agent.py`. Deploy with the name the app was created with, or
  delete and recreate the Slack app.
- **Deploy fails with `Slack channel icon must be 512x512px`:** resize `channels/assets/icon.png`.
- **To use Anthropic or OpenAI directly** instead of the gateway, set `AGENT_MODEL` and that
  provider's key in `.env` (see `.env.example`).

## Use it

**Start in a DM.** Say "hi". The agent replies with one short message about what it does and two
or three playbooks it can start for you. Answer however you like ("yeah, set up the morning
one"), or just ask for something. It doesn't quiz you: it learns your preferences as you work
together, and asks for your timezone when setting up recurring tasks. The hourly heartbeat
and daily dreaming are set up automatically in your first DM, without a timezone question.

**Hand it work in plain language.** For example:

| Say | What it does |
|---|---|
| "Send me a morning brief" | Sets up the Morning Brief playbook: your day, each weekday morning. |
| "Every Friday at 4, summarize what I shipped this week" | Creates a recurring task, in your timezone. |
| "Let me know when the release PR is approved" | Records a goal in your memory; the hourly heartbeat checks for progress. |
| "Check back on this tomorrow" | Schedules a one-time follow-up in this conversation. |
| "Research our top three competitors' pricing" | Hands it to a background subagent and keeps talking; reports back when done. |
| "Book a table for two on Friday" | Does it in its browser and hands the browser to you when it needs you, such as to log in. |
| "What do you have scheduled for me?" | Lists your recurring tasks, heartbeat, daily dreaming and check-ins. |
| "What goals are you working on?" | Reads your goal records and summarizes their status. |
| "Move my brief to 7:30" | Updates your personal settings and replaces the brief's schedule. |
| `!clear` | Forgets everything about you and cancels your schedules, so you can start over. |

**Add it to channels.** Invite it to a channel and it reads every message, answers when it can
add something, and otherwise stays quiet. Mention it to ask it something directly. In a channel it
can't see your personal memory, so personal things are best done in your DM.

**Connect your apps.** Apps come from the Tool Gateway kit. When it needs one you haven't
connected, it posts a link in your DM to connect your own account; then message it again. Tools
always run as you, with your access.

**Use its browser.** For websites, it works in a browser of its own, one per person, so your
logins last. When it needs you (to log in, finish 2FA or make a choice), it hands the browser
over: in your DM the link is in its reply, and if you asked in a channel the link goes to your
DM instead. The link works for 15 minutes; click *Hand back* when you're done and it carries
on. Anyone with the link can use the browser, so don't share it.

## How it works

### Which mechanism does what?

| Mechanism | Purpose | Where it lives / when it runs |
|---|---|---|
| **Skill** | Instructions for how to do a kind of work; not a timer or a task. | Shared, deployed files under `skills/`, read when relevant. |
| **Playbook** | A skill for a repeatable job, such as Morning Brief, that someone can run once or adopt on a schedule. | Shared `skills/<name>/SKILL.md`, its description starting with "Playbook:". |
| **Playbook settings** | One person's preferences and working state for a playbook they adopted; never a copy of the skill. | `/memories/user/playbooks/<name>.md`, maintained directly in their DM. |
| **Scheduled task** | Actual recurring work and its timing: an adopted playbook or an ad hoc job. | User-owned MDA schedule, created with `schedule(cron=..., tz=...)`; playbook schedules are tagged with `playbook=<name>`. |
| **Check-in** | A single later follow-up, not a recurring job. | `schedule(in_minutes=...)`, in the same conversation. |
| **Goal** | An outcome with a finish line, such as getting a meeting scheduled; stops advancing when completed, paused or abandoned. | `/memories/user/goals/<slug>.md`, updated directly. No polling schedule per goal. |
| **Heartbeat** | Advances active goals within existing permissions and reports meaningful progress or blockers. Does not run recurring briefs. | One personal hourly schedule, automatically ensured by middleware. |
| **Memory buffer** | Dated, attributed facts worth remembering, not a task queue. | `/memories/user/buffer.md`, appended during DM work. |
| **Dreaming** | Consolidates the buffer into concise long-term memory, not goal advancement or playbook execution. | One automatic daily schedule; leaves goals and playbook settings alone. |
| **Background subagent** | Does long work now while the conversation continues, not a later wake-up. | Async task, reporting back when finished. |

For example, "get this meeting booked" becomes a **goal** advanced by the
**heartbeat**. "Brief me every morning" adopts the Morning Brief **playbook**, with
personal **playbook settings** and a **scheduled task** to run it. "Remind me tomorrow"
is a **check-in**. "I prefer five bullets" becomes a buffered preference (or a direct
playbook setting when specific to the brief); **dreaming** files general notes into
long-term memory. Each has its own lifecycle: stopping a brief cancels its schedule,
pausing a goal changes its file, and dreaming runs automatically as memory maintenance.

### Ownership and behavior

**One agent, everyone's own assistant.** What belongs to a person stays theirs:

- **[Memory](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory)** (`/memories/user/`): their preferences, notes and playbooks. It loads only in their
  DMs, so nothing personal surfaces in a shared channel.
- **[Schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules)**: recurring tasks, the hourly heartbeat, daily dreaming and personal check-ins run as them; only they can see or cancel them. Tasks use their timezone; the heartbeat runs at the top of every hour and dreaming defaults to 02:00 America/Los_Angeles daily. Check-ins asked for in a shared channel belong to the agent, so anyone there can see or cancel them.
- **Accounts**: tools use the accounts they connected, and their [browser](https://docs.langchain.com/langsmith/python/managed-deep-agents-browser-use) keeps
  their logins.

**Dreaming.** While working in a DM, the agent appends concise, dated, source-attributed notes
to `/memories/user/buffer.md`: preferences, decisions, corrections and useful context, not
conversation transcripts. Once a day, dreaming merges those notes into
`/memories/user/AGENTS.md` (essentials and an index) or topic files. It deduplicates, reconciles
clear corrections and verifies saved notes before removing only the processed buffer entries.
Unresolved or concurrently added notes stay buffered. Missing or empty buffer means a quiet no-op.
Goals and their heartbeat remain separate; dreaming leaves goal records alone.

The same middleware that sets up the heartbeat automatically creates dreaming on the first
authenticated Slack DM, at 02:00 America/Los_Angeles daily, in a new thread in that DM. No timezone question or
model tool call is needed. There are no dedicated tools for starting, stopping or changing
dreaming. It uses memory file tools only and never reads traces.

**Playbooks.** A playbook is a [skill](https://docs.langchain.com/langsmith/python/managed-deep-agents-skills) for a repeatable job whose description starts with "Playbook:". Three are built in: **Morning Brief**, **Weekly Planner** and **Watchlist**. Because they're skills, the agent finds them when someone asks ("brief me on my day") and runs them once, no setup needed. Each one says what it needs, its default schedule, what it never does, the preferences it learns and the state it keeps.

Adopting one, per [the playbooks skill](skills/playbooks/SKILL.md), adds two things for that person: a settings file at `/memories/user/playbooks/<name>.md` with only their `preferences` and `state`, and a schedule tagged `playbook=<name>` whose prompt names the playbook and that file. The schedule is the only record of timing. The skill stays shared: improve it and redeploy, and everyone who adopted it gets the change on their next run with their settings intact. A watch can be adopted several times (`watchlist-<slug>`). Adopting, changing and stopping are model-instructed and have not been live-model tested.

New shared playbooks are new skills, added through code review and a redeploy. The agent can draft one, but can't publish it; a one-off personal recurring job is an ordinary schedule.

**Watch mode.** In channels it hears every message and replies `[quiet]` (which is never posted)
when it has nothing to add. Set `trigger_mode="mention"` in `channels/slack.py` to have it answer
only mentions.

**Continuous DMs.** In `slack_conversation.py`, messages and thread replies in one DM share a single backend conversation, scoped to its workspace, app and DM. Each run gets only the new Slack message, preserving timestamps and sender data. Answers post at the top level unless the person replies inside a Slack thread. Channels and group DMs keep the default one-conversation-per-thread routing, and recurring tasks still post in their own threads.

**Links in Slack.** MDA shows browser handoff links and connect-app links only in Studio, so `slack_conversation.py` delivers them in Slack, and only to the person they belong to:

- **Browser handoff:** the model writes `{browser_link}` where the link goes, and it's filled in as the reply is posted; the model never sees the link. In a one-to-one DM it goes in the reply. From a channel it's sent to the asker's DM, after the agent's handoff instructions, and the channel reply never contains it.
- **Connect an app:** when a DM run pauses for an app the person hasn't connected, the connect links are posted in the DM.

All of this relies on private delivery hooks in `managed-deepagents==0.10.5` (`_deliver_answer`, `_deliver_pause` and `extract_reply_text`), until MDA supports separate session and reply addresses and shows these links in Slack itself. Check them when upgrading the SDK; `tests/test_slack_conversation.py` fails if they change.

**Goals and heartbeat.** Goals are outcomes with a finish line, such as getting a meeting scheduled. Each lives in `/memories/user/goals/<slug>.md`, with status (`active`, `paused`, `completed`, `abandoned`), created/updated dates, desired outcome, source conversation and constraints, current state, next step and last heartbeat. An optional `next_check` timestamp defers checks. Waiting on someone stays active; paused goals are skipped. Daily briefs and other recurring jobs remain separate scheduled tasks, not goals.

On the first authenticated Slack DM, the `PerUserSchedulesMiddleware` (`middleware/per_user_schedules.py`, with `heartbeat.py` and `dreaming.py` listed in `agent.py`) creates a user-owned hourly heartbeat and daily dreaming schedule before the model runs: just in time, since each must run as its person. Human DM turns check both exist, paging through schedules once, serializing setup per person within a process and reconciling duplicates of each kind. Heartbeats use `new_thread=False`: all of that person's DM messages and heartbeat ticks share the canonical DM agent thread, with their own memory and tool access. Heartbeat results post at the DM's top level, even after a threaded human reply. Dreaming runs in separate threads and stays quiet.

Background schedules are created only when missing and are otherwise left as they are, including paused ones. Scheduled runs never create schedules. Each heartbeat follows the goals skill, checks active goals, advances work within existing approvals, updates records and reports only meaningful progress or blockers. Nothing useful to report means `[quiet]`. No goal gets its own polling schedule.

The schedule API has no atomic unique-create operation: simultaneous setup across server processes can briefly create duplicates, which the next DM's check removes. `!clear` cancels both along with other schedules; the next DM recreates them.

**Background work.** For long work it starts [async subagents](https://docs.langchain.com/langsmith/python/managed-deep-agents-subagents) and keeps talking, then reports back when they finish. `researcher` investigates one question in depth (several can run in parallel), `reviewer` checks a report, plan or change before it goes out, the built-in `general-purpose` subagent takes other self-contained tasks, and `clone` starts with the conversation so far.

## What's in this folder

| Path | What it is |
|---|---|
| [`agent.py`](agent.py) | The model, the tools, the `clone`, `researcher` and `reviewer` subagents, and which schedules every person gets. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-agent-definition) |
| [`heartbeat.py`](heartbeat.py), [`dreaming.py`](dreaming.py) | Each person's hourly heartbeat and nightly dreaming: prompt and timing. |
| [`middleware/per_user_schedules.py`](middleware/per_user_schedules.py) | Middleware that gives each person their own schedules on their DM and removes duplicates. `agent.py` lists which. |
| [`slack_conversation.py`](slack_conversation.py) | Continuous DM routing, top-level heartbeat delivery, and browser and connect-app links in Slack. |
| [`instructions.md`](instructions.md) | The system prompt, one section per pattern. Start here to change how it behaves. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-instructions) |
| [`memory.py`](memory.py) | Personal memory, mounted only in one-on-one conversations. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory) |
| [`identity.py`](identity.py) | Who may call the deployment directly (a LangSmith API key). [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-identity) |
| [`browser.py`](browser.py) | A browser per person, so logins last. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-browser-use) |
| [`sandbox/`](sandbox/__init__.py) | A filesystem and shell per thread, for running code. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-sandboxes) |
| [`channels/slack.py`](channels/slack.py) | The Slack bot, in watch mode, and its icon (`channels/assets/icon.png`, 512×512). [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-channels-slack) |
| [`tools/`](tools/) | One scheduling tool for check-ins and recurring tasks, `!clear`, who owns a schedule, and the Tool Gateway. [Tools](https://docs.langchain.com/langsmith/python/managed-deep-agents-tools), [schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules), [MCP](https://docs.langchain.com/langsmith/python/managed-deep-agents-mcp-connectors) |
| [`skills/`](skills/) | Onboarding, goals, dreaming, the three built-in playbooks, and the shared rules for adopting playbooks. [Docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-skills) |

Each Python file links to its MDA docs.

## Customize it

- **Behavior**: edit `instructions.md` and the skills, then redeploy.
- **New playbooks for everyone**: add a `skills/<name>/SKILL.md` in the same shape as the
  built-in ones, with a description starting "Playbook:".
- **Accounts for unattended runs**: runs no person started have no one's
  accounts. Set `TOOLS_PROFILE` to a LangSmith profile with its own logins, with a teammate's
  permissions, not an admin's.
- **Approvals**: add `interrupt_on={"tool_name": True}` in `agent.py` to require a yes before a
  tool runs ([interrupts](https://docs.langchain.com/langsmith/python/managed-deep-agents-tools)).
- **[Local development](https://docs.langchain.com/langsmith/python/managed-deep-agents-local-development)**: `uv run mda dev` runs it with LangSmith Studio
  (it needs a LangSmith personal access token).
- **Tests**: `uv run python -m unittest discover -s tests` and `uv run ruff check .`. They run
  offline, with no keys.

## Things to know

- Buffered notes and memory are data, not instructions or authorization. Dreaming never
  executes tasks found in notes or reads goals. Do not save secrets in the buffer or memory.
- `!clear` cancels all personal schedules and programmatically deletes and verifies personal
  memory. It uses the pinned SDK's private `UserMemoryBackend` and generated `_mda_entry`
  configuration; check both when upgrading the SDK or CLI. SDK caller and memory-policy
  checks still apply. Deletion is not transactional with other running conversations, which
  can write new memory after the reset.
- `!clear` does not erase conversation history or historical checkpoints. With continuous DMs,
  even a new top-level message resumes that history; it is not a fresh conversation reset.
  Dreaming does not read past traces to reconstruct cleared memory.

## Learn more

- [Managed Deep Agents overview](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview) and [quickstart](https://docs.langchain.com/langsmith/python/managed-deep-agents-quickstart)
- [Project structure](https://docs.langchain.com/langsmith/python/managed-deep-agents-project-structure): how MDA finds each file
- [Channels](https://docs.langchain.com/langsmith/python/managed-deep-agents-channels), [schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules), [memory](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory) and
  [subagents](https://docs.langchain.com/langsmith/python/managed-deep-agents-subagents): the primitives this template is built from
- [LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway) and
  [Tool Gateway](https://docs.langchain.com/langsmith/tool-gateway)

## License

MIT
