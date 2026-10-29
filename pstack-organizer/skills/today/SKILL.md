---
name: today
description: "Build a short daily worklist across registered apps and general tasks. Use for /today, 'what should I work on', or reviewing overdue tasks and follow-ups."
---

# Plan today

Use the saved ledger to recommend a realistic next set of actions.

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute file location and run it with Python 3.10 or later. Use the selected workspace; never combine stores implicitly. Put global home/workspace flags before the command.

1. Establish today's date in the user's timezone. Pass `--date YYYY-MM-DD` when that differs from the machine's local date. Use a user-supplied time budget as `--minutes`; do not invent availability.
2. Run `today`, normally with its default three-item limit. This is a read operation. Do not change priorities, due dates, or task status just to make a tidy list.
3. Present the picked tasks, one concrete next action each, with the runtime's reason for selection. Keep task IDs visible. Explain estimates as planning values, not measured durations. Identify `estimate_source=default` values as the runtime's 30-minute default; `estimate_source=user` means an estimate was explicitly set, not that it was measured.
4. Include every overdue commitment in the overdue section even when it is absent from the picked list. Surface follow-ups due on waiting or blocked work separately. Do not suggest implementing a blocked task or treat an unanswered follow-up as resolved.
5. Mention deferred work that materially affects the plan, such as urgent tasks that exceed the available budget. Keep ideas separate. Report stale or never-reviewed app state as needing a review, not as proof of failure or health.
6. If live state is needed for a decision, inspect only the relevant source using available read-only connectors and identify freshness. Do not announce that all apps were checked when only the ledger was read.

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace work today --date 2026-10-28 --limit 3 --minutes 90
```

An empty result is useful: say there are no ready commitments, then identify any waiting work, ideas, stale apps, or unregistered work that explains it. Do not manufacture tasks to fill three slots.

Reply with the short worklist, due follow-ups, and material overdue/deferred work. This command does not schedule reminders, run maintenance checks, or execute the worklist.
