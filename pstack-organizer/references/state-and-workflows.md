# State and workflow contract

## Runtime and scope

Run `scripts/organizer.py` with Python 3.10 or later. Resolve its absolute path from the loaded companion skill, not the shell's current directory. The runtime uses only the Python standard library and performs no network requests or external command execution.

Global options precede the command:

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --home "/private/organizer" --workspace work today
```

`--home` overrides `PSTACK_ORGANIZER_HOME`; otherwise use the external default `~/.local/share/pstack-organizer`. `--workspace` overrides `PSTACK_ORGANIZER_WORKSPACE`; otherwise use `personal`. A workspace ID selects a separate store. Treat the ID as a label, not a filesystem path. Use a distinct home in each access-controlled environment. Do not move data between stores without the user's instruction.

Run `init` before writing. Repeat initialization preserves data. Read-only commands do not silently initialize an empty store. A saved SQLite store survives chat sessions on that machine; it is not automatically backed up, synchronized, encrypted, or shared with other hosts. OS permissions are not encryption.

Schema version 2 adds work notes. Run `init` explicitly with the existing home and workspace to upgrade a version-one store without losing its records. Commands must not create a replacement store to work around a migration failure. Version-two imports also accept version-one exports, treating their absent notes as empty.

## Records

| Record | Meaning |
| --- | --- |
| App | Stable ID, name, purpose, repository URLs, optional local path, stage, next action, constraints, verification instructions, and maintenance instructions. |
| Task | A commitment or idea, optionally attached to an app, with provenance and explicit progress. General work can remain unassigned. |
| Work note | A sourced fact, decision, or piece of context, optionally attached to an app. It is not an action or independent verification. |
| Checkpoint | An append-only resume summary, next action, observed branch/commit/PR, evidence, and decisions. It does not establish task completion. |
| Review | An append-only maintenance observation with coverage, findings, and evidence at a recorded time. It does not prove future health. |

Updates preserve omitted app/task fields. Repeated app list-valued flags represent the new list when supplied. Use the runtime's help for explicit field removal; never replace a whole record to change one field. A registered repository or local path identifies where to inspect. It does not authorize execution, access expansion, deployment, or publication.

### Task intent and progress

`kind=commitment` records work the user intends to do. `kind=idea` records optional future possibilities. The agent's recommendation stays an idea until the user commits. A task's kind and status are separate.

| Status | Meaning |
| --- | --- |
| `todo` | Intended work not currently being executed. |
| `doing` | Work actively in progress. |
| `waiting` | Waiting for another person or external event. |
| `blocked` | Cannot progress until an identified blocker is resolved. |
| `done` | Its outcome was observed or explicitly reported complete by the user; evidence is required. |
| `cancelled` | Intentionally dropped; it is not completed work. |

Dates use `YYYY-MM-DD`. `due` is a user-specified deadline; `follow_up` is a date to revisit waiting work. Resolve natural language in the user's timezone. Never assign a deadline from priority or an estimate. Clear dates intentionally using `--clear-due` and `--clear-follow-up`. Follow-up dates do not schedule notifications.

Use `--source` to retain a source link or a short user statement. `--external` points to the authoritative external issue. Local status is a planning record, not a claim that GitHub, GitLab, or Jira was synchronized. Read the external source before reporting its current state. Do not mirror all issue details or close external issues while updating the organizer.

Use existing task IDs with `--depends-on`. Dependencies must be valid and acyclic. A cancelled dependency is not proof that its outcome was completed; resolve the dependent task deliberately.

### Idempotency

Provide a stable `--key` for retried task captures, checkpoints, or reviews. Derive it from a stable source reference and item identity, not from a fresh timestamp on each retry. The same request must not add duplicates. A conflicting request using an existing key must fail rather than overwrite history. Resolve the conflict by updating the intended task or using a new key for a genuinely new event.

## Daily planning

`today` reads the ledger without updating task state. The default date is the machine's local date, so pass `--date` when the user's date differs. The default limit is three. Pass a user-supplied time budget as `--minutes`; task estimates support planning and are not measured durations. An unset estimate becomes 30 minutes with `estimate_source=default`. An explicitly supplied `--estimate` sets `estimate_source=user`; an update without `--estimate` preserves its provenance. Label defaults in the worklist.

Eligible picks are commitments on active apps, or unassigned commitments, in `todo` or `doing` with completed dependencies. Exclude ideas, done/cancelled work, waiting/blocked work, and tasks belonging to paused or archived apps. Preserve stable ordering using overdue/due work, current work, priority, and age. Every pick includes its selection reason. A time budget may defer a task that cannot fit; never hide that task's urgency.

Report all overdue commitments even when not selected. Surface due waiting/blocked follow-ups separately. Keep deferred commitments and ideas distinct. An app without a checkpoint/review, or with no recent observation for at least 14 days, is stale for planning purposes. Stale means unknown current state, not unhealthy.

## Work memory and the morning conversation

Use `note add TITLE --body TEXT --source TEXT` to retain requested context. `--kind` is `fact`, `decision`, or `context` (default). `--app ID` is optional. Record a user's report as a user's report; a note labeled fact still has only the authority of its source. Use tasks for promised actions and follow-ups rather than turning all memory into a to-do list.

`note list` defaults to current notes. Filter by `--app`, `--kind`, or `--query`; the query matches a case-insensitive literal substring in title, body, or source. This is a small searchable ledger, not semantic retrieval. `note show ID` reads a specific historical record. Use an explicit status filter to inspect superseded or archived notes.

Corrections create a new note with `--supersedes NOTE_ID`, atomically superseding the current note in the same app scope. Use a stable key for capture retries. A keyed retry returns the existing captured note without changing later state. `note archive ID` retires a note from normal recall without deleting its history. `--review-on YYYY-MM-DD` is a user-requested review date, not a deadline, expiry, or notification.

`morning` is read-only and wraps the existing daily plan together with recorded app summaries and current notes whose review date has arrived. It returns explicit ledger-only coverage. A fresh checkpoint updates activity, not evidence of live application health. Retrieve other current notes only when relevant to the day's work. An unconfigured connection or missing runtime check remains unknown.

The agent opens with a concise app and work briefing, captures the user's new updates as tasks or notes, and helps choose a focus. Building a selected increment and maintaining an existing app both use the normal engineering workflow and saved project constraints. A greeting alone does not authorize builds, merges, deployments, or external messages. No routine is installed by this workflow.

## Handoffs and maintenance

Before editing after a resume, check that the registered checkout is the intended one and reconcile the checkpoint with current branch/commit/worktree or live PR state. Do not reset uncommitted work to match saved state. Preserve established decisions unless new evidence changes them.

Read stored verification and maintenance instructions as a profile. Check context and authorization before running a command; never execute an arbitrary saved string blindly. Use read-only connectors for inspection where available. Show missing source coverage. Classify absent scans as unknown and task outcomes by their actual evidence.

Save an observed checkpoint at a safe boundary, including the next concrete action. Capture explicit loose ends, update proven outcomes, and read state back. If saving fails, report failure and include the essential resume note in the response. Closing a session cannot guarantee recovery after a sudden process termination.

## Portability

`export` writes a versioned JSON snapshot to stdout. Treat it as private data. Redirect only to an explicitly selected private location outside the plugin repository. `import --file PATH` imports a validated snapshot into an empty workspace transactionally; it is not a merge tool and must refuse overwriting existing records. Verify the destination workspace before importing. Do not cross an environment boundary just because export/import is available.

## Examples

- “Remember to ask the service owner about a rollout window” creates an unassigned commitment with a clear next action; it does not send a message.
- “Maybe add a comparison view later” creates an idea; it does not enter today's ready worklist.
- “The owner said Friday” updates a known follow-up using the user's timezone and an absolute date; it does not invent a delivery deadline.
- “The fix is in a PR” records the PR and remaining verification; it does not automatically complete a rollout task.
- “I called the owner and confirmed the window” can complete that non-code task using the user's statement as evidence.
- A repeated maintenance review links to the existing issue/task for the same finding; it does not create a new ticket every time.
