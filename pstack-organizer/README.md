# pstack organizer

Build and maintain several apps while keeping work commitments, decisions, and next steps together across sessions. This companion adds durable organization to [pstack](../pstack/) without changing its engineering workflows.

The organizer works offline with Python 3.10 or newer and its standard library. Agent skills turn ordinary requests into updates to a local SQLite store. The CLI works independently of any agent or plugin host.

## Install

### Grok Bot

Use the [Grok Bot setup guide](docs/grok-bot.md). It runs the CLI on the Bot's cloud computer and saves a private skill that loads the organizer workflows. Keep its data under `/workspace/pstack-organizer-data`, outside the checkout, and invoke the saved skill by name. This is a CLI plus private-skill setup; native GitHub-plugin import in Grok Bot has not been verified.

### Cursor

For a local installation, clone this fork and copy the companion into Cursor's local plugin directory:

```bash
git clone https://github.com/jaredpricedev/pstack-personal.git
mkdir -p ~/.cursor/plugins/local
test ! -e ~/.cursor/plugins/local/pstack-organizer && \
  cp -R "$PWD/pstack-personal/pstack-organizer" ~/.cursor/plugins/local/pstack-organizer
```

Reload Cursor after copying. Cursor skips symlinks whose targets are outside its local plugin directory. If local plugin imports are disabled by your organization, use its approved marketplace process. If the destination already exists, the command leaves it alone; review it before updating. On Windows, copy the `pstack-organizer` folder to your user profile's `.cursor/plugins/local/` directory.

Keep your existing pstack installation for engineering work. If it is not installed, install pstack from the official marketplace. The organizer itself does not require pstack; `jared-mode` uses it when you request implementation work.

### Claude Code

This fork has its own marketplace name so it can coexist with the upstream marketplace:

```text
/plugin marketplace add jaredpricedev/pstack-personal
/plugin install pstack-organizer@pstack-personal
```

Claude Code prefixes the commands, for example `/pstack-organizer:today` and `/pstack-organizer:jared-mode`. Install the base pstack plugin separately if you want to use its engineering playbooks. For a temporary local session, Claude Code can load the `pstack-organizer` directory as a plugin directory.

Plugin packaging is provided for Cursor and Claude Code. Grok Bot can use the CLI and a private skill as described above. Installing this repository does not add persistent memory to ChatGPT.

## Start using it

Run `/setup-organizer` to register the apps you want to track. It records current repository links and your verification instructions in your local workspace. It does not infer a backlog from old conversations or scan every repository in your account.

| Command | Result |
| --- | --- |
| `/morning` | Review recorded app progress, today's priorities, due follow-ups, and work notes to revisit. |
| `/remember-work` | Save or recall work facts, decisions, and context with their sources. |
| `/capture-task` | Save an explicit commitment, idea, blocker, or follow-up, with its source. |
| `/today` | Get a short worklist with reasons, plus overdue work and follow-ups. |
| `/resume-app` | Recover an app's checkpoint, open work, evidence, and next action. |
| `/maintain-app` | Review the selected app using available repository tools and its maintenance profile. |
| `/close-session` | Save progress, decisions, verification evidence, and unfinished commitments. |
| `/jared-mode` | Combine these workflows with pstack while the mode is active. |

For a daily conversation, start with **“Good morning. Catch me up on my apps and work.”** In Grok Bot, ask **“Use Personal App Organizer for my morning check-in.”** It starts with a short briefing, accepts new updates, and helps you choose what to build or maintain next. The check-in reads saved records first; it reports live checks only when they were actually performed. Starting the briefing does not automatically execute the recommended tasks.

Examples you can say to the agent:

```text
/capture-task Remind me to ask the architect about the deployment constraint.
/capture-task This dashboard redesign is an idea, not a commitment yet.
/remember-work We chose the simpler API so operators can inspect the result directly.
/morning I have 90 minutes. Catch me up before we start.
/today I have 90 minutes. What should I work on?
/resume-app demo
/maintain-app demo Review open PRs and what needs verification.
/jared-mode Finish this fix and record the follow-up work before closing out.
```

Capture saves a record. It does not create a timed reminder. `jared-mode` captures explicit loose ends and writes checkpoints at safe boundaries while it remains in context. A standalone `/poteto-mode` session does not automatically invoke the organizer. There are no background hooks or scheduled jobs in this plugin.

Work notes are separate from tasks. Each note retains its source and can be attached to an app or left as general work context. Corrections supersede an earlier note while preserving its history; archived and superseded notes stay out of normal recall. A review date means “revisit this detail,” not that the detail expires or a notification is scheduled.

## Local CLI

Run these commands from the `pstack-organizer` directory of your checkout. From another working directory, use the script's absolute path. Global flags go before the command.

```bash
python3 scripts/organizer.py init
python3 scripts/organizer.py app add demo \
  --name 'Demo app' --purpose 'An example project' \
  --repo https://github.com/example/demo \
  --verify 'Run the project tests, then exercise the changed behavior.'
python3 scripts/organizer.py task add 'Exercise the recovery path' \
  --app demo --source 'User request in the current session' \
  --next-action 'Reproduce the failed startup in a disposable lab' \
  --estimate 45 --key demo-recovery
python3 scripts/organizer.py today --minutes 90
python3 scripts/organizer.py checkpoint add demo \
  --summary 'Reproduced startup failure; fix remains to be implemented' \
  --next-action 'Implement the smallest fix and rerun the reproduction' \
  --branch fix/startup --evidence 'Lab reproduction reproduced the failure'
python3 scripts/organizer.py resume demo
python3 scripts/organizer.py note add 'API decision' \
  --kind decision --app demo \
  --body 'Keep one inspectable endpoint for the first release.' \
  --source 'User decision in the current session' --key demo-api-decision
python3 scripts/organizer.py note list --app demo --query endpoint
python3 scripts/organizer.py morning --minutes 90
```

All successful commands return JSON. Use `--help` at any level for the complete interface. The runtime never executes a saved verification or maintenance instruction and never connects to GitHub, GitLab, Jira, or a cluster. `maintain-app` uses the host agent's available tools and records its findings through the CLI. Missing access is reported as unknown, never healthy.

## Workspaces and storage

The default store is `~/.local/share/pstack-organizer/personal/`. Choose a different root with `PSTACK_ORGANIZER_HOME` or `--home`, and a workspace with `PSTACK_ORGANIZER_WORKSPACE` or `--workspace`.

```bash
python3 scripts/organizer.py --workspace work init
python3 scripts/organizer.py --workspace work today
```

Workspaces have separate databases. Keep work records in their approved environment and personal records on your own machine. Workspace separation is organizational, not an access-control boundary or encryption mechanism. The directory and database use private permissions where supported by the operating system. There is no automatic cloud synchronization.

After updating from version 0.1.0, run `init` with the same home and workspace to upgrade the existing store to schema version 2. This preserves apps, tasks, checkpoints, reviews, and capture keys. Commands encountering an older store ask for this explicit upgrade. New exports include work notes; imports also accept version-one snapshots into an empty version-two workspace.

The store is independent of the plugin checkout, so replacing or updating the plugin preserves your records. Do not put a data root or export in this public fork. The runtime rejects stores inside this repository. Check the selected workspace before capturing or exporting data.

Export a snapshot and import it into an initialized, empty workspace on another machine:

```bash
python3 scripts/organizer.py export > /private/location/organizer-snapshot.json
python3 scripts/organizer.py --workspace restored init
python3 scripts/organizer.py --workspace restored import \
  --file /private/location/organizer-snapshot.json
```

Exports contain your task content and repository references. Store them with the same care as the original records. Imports validate the snapshot and refuse to overwrite an existing nonempty workspace. The database remains authoritative; exports are snapshots, not a second live task ledger.

## How planning works

Ideas remain separate from commitments. An unfinished dependency, a paused or archived app, or an explicit waiting/blocked status keeps a task out of the actionable shortlist. Overdue work stays visible even when it cannot be selected. Follow-up dates are distinct from due dates. A due date is only set when you provide one.

The planner ranks actionable work by due date, work already underway, priority, and age. It respects the requested item limit and estimated time budget. Reasons accompany the selections. The 30-minute default estimate is a planning placeholder, not a measured duration; change it when you know more. Suggestions do not change task states. Completing a task requires evidence, including a concrete outcome for noncoding work.

See [state and workflow rules](references/state-and-workflows.md) for capture, freshness, and external tracker behavior.

## Development and upstream updates

```bash
python3 -m unittest discover -s pstack-organizer/tests -v
python3 pstack-organizer/scripts/validate_plugin.py
node scripts/generate-pstack-harness-trees.mjs --check
```

Run those commands from the repository root. The organizer CI runs the Python checks without installing third-party Python packages. The upstream plugin validator additionally uses `ajv` and `ajv-formats` as in the existing workflow.

Changes to the companion live in `pstack-organizer/`; upstream `pstack/` and its generated harness remain unchanged. To bring in upstream changes, add `https://github.com/cursor/plugins.git` as the `upstream` remote, fetch it, and merge `upstream/main` on a review branch. Preserve this fork's marketplace name and organizer entries when resolving manifest conflicts.

Sources for host installation behavior: [Cursor plugins](https://cursor.com/docs/plugins), [Claude Code plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).
