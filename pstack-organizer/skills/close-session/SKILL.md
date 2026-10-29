---
name: close-session
description: "Save durable progress, decisions, evidence, and a resume point for an app. Use for /close-session, wrapping up work, switching projects, or a safe checkpoint during jared-mode."
---

# Save a session handoff

Leave enough verified state for another session to continue.

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute file location and run it with Python 3.10 or later. Use the selected workspace, with home/workspace flags before the command.

1. Resolve the registered app and read `resume APP`. Summarize this session's actual changes, outcomes, decisions, and unfinished actions. Keep attempted checks distinct from passing checks.
2. Inspect relevant local state or live artifacts read-only. Record the branch, exact commit, PR link, uncommitted changes, and check evidence only when observed. Do not create commits, push, merge, or stop running processes merely to write a handoff.
3. Reconcile task updates with the outcome. Mark a task done only for an observed result or the user's explicit completion report, using `task update ID --status done --evidence TEXT`. Leave partial work open with a concrete next action. Use capture-task for explicit new loose ends; preserve optional ideas as ideas and avoid duplicates.
4. Save `checkpoint add APP --summary TEXT --next-action TEXT`. Include known `--branch`, `--commit`, `--pr`, and repeated `--evidence` or `--decision` fields. Name uncertainty and blockers in the summary. A “verified” assertion must point to what was actually checked.
5. Supply a stable `--key` if the same checkpoint command may be retried. Read `resume APP` afterward and confirm the checkpoint was saved. If persistence fails, say the handoff was not saved and include the essential resume text in the reply; do not claim durable memory.

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace personal checkpoint add service-a --summary "Timeout reproduced; fix not implemented" --next-action "Inspect the retry deadline calculation" --branch "fix/request-timeout" --evidence "Local reproduction command returned the expected timeout" --decision "Keep the public request interface unchanged" --key "session-42:handoff-1"
```

For general tasks without a registered app, update their records directly and report their IDs rather than inventing an app checkpoint. Never copy private records into the public plugin repository or another workspace for convenience.

Reply with what was saved, what remains open, and the first action on resume. This workflow saves state only when invoked or routed to during an active mode; it cannot catch a forcibly terminated editor process or run after the session ends.
