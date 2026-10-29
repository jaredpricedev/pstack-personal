---
name: jared-mode
description: "Work across apps with durable task capture and verified session handoffs, routing engineering execution through pstack when available. Use for /jared-mode or a request to keep the user's app work organized while executing it."
---

# Jared mode

Keep useful project state while carrying the user's requested work through to a reviewable outcome.

Read [state and workflows](../../references/state-and-workflows.md). Resolve companion skills by their names within this plugin. Their script path is `../../scripts/organizer.py` relative to each loaded skill file; do not use a current-directory assumption.

1. Pin one workspace and the current app, if any. Use setup-organizer when no store or app exists. Keep separate environments separate. Read the saved resume point before app work; do not repeatedly mine old chats after the ledger supplies enough context.
2. Route organization requests to the appropriate companion workflow:

   | Request | Workflow |
   | --- | --- |
   | Register apps or configure a workspace | setup-organizer |
   | Remember a commitment, idea, or follow-up | capture-task |
   | Choose today's next actions | today |
   | Continue a project | resume-app |
   | Review maintenance needs | maintain-app |
   | Save progress or switch projects | close-session |

3. For engineering execution, locate installed upstream pstack using the host's plugin/skill discovery and its manifest name. Read its relevant workflow before using it. Do not assume a sibling `pstack/` directory exists after installation. If pstack is absent, use the host's ordinary engineering tools; local organizer functions remain available.
4. Carry out authorized work with the project's constraints and verification profile. Prefer a concrete next action to a broad new plan. Ask only for material missing intent, access, or an action that requires permission. Do not infer authority to deploy, merge, send messages, or widen access from a maintenance profile.
5. During the active mode, capture explicit commitments and loose ends at safe boundaries. Distinguish suggestions from promises. Include provenance, avoid duplicate records, and do not invent deadlines or completion. Do not let an optional organizer update block urgent work; report a failed save and retry at the next safe boundary.
6. Save a handoff through close-session after meaningful progress, before a project switch, and before the final response when app state changed. Update only facts established by the session. Keep the next action useful even when work is blocked or incomplete.
7. Reply plainly with the outcome, relevant evidence, remaining work, and saved task/checkpoint references. State any persistence failure directly. Keep routine implementation detail out of the user's planning view.

Automatic capture and handoffs apply only while this mode is active in the host's context. They are agent workflow instructions, not installed event hooks, background monitoring, scheduled reminders, or memory shared automatically with ChatGPT or another machine. Use the host's supported persistent mode feature when available; otherwise invoke this skill on each session that should use it.
