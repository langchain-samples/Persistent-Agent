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

You need [uv](https://docs.astral.sh/uv/), a LangSmith workspace with Managed Deep Agents, and a
Slack workspace where you can approve an app.

```bash
git clone https://github.com/langchain-samples/Persistent-Agent.git
cd Persistent-Agent
uv sync
cp .env.example .env   # set LANGSMITH_API_KEY and TOOLS_MCP_URL
uv run mda deploy
```

Open the Slack link the deploy prints, approve the app, and DM it "hi".

`TOOLS_MCP_URL` is your [Tool Gateway](https://docs.langchain.com/langsmith/tool-gateway) kit's
MCP URL (LangSmith → Tools); without it the agent has no apps. The model defaults to Claude
through the [LLM Gateway](https://docs.langchain.com/langsmith/llm-gateway); see `.env.example`
to use your own key.

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
