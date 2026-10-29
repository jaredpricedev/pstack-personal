---
name: resume-app
description: "Resume a registered app from saved checkpoints, decisions, tasks, and reviews. Use for /resume-app, 'where did I leave off', or continuing work on an app."
---

# Resume an app

Recover the resume point without rebuilding the project history from scratch.

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute file location and run it with Python 3.10 or later. Use one selected workspace and put home/workspace flags before the command.

1. Resolve the app ID from the request or `app list`. Ask only when identity is genuinely ambiguous. If it is unregistered, route through setup-organizer using known facts.
2. Run `resume APP`. Read the app profile, latest checkpoint, open tasks, latest review, their timestamps, evidence, and decisions. Saved claims describe the recorded moment, not guaranteed current live state.
3. If a branch, commit, PR, or ticket matters to the next action, inspect that exact artifact read-only. For a local checkout, check its actual path, current branch, worktree changes, and relevant diff before editing. Never reset or switch away from uncommitted work to match a stale checkpoint.
4. Reconcile differences explicitly. Preserve useful prior evidence, but update stale claims with current observations. Do not mark tasks done or overwrite the next action merely because a checkpoint sounds complete.
5. Return a concise resume brief: goal, last verified result, current branch/PR if known, unresolved decisions or blockers, and the next concrete action. If no checkpoint exists, say so and use the profile/tasks instead.
6. If the user requested execution, continue within their authorized scope. Locate installed upstream pstack by plugin name/manifest using the host's skill discovery; do not assume its files are a sibling directory. Use an appropriate pstack workflow if available. Otherwise proceed with the host's normal engineering tools and explain any missing capability that affects the outcome.

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace personal resume service-a
```

Do not search unrelated project transcripts or all repositories to compensate for a missing checkpoint. Ask for missing material context or make a narrow inspection of the registered app. Save meaningful progress through close-session at a safe boundary.
