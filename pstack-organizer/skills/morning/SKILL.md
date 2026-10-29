---
name: morning
description: "Run an on-demand morning check-in across app delivery, maintenance, work tasks, and remembered context. Use for /morning, 'good morning', 'morning check-in', or 'catch me up for today' while organizing the user's work."
---

# Morning check-in

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute path. Run Python 3.10+ with explicit configured home/workspace flags before the command. Keep the selected workspace throughout; in Grok Bot its configured data home belongs under `/workspace`.

1. Establish the user's current date and timezone, and any stated time budget or focus. Run `morning --date YYYY-MM-DD`, optionally `--minutes N` and `--limit N`. This reads saved state only. Use setup-organizer for a new store or `init` to upgrade an existing version-one store; do not silently substitute a fresh empty workspace.
2. Lead with a short useful briefing. For each active app, show its recorded stage, latest progress, blocker or next action when available, and source freshness. Include apps being built as well as maintained. A checkpoint is reported progress, not proof the app currently works. Label missing or unverified state plainly.
3. Present up to three recommended commitments with one concrete next action and the planner's reason. Label default estimates. Surface all overdue commitments and due waiting/blocked follow-ups even if they are not selected. Keep the full inventory available without flooding the opening message.
4. Review `notes_to_review`. Retrieve additional current notes with `note list --app ID` or `--query TEXT` only when relevant to today's projects or the user's question. Attribute sources and mention conflicting, superseded, or uncertain information. Do not recite every stored note every morning or treat a review date as proof something changed.
5. When live repository state matters to today's decision, inspect the relevant source read-only and identify what was checked and when. The default result is ledger-only; do not claim all repositories, applications, or clusters were checked. Route an app audit through maintain-app rather than making unsupported health claims.
6. Accept the user's updates or brain dump. Route actions to capture-task and facts/decisions to remember-work. Confirm saves with returned IDs. Preserve unfinished work; never silently reset priorities, assign deadlines, or turn ideas into promises to fill a list.
7. Let the user choose the focus, or continue a specific action they already requested. A greeting or check-in alone does not start builds, send messages, merge PRs, or deploy. Use jared-mode for authorized engineering work, then close-session to retain progress and loose ends.

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --home "/workspace/pstack-organizer-data" --workspace personal morning --date 2026-10-28 --minutes 90
```

If the ledger is empty, state that briefly and help register the selected apps or capture what the user tells you. This is a conversation workflow, not an installed routine or scheduled notification.
