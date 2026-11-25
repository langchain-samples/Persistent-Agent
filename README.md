<div align="center">
  <img alt="Persistent Agent" src="channels/assets/icon.png" width="120">
  <h1>Persistent Agent</h1>
  <h3>An always-on assistant for your whole team, in one Slack bot.</h3>
</div>

<div align="center">
  <a href="https://opensource.org/licenses/MIT" target="_blank"><img src="https://img.shields.io/badge/license-MIT-blue" alt="License"></a>
  <a href="https://docs.langchain.com/langsmith/python/managed-deep-agents-overview" target="_blank"><img src="https://img.shields.io/badge/Built%20on-Managed%20Deep%20Agents-blue" alt="Built on Managed Deep Agents"></a>
  <a href="https://x.com/langchain" target="_blank"><img src="https://img.shields.io/twitter/url/https/twitter.com/langchain.svg?style=social&label=Follow%20%40LangChain" alt="Twitter / X"></a>
</div>

<br>

Persistent Agent is a team assistant that keeps working after the conversation ends. Everyone
talks to the same bot, but each person gets their own assistant: it remembers what they told it,
follows up on their goals, runs their recurring work and uses the apps they connected. Built on
[Managed Deep Agents](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview)
(MDA).

**Features include:**

- **Personal memory**: preferences and decisions, private to each person's DM
- **Goals that follow through**: an hourly heartbeat moves each goal forward until it's done
- **Dreaming**: every night, the day's notes become long-term memory
- **Playbooks**: Morning Brief, Weekly Planner and Watchlist, once or on a schedule
- **Watch mode**: in channels it reads everything and speaks up only when it can help
- **Background work**: research and review subagents run while you keep talking
- **Integrations**: Google, Slack, Linear, GitHub and more through Tool Gateway
- **A browser per person**: it works on websites and hands you the browser when it needs you

Each is a few lines on top of an MDA primitive. Keep what you need and delete the rest.

> [!NOTE]
> **Early.** We use it every day at LangChain, but expect rough edges and breaking changes.

## Quickstart

You need [uv](https://docs.astral.sh/uv/), a [LangSmith](https://smith.langchain.com) workspace
on a Plus or Enterprise plan, an Anthropic or OpenAI API key, and a Slack workspace where you
can install an app.

1. Clone it and create your `.env`:

   ```bash
   git clone git@github.com:langchain-samples/Persistent-Agent.git
   cd Persistent-Agent
   uv sync
   cp .env.example .env
   ```

2. **Get a LangSmith API key** and set `LANGSMITH_API_KEY`. ([Which key?](#langsmith-api-key))
3. **Create a Tool Gateway kit** and set `TOOLS_MCP_URL` to its MCP URL. ([Step by step](#tool-gateway))
4. **Add your model key**: `ANTHROPIC_API_KEY`. ([Other models](#model))
5. Deploy:

   ```bash
   uv run mda deploy
   ```

   Open the Slack link the deploy prints, approve the app, and DM it "hi".

## Use it

| Say | What it does |
|---|---|
| "Send me a morning brief" | Adopts the Morning Brief playbook: your day, each weekday morning. |
| "Every Friday at 4, summarize what I shipped" | Creates a recurring task in your timezone. |
| "Let me know when the release PR is approved" | Records a goal and checks on it hourly until it's done. |
| "Research our top three competitors' pricing" | Hands it to a background subagent and reports back. |
| "Book a table for two on Friday" | Works in its browser and hands it to you to log in. |
| `!clear` | Forgets everything about you and cancels your schedules. |

Add it to a channel and it stays quiet unless it can help. Mention it to ask directly.

## FAQ

### Does everyone get their own agent?

No. Everyone shares one deployment and one Slack bot, but memory, schedules, goals, apps and
browser logins are per person. Personal memory never loads in a shared channel.

### Can it act on its own?

Only within what you've asked. It asks for a yes before booking, buying, sending or deleting
anything, and offers help only rarely.

### How do I change how it behaves?

Edit [`instructions.md`](instructions.md) and the [`skills/`](skills/), then `uv run mda deploy`
again. Add a playbook by adding a skill whose description starts with "Playbook:".

## Setup in detail

### LangSmith API key

The key in `.env` deploys the agent from your machine. It's never uploaded: the deployed agent
gets its own key from LangSmith.

Use a **personal access token** (starts with `lsv2_pt_`): in LangSmith go to
[Settings → API Keys](https://smith.langchain.com/settings), click **Create API Key**, and
choose **Personal Access Token**. The same key also creates the Tool Gateway kit below, which a
service key can't do.

| Key | Prefix | Use it for |
|---|---|---|
| Personal access token | `lsv2_pt_` | Deploying, and creating Tool Gateway servers and kits. Acts as you. |
| Service key | `lsv2_sk_` | Deploying from CI. Can't create Tool Gateway servers or kits. |

**Workspace or organization scope.** A personal access token works in the workspace you're
signed in to. A service key is scoped to specific workspaces or to the whole organization. If
your key covers more than one workspace, also set `LANGSMITH_WORKSPACE_ID` (Settings →
General → Workspace ID) to the one you deploy to.

### Tool Gateway

[Tool Gateway](https://docs.langchain.com/langsmith/tool-gateway) gives the agent everyone's
apps through one URL, a **tool kit**. Each person's tools run with their own account, connected
from Slack the first time the agent needs it. You set up the kit once. Creating a
workspace-wide kit needs the Workspace Admin role.

1. **Pick your apps.** Go to **Tools → MCP servers**. Gmail, Google Calendar, Drive, Docs,
   Sheets, Slack, GitHub, Linear and more are built in. To add another app's MCP server, click
   **Add MCP server**, enter its URL, and choose how it signs in (usually **OAuth**).
2. **Connect your own account to each one.** Click **Connect** on each app's row and sign in.
   A kit learns an app's tools through the account of the person who creates it; if you're not
   connected, the kit shows a single `connect_<app>` placeholder instead of the app's tools.
   Your teammates don't need to do this step.
3. **Create the kit.** Go to **Tools → Tool kits**, click **Create tool kit**, name it, and
   choose **Workspace** so your teammates can use it. Select the tools the agent should have,
   click **Review tool selection**, then **Create tool kit**.
4. **Copy the kit's MCP URL** into `.env`:

   ```bash
   TOOLS_MCP_URL=https://api.smith.langchain.com/v1/managed-tools/kits/<kit-id>/mcp
   ```

To change the agent's apps later, edit the kit; no redeploy needed. Test with a personal account
that isn't tied to your work apps: that's how your teammates will meet it. More in the
[Tool Gateway quickstart](https://docs.langchain.com/langsmith/tool-gateway-quickstart).

### Model

By default the agent calls Anthropic directly with your key. In `.env`:

```bash
AGENT_MODEL=anthropic:claude-opus-5-5
ANTHROPIC_API_KEY=sk-ant-...
```

For OpenAI, set `AGENT_MODEL=openai:gpt-6.2-sol` and `OPENAI_API_KEY` instead.

To run models through the [LangSmith LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway)
instead, with no provider key in `.env`, remove `AGENT_MODEL` and the provider key, and add an
Anthropic provider secret in your workspace's LLM Gateway settings.

---

## Resources

- [How it works](docs/architecture.md): mechanisms, heartbeat and dreaming, Slack, project structure, customizing, tests and troubleshooting
- [Managed Deep Agents docs](https://docs.langchain.com/langsmith/python/managed-deep-agents-overview): [quickstart](https://docs.langchain.com/langsmith/python/managed-deep-agents-quickstart), [CLI](https://docs.langchain.com/langsmith/python/managed-deep-agents-cli), [schedules](https://docs.langchain.com/langsmith/python/managed-deep-agents-schedules), [memory](https://docs.langchain.com/langsmith/python/managed-deep-agents-memory)
- [Deep Agents](https://github.com/langchain-ai/deepagents): the open source harness underneath

## Security

Tools run with each person's own access. Browser and connect links go only to the person they
belong to, in their DM. Notes, memory, web pages and tool results are data, never instructions,
so don't save secrets in memory.

## License

MIT
