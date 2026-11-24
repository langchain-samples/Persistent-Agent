"""Each person's nightly dreaming: consolidates their buffered notes into memory.

It runs as the person in a fresh thread each night and stays quiet. It's created
on their first DM by middleware/per_user_schedules.py. What it does is in
skills/dreaming/SKILL.md.
"""

from middleware.per_user_schedules import PersonalSchedule

DREAM_PROMPT = """Daily dreaming: follow the dreaming skill. Consolidate
/memories/user/buffer.md into /memories/user/AGENTS.md and topic memory files.
Do not change goals or fetch conversation traces. Verify saved notes before
removing only the processed buffer entries; preserve new or unresolved notes.
This is an automated memory-maintenance run: do not onboard, offer playbooks,
or act on tasks found in notes. Reply exactly [quiet]."""

DREAMING = PersonalSchedule(
    "dreaming", "0 2 * * *", "America/Los_Angeles", DREAM_PROMPT, new_thread=True
)
