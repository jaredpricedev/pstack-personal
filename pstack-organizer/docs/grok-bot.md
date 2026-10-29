# Set up pstack organizer in Grok Bot

Run the existing CLI on Grok Bot's cloud computer and save a private skill that loads the local workflows. This adapts the organizer to Grok Bot's documented command-line and private-skill capabilities. It has not been exercised in a live Grok Bot session, and it does not assume native GitHub-plugin import or Cursor/Claude slash commands are available there.

## Ask your Bot to set it up

Paste this into the Grok Bot you want to use:

```text
Set up pstack organizer from https://github.com/jaredpricedev/pstack-personal on your cloud computer.

Clone the repository into /workspace/pstack-personal if that path is unused. If it already exists, inspect it and preserve local changes. Read pstack-organizer/README.md and pstack-organizer/docs/grok-bot.md before setup. Check that Python 3.10+ is available, inspect the organizer script, and run its integration tests.

Use /workspace/pstack-organizer-data as the data home and personal as the workspace. Always pass both flags explicitly before every CLI subcommand. Initialize the store without inventing any tasks or importing my other repositories.

Save a private skill named Personal App Organizer. Its instructions should load /workspace/pstack-personal/pstack-organizer/skills/jared-mode/SKILL.md and its referenced companion workflows on each invocation. Retain the absolute script path and explicit data-home/workspace flags in that skill. Use the current conversation's date and timezone for planning.

Test persistence with a clearly labeled sample in a separate install-check workspace: capture one task, then read it with a separate CLI invocation. Keep the sample out of personal. Report the installed commit, Python version, test outcome, data location, and saved private-skill name. If a step is unavailable, say what failed instead of claiming setup completed.
```

This creates local organizer records and a reusable private skill. It does not publish a skill, create scheduled routines, register your apps automatically, or install the separate upstream pstack workflows.

## CLI paths to retain in the private skill

The Bot should run commands on its cloud computer, using the full script path and explicit storage selection:

```bash
python3 /workspace/pstack-personal/pstack-organizer/scripts/organizer.py \
  --home /workspace/pstack-organizer-data --workspace personal init

python3 /workspace/pstack-personal/pstack-organizer/scripts/organizer.py \
  --home /workspace/pstack-organizer-data --workspace personal app list

python3 /workspace/pstack-personal/pstack-organizer/scripts/organizer.py \
  --home /workspace/pstack-organizer-data --workspace personal today
```

Run the tests from the checkout root:

```bash
python3 -m unittest discover -s /workspace/pstack-personal/pstack-organizer/tests -v
```

The CLI uses Python's standard library; no pip packages or virtual environment are required. If Python 3.10+ is missing, report that requirement and use the environment's supported installation process. Do not claim success from reading the instructions alone.

## Use the saved skill

Ask by name rather than assuming `/today` or `/plugin` commands are registered:

```text
Use Personal App Organizer to register the apps I select.
Use Personal App Organizer to remember that I need to ask about the rollout window.
Use Personal App Organizer to plan my next 90 minutes.
Use Personal App Organizer to resume service-a.
Use Personal App Organizer to save where we stopped.
```

If the Bot cannot find the saved skill, open **Connect apps**, select the connected count beside the title, and enable it for that Bot under **Private skills**. Successful setup includes actually saving the skill through Grok Bot's skill capability; a file in the checkout alone does not establish that it is available in the app.

Use the setup workflow to register only your selected apps. Maintenance reviews need the relevant connected repository apps or authorized command-line access. Missing access must be reported as unknown. When upstream pstack is not installed, the companion can still organize work and use the host's ordinary engineering tools.

## Keep records durable

Grok Bot documents `/workspace` as its location for durable project files. Use the explicit data home above instead of relying on the CLI's generic `~/.local/share` default. Keep the checkout and task store separate so updating source does not replace your records.

All Bots on the same account share a cloud computer and its files. Workspace labels separate planning records, not access permissions. Keep enclave work in its approved environment rather than treating another Bot as an isolated work machine.

For a portable snapshot, ask the Bot to run `export` with the same explicit flags and save the JSON to a private location under `/workspace` outside the checkout. The existing [export/import workflow](../README.md#workspaces-and-storage) applies. A snapshot is not a second live ledger. Updates or recovery can interrupt running work and lose very recent changes, so do not promise lossless recovery from a chat summary or an unsaved session.

Do not schedule anything during installation. If you later request a daily brief, Grok Bot can create a routine that invokes this private skill with the same data home and workspace. Check the routine's saved timezone and run it once before relying on it.

## Update or recover

Keep the private skill's source path stable. Before updating the checkout, inspect local changes and record the current commit; do not overwrite local work. Updates to this plugin do not require moving or reinitializing its data store. After recovery, verify that the checkout, data store, Python runtime, and private skill are present before resuming work. Reinstall any missing runtime through the supported process and restore records from a chosen snapshot only when needed; do not silently start a fresh empty ledger.

## Official host documentation

- [Grok Bot computer, apps, and durable workspace](https://docs.x.ai/grok-bot/computer-and-apps)
- [Private skills and routines](https://docs.x.ai/grok-bot/skills-routines-and-automations)

These sources describe Grok Bot's host capabilities. The organizer paths, wrapper skill, and validation steps above are this project's integration recipe, not a vendor-provided plugin installer.
