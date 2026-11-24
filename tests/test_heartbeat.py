"""Exercise automatic personal background schedules and delivery."""

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from langchain_core.runnables import RunnableLambda

from heartbeat import DREAM_PROMPT, HEARTBEAT_PROMPT, ensure_personal_schedules


class Schedules:
    def __init__(self, items=()):
        self.items = list(items)
        self.created = []
        self.deleted = []

    async def list(self, *, owner, limit, offset):
        assert owner == {"type": "user"}
        await asyncio.sleep(0)
        end = offset + limit
        return {
            "items": self.items[offset:end],
            "next_offset": end if end < len(self.items) else None,
        }

    async def create(self, **kwargs):
        self.created.append(kwargs)
        item = {"id": f"created-{len(self.created)}", "paused": False, **kwargs}
        self.items.append(item)
        return item

    async def delete(self, id, *, owner):
        assert owner == {"type": "user"}
        self.deleted.append(id)
        self.items = [s for s in self.items if s["id"] != id]


def runtime(channel=None, *, kind="person", user="alice", schedules=None):
    return SimpleNamespace(
        server_info=SimpleNamespace(principal=SimpleNamespace(kind=kind, id=user)),
        thread=SimpleNamespace(origin=channel),
        schedules=schedules if schedules is not None else Schedules(),
    )


DM = {
    "name": "slack",
    "provider": "slack",
    "transport": "trigger_server",
    "source_thread_key": "slack:v1:T123:A123:D123:0",
    "raw_event": {"channel_type": "im"},
    "target": {"address": {"conversation_id": "D123", "thread_id": "1.0"}},
}


class HeartbeatTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.route = patch(
            "tools.owner.current_run_thread", side_effect=lambda r, _: r.thread
        )
        self.route.start()
        self.addCleanup(self.route.stop)

    async def run_hook(self, value, *, scheduled=False):
        async def invoke(state):
            return await ensure_personal_schedules.abefore_agent(state, value)

        return await RunnableLambda(invoke).ainvoke(
            {"messages": []},
            config={
                "configurable": {
                    "thread_id": "alice-dm-thread",
                    "langgraph_auth_user": {"mda_scheduled_run": scheduled},
                },
                "metadata": {"mda_managed": scheduled},
            },
        )

    async def test_first_dm_and_concurrent_repeats_create_one_of_each_schedule(self):
        value = runtime(DM)
        await asyncio.gather(*(self.run_hook(value) for _ in range(8)))
        self.assertEqual(
            value.schedules.created,
            [
                {
                    "owner": {"type": "user"},
                    "cron": cron,
                    "timezone": timezone,
                    "new_thread": kind != "heartbeat",
                    "prompt": prompt,
                    "metadata": {"kind": kind},
                }
                for kind, cron, timezone, prompt in [
                    ("heartbeat", "0 * * * *", "UTC", HEARTBEAT_PROMPT),
                    ("dreaming", "0 2 * * *", "America/Los_Angeles", DREAM_PROMPT),
                ]
            ],
        )

    async def test_shared_missing_and_service_contexts_do_not_access_schedules(self):
        for channel, kind in [
            (None, "person"),
            ({"provider": "slack", "raw_event": {"channel_type": "channel"}}, "person"),
            ({"provider": "slack", "raw_event": {"channel_type": "group"}}, "person"),
            ({"provider": "slack", "raw_event": {"channel_type": "mpim"}}, "person"),
            ({"provider": "slack"}, "person"),
            (DM, "service"),
        ]:
            with self.subTest(channel=channel, kind=kind):
                schedules = SimpleNamespace(list=AsyncMock(), create=AsyncMock())
                await self.run_hook(runtime(channel, kind=kind, schedules=schedules))
                schedules.list.assert_not_awaited()
                schedules.create.assert_not_awaited()
        value = runtime(DM)
        value.server_info = None
        await self.run_hook(value)
        self.assertEqual(value.schedules.created, [])

    async def test_scheduled_or_noncanonical_dm_cannot_create_schedules(self):
        for channel, scheduled in [
            (DM, True),
            ({**DM, "source_thread_key": "slack:v1:T123:A123:D123:1.0"}, True),
            ({**DM, "source_thread_key": "slack:v1:T123:A123:D123:1.0"}, False),
        ]:
            with self.subTest(channel=channel, scheduled=scheduled):
                schedules = SimpleNamespace(list=AsyncMock(), create=AsyncMock())
                await self.run_hook(
                    runtime(channel, schedules=schedules), scheduled=scheduled
                )
                schedules.list.assert_not_awaited()
                schedules.create.assert_not_awaited()

    async def test_schedules_on_later_pages_are_not_duplicated(self):
        items = [{"id": str(i), "metadata": {"kind": "task"}} for i in range(101)]
        items.extend(
            [
                {"id": "heartbeat", "metadata": {"kind": "heartbeat"}},
                {
                    "id": "dreaming",
                    "metadata": {"kind": "dreaming"},
                    "prompt": DREAM_PROMPT,
                },
            ]
        )
        value = runtime(DM, schedules=Schedules(items))
        await self.run_hook(value)
        self.assertEqual(value.schedules.created, [])
        self.assertEqual(value.schedules.deleted, [])

    async def test_reconciliation_preserves_paused_schedules_and_other_tasks(self):
        items = [{"id": "task", "metadata": {"kind": "task"}}]
        for kind, prompt in [
            ("heartbeat", HEARTBEAT_PROMPT),
            ("dreaming", DREAM_PROMPT),
        ]:
            items.extend(
                [
                    {"id": f"02-{kind}", "metadata": {"kind": kind}},
                    {
                        "id": f"01-{kind}",
                        "metadata": {"kind": kind},
                        "paused": True,
                        "prompt": prompt,
                    },
                ]
            )
        value = runtime(DM, schedules=Schedules(items))
        await self.run_hook(value)
        self.assertEqual(value.schedules.deleted, ["02-heartbeat", "02-dreaming"])
        self.assertEqual(value.schedules.created, [])
        self.assertEqual(len(value.schedules.items), 3)
        self.assertTrue(
            all(s["paused"] for s in value.schedules.items if s["id"] != "task")
        )

    async def test_each_person_gets_their_own_schedules(self):
        alice, bob = runtime(DM), runtime(DM, user="bob")
        await asyncio.gather(self.run_hook(alice), self.run_hook(bob))
        self.assertEqual(len(alice.schedules.created), 2)
        self.assertEqual(len(bob.schedules.created), 2)

    async def test_existing_schedules_are_left_as_configured(self):
        items = [
            {
                "id": kind,
                "metadata": {"kind": kind},
                "prompt": "Custom prompt",
                "cron": "0 3 * * *",
                "timezone": "America/New_York",
                "paused": True,
                "new_thread": True,
            }
            for kind in ["heartbeat", "dreaming"]
        ]
        value = runtime(DM, schedules=Schedules(items))
        await self.run_hook(value)
        await self.run_hook(value)
        self.assertEqual(value.schedules.items, items)
        self.assertEqual(value.schedules.created, [])
        self.assertEqual(value.schedules.deleted, [])
