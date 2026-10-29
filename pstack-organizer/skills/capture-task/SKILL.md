---
name: capture-task
description: "Save a commitment, idea, blocker, or follow-up to a durable task ledger. Use for /capture-task, 'remember I need to', 'add this to my list', or updating an organizer task."
---

# Capture a task

Record the user's intent with enough provenance to recover it later.

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute file location and run it with Python 3.10 or later. Put explicit workspace/home flags before the command; use the selected workspace consistently. Initialize through setup-organizer if needed.

1. Identify the requested commitment or idea. “I need to test this” is a commitment. “Maybe someday” is an idea. Preserve uncertain intent as an idea; never turn the agent's suggestions into commitments. Split independent actions into separate records.
2. Resolve the app from explicit context or `app list`. If several apps fit, ask one focused question or save an unassigned task and state that choice. General work tasks need no app. Never guess a repository from a similar name.
3. Run `task list` in the relevant scope before adding. Reuse the existing task for the same intent or external issue. Supply a stable `--key` for a retried capture, such as a source message ID plus item index. Do not reuse a key for changed intent; conflicting keyed requests must be resolved, not overwritten.
4. Run `task add TITLE --source TEXT`, optionally with `--app`, `--kind`, `--next-action`, and other known fields. Save a concise source quote or source link. Keep credentials and unnecessary private content out of the record.
5. Set `--due` only for a deadline the user actually specified. Resolve relative dates in the user's timezone and pass an absolute `YYYY-MM-DD`. Ask if a material date or timezone is ambiguous. Use `--follow-up` for a waiting check-in, with `--waiting-on` and `--status waiting` when appropriate. These dates do not create reminders.
6. Use `task update ID` to change existing work. Preserve omitted fields. Use `--clear-due` or `--clear-follow-up` only when removing those dates is intended. Dependencies must identify existing task IDs. Record an external tracker URL with `--external`; that tracker remains authoritative for its own issue state.
7. Read the saved record using `task show ID`. Report success only after the command succeeds and the returned record matches the intent.

Example:

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace work task add "Confirm the rollout window" --source "User: confirm the rollout window" --next-action "Ask the service owner for available windows" --kind commitment --priority normal --key "session-42:item-1"
```

Mark a task `done` only when the user reports completion or observed evidence establishes its outcome. Supply `--evidence` describing that evidence, including non-code outcomes where applicable. A passing build, a checkpoint, an open PR, or a closed external issue alone does not prove every task complete. Never close external issues as part of saving local progress.

Reply with task IDs, the captured next actions, and any due/follow-up dates. Distinguish ideas, commitments, and waiting work plainly.
