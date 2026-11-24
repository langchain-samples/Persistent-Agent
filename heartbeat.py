"""Each person's hourly heartbeat: advances their goals and, rarely, offers help.

It runs as the person, continuing their DM, and is created on their first DM by
middleware/per_user_schedules.py.
"""

from middleware.per_user_schedules import PersonalSchedule

HEARTBEAT_PROMPT = """Hourly heartbeat: be a helpful work assistant. Follow
the goals skill to advance active goals within existing approvals and follow-up
timing. Even without active goals, occasionally consider a concrete offer to help
with recent work visible in the shared DM history or a relevant available playbook.
Follow the skill's attention budget and personal proactivity preferences: offers
are rare, not an every-tick or daily quota. Never repeat ignored or declined offers,
pretend to see activity you cannot access, or treat an offer as permission to act.
Report meaningful progress, completion, a blocker needing the person, or one timely
suggestion that passes those rules. Otherwise reply exactly [quiet]. This is an
automated run, not a new person's first message; do not onboard."""

HEARTBEAT = PersonalSchedule("heartbeat", "0 * * * *", "UTC", HEARTBEAT_PROMPT)
