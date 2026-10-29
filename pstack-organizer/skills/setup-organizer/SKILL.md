---
name: setup-organizer
description: "Set up a durable app registry and task workspace. Use for /setup-organizer, registering an app, or configuring pstack-organizer for work or personal projects."
---

# Set up the organizer

Create a small registry that future sessions can use without searching old chats.

Read [state and workflows](../../references/state-and-workflows.md). Resolve `../../scripts/organizer.py` from this skill's absolute file location. Call that absolute path with Python 3.10 or later. Put global `--home` and `--workspace` flags before the command. Never assume the current directory is the plugin directory.

1. Select the workspace from the user's request or `PSTACK_ORGANIZER_WORKSPACE`. Otherwise use `personal`. Keep work environments with different access boundaries in separate stores; never copy records between them implicitly. Use the configured `PSTACK_ORGANIZER_HOME`, or the runtime's external default. Store no state in a plugin checkout.
2. Run `init`. Report the returned store location and selected workspace briefly. A repeat setup must preserve existing records.
3. Ask which apps to register only if the user has not identified them. Use supplied repositories or an explicitly selected repository list. Read current metadata through available connectors or authorized forge CLIs. Do not enumerate unrelated repositories or mine every workspace's chats.
4. Run `app list` before adding records. Use a stable lowercase ID for each app. Register its name, purpose, repository URLs, and optional local checkout path. A project can have several repositories. A non-code area can be registered without one.
5. Capture known stage, next action, constraints, verification instructions, and maintenance instructions. Use `app update` for later changes; omitted fields stay intact. Do not invent deadlines, successful checks, deployment access, or maintenance commands.
6. Read each saved app back with `app show ID`. Leave suggested future work out of the commitment ledger unless the user committed to it. Use the capture-task skill for requested tasks.

Example with an already selected workspace and app:

```sh
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace personal init
python3 "/absolute/plugin/root/scripts/organizer.py" --workspace personal app add service-a --name "Service A" --purpose "Internal service health" --repo "https://github.com/example/service-a" --stage active --next-action "Reproduce the reported timeout" --verify "Exercise a real request and inspect the response" --maintenance "Review failed checks and open security reports"
```

Connectors and upstream pstack are optional for local organization. If a connector is unavailable, register the information supplied and label live state unverified. Never publish registry contents, private repository metadata, or task records in the plugin source.

Reply with the selected workspace, registered app IDs, missing information that matters, and the first useful command (`today`, `resume-app`, or `capture-task`). Do not claim installation in another editor or automatic background operation.
