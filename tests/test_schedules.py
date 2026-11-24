"""Exercise one-time and recurring scheduling after background schedule setup."""

import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from tools.schedules import list_schedules, schedule


class ScheduleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(
            server_info=SimpleNamespace(
                principal=SimpleNamespace(kind="person", id="alice")
            ),
            config={},
            thread=SimpleNamespace(
                origin={"provider": "slack", "raw_event": {"channel_type": "im"}}
            ),
            schedules=SimpleNamespace(create=AsyncMock(return_value={"id": "task"})),
        )
        route = patch(
            "tools.owner.current_run_thread", side_effect=lambda r, _: r.thread
        )
        route.start()
        self.addCleanup(route.stop)
        config = patch("tools.owner.get_config", return_value={})
        config.start()
        self.addCleanup(config.stop)

    async def test_recurring_playbook_is_tagged_and_uses_local_time(self):
        task = (
            "Run the morning-brief playbook with the settings in "
            "/memories/user/playbooks/morning-brief.md."
        )
        await schedule.coroutine(
            task,
            self.runtime,
            cron="30 7 * * 1-5",
            tz="America/Los_Angeles",
            playbook="morning-brief",
        )
        self.runtime.schedules.create.assert_awaited_once_with(
            owner={"type": "user"},
            cron="30 7 * * 1-5",
            timezone="America/Los_Angeles",
            new_thread=True,
            prompt=task,
            metadata={"kind": "playbook", "playbook": "morning-brief"},
        )

    async def test_check_in_uses_same_conversation_and_correct_owner(self):
        for channel_type, owner_type in [("im", "user"), ("channel", "agent")]:
            with self.subTest(channel_type=channel_type):
                self.runtime.thread.origin["raw_event"]["channel_type"] = channel_type
                before = datetime.now(timezone.utc)
                await schedule.coroutine("Check progress", self.runtime, in_minutes=30)
                created = self.runtime.schedules.create.call_args.kwargs
                self.assertEqual(created["owner"], {"type": owner_type})
                self.assertFalse(created["new_thread"])
                self.assertEqual(created["prompt"], "Check progress")
                self.assertGreaterEqual(created["at"], before + timedelta(minutes=30))
                self.assertLessEqual(
                    created["at"], datetime.now(timezone.utc) + timedelta(minutes=30)
                )

    async def test_exactly_one_timing_mode_is_required(self):
        for timing in [
            {},
            {"in_minutes": 30, "cron": "0 * * * *"},
            {"in_minutes": 30, "playbook": "morning-brief"},
            {"cron": "0 9 * * *", "playbook": "../brief"},
        ]:
            await schedule.coroutine("Check progress", self.runtime, **timing)
        self.runtime.schedules.create.assert_not_awaited()

    async def test_person_can_see_background_schedules_and_recurring_tasks(self):
        self.runtime.schedules.list = AsyncMock(
            return_value={
                "items": [
                    {
                        "id": kind,
                        "metadata": {"kind": kind},
                        "cron": "0 * * * *",
                        "paused": False,
                        "prompt": kind,
                    }
                    for kind in ["heartbeat", "dreaming", "task"]
                ]
                + [
                    {
                        "id": "brief",
                        "metadata": {"kind": "playbook", "playbook": "morning-brief"},
                        "cron": "30 7 * * 1-5",
                        "paused": False,
                        "prompt": "Run the morning-brief playbook",
                    }
                ]
            }
        )
        result = await list_schedules.coroutine(self.runtime)
        for kind in ["heartbeat", "dreaming", "task"]:
            self.assertIn(kind, result)
        self.assertIn("[playbook morning-brief]", result)
