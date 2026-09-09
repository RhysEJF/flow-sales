---
name: start
description: The first thing to run after installing FlowSales, or whenever someone says "set up FlowSales", "get started", "how do I use this". Checks the machine, explains the loop in five lines, and walks straight into setup (demo data or your own). Safe to run any time; it reads and asks, it never scores or pulls on its own.
argument-hint: "[--demo]"
---

You are welcoming someone to FlowSales. They may be a rep who wants the morning briefing, or the person who runs sales ops. They may be in Claude Code or in the Claude desktop app. Assume nothing about what they know. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse). Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## 1. Check the machine, quietly

Run `fs.py doctor --json` (it works before a store exists). If Python is missing or older than 3.10, say so in one line with the fix and stop: nothing else can run. If it passes, do not list the checks; just carry on.

Run `fs.py status --json`. If a store already exists in this folder, say what is in it in one line (deals, interactions, last audit) and skip to step 3.

## 2. Say what this is, in five lines

Plain words, no bullets longer than a line:

FlowSales reads your CRM and your call transcripts, scores every call and email against MEDDPICC with the buyer's own words as evidence, and shows each rep and the team how much of the framework they actually use, week by week, and what it changes on won and lost deals. Six commands: `setup` once, `audit` for the benchmark and then weekly, `daily-sync` every morning for a rep, `retro` every week, `impact` for the quarter, `status` whenever in doubt. Everything stays on this machine except the text sent to the model for scoring. Nobody needs a token: you sign in to HubSpot as yourself. A team shares judged deals through a folder it already syncs, so a deal is judged once.

## 3. Ask one question (gate)

"Where do you want to start?" Options: see it on fictional data first (two minutes of setup, then an audit of about seven minutes); connect my own data now; just show me the commands.

- Fictional data, or `$ARGUMENTS` contains `--demo`: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/SKILL.md` and follow it with `--demo`. When it finishes, offer `/flow-sales:audit` and say what it will do and how long it takes.
- Own data: read `${CLAUDE_PLUGIN_ROOT}/skills/setup/SKILL.md` and follow it from gate 1. Say first that it asks who they are, whether the reps have been told, and who will see the report, before it connects anything.
- Just the commands: print the six commands with one line each and the moment to run them, then stop.

Plain language, no em dashes. Never write to the CRM.
