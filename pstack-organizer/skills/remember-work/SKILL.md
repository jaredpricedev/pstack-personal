---
name: remember-work
description: "Remember and recall work facts, decisions, and context across sessions. Use for /remember-work, 'remember that', 'what did we decide', or correcting a saved work detail; route actions and deadlines to capture-task."
---

# Remember work context

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute path. Use Python 3.10+ and put the selected home/workspace flags before each command. In Grok Bot use the configured home under `/workspace`, not the generic desktop default.

1. Separate intent from information. An action such as “ask the owner” is a task for capture-task. A fact, decision, or useful explanation is a note. Save both only when the user supplied both. Do not invent tasks from informational notes.
2. Resolve the workspace and optional app. Work details can remain unassigned. Initialize through setup-organizer if needed; an existing version-one store needs `init` to upgrade before continuing. Never mix stores implicitly.
3. Search `note list --query TEXT`, optionally scoped with `--app`, before capturing. Use several short searches when needed because the query is a literal substring, not semantic search. For recall, return the relevant current notes with their IDs, sources, and dates. State missing or uncertain evidence rather than reconstructing a decision as fact from an old chat.
4. Save `note add TITLE --body TEXT --source TEXT`, with `--kind fact`, `decision`, or `context` as appropriate. Attribute user reports to the user; a stored note is not independent proof. Record only useful requested context, without credentials or unnecessary raw conversation history. Supply a stable `--key` for retried captures.
5. A correction is a new note using `--supersedes NOTE_ID`. Read the original first, confirm the topic and app match, and retain its history. Read back both records to confirm that the new version is current and the old version superseded. Do not overwrite an unrelated note that happens to share a word.
6. Set `--review-on YYYY-MM-DD` only when the user asks to revisit a detail. Resolve relative dates in the user's timezone. A review date prompts reconsideration during a check-in; it does not establish expiration or schedule a notification. Use `note archive ID` when the user asks to retire a detail; archived records remain in history.
7. Read the saved record with `note show ID`. Report the saved meaning and ID briefly. If persistence fails, say it was not saved. Do not promise memory across devices or access to notes in another environment.

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace work note add "Preferred review window" --body "User reports that service reviews should happen before the weekly planning meeting." --kind context --source "User statement in this session" --key "session-42:review-window"
```

Keep current notes distinct from commitments, suggestions, and independently verified observations. Recheck the authoritative source before acting when a remembered detail may have changed.
