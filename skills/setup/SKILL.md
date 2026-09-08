---
name: setup
description: Connect FlowSales to your data (HubSpot, Granola, a folder of Gong, Fireflies or Fathom transcripts, a CSV export from Salesforce or any other CRM, or the demo dataset), agree who will see the report and what may be read, choose the framework and time window, map pipeline stages, pick reps and a training date, and pull the first data. Run this once per project directory before audit.
disable-model-invocation: true
argument-hint: "[--demo]"
---

You are running FlowSales setup for the user. Everything is local: the store is `.flow-sales/` in the current directory. Ask with AskUserQuestion at every gate below, one gate at a time, and never guess a token, a path or a date. Use the CLI at `${CLAUDE_PLUGIN_ROOT}/scripts/fs.py` (call it as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py" ...`; add `--json` when you need to parse output). If `$ARGUMENTS` contains `--demo`, skip gates 2, 3 and 5 entirely, use the demo dataset, and say so in one line.

Say what each step does before you ask its question. The person running this is usually the ops or RevOps person, not a rep, and often not the person who chose the tool.

## 1. Create the store

Run `fs.py init`. Tell the user where the store is, that it is git-ignored, and that nothing in it leaves the machine except the interaction text sent to the model during audit.

## 2. Who sees this, and do the reps know (gate)

Before connecting anything, ask two questions in one call:

1. "Have the reps been told that FlowSales will read their calls, emails and notes and score them against the framework?" Options: yes, they know; not yet, I will tell them before the first audit; this is a pilot on my own deals only.
2. "Who will see the finished report?" Options: only me; sales managers; the reps, each their own page; leadership or the board too.

Record the answers with `fs.py config set consent.repsInformed <true|false|"pilot">` and `fs.py config set consent.audience "<answer>"`. If the reps have not been told, say plainly that the report names every rep next to their weakest elements, recommend switching anonymised names on for the first run (gate 5 below), and mention that the report's Export menu has a names-hidden Impact export for anyone outside the sales team. If leadership will see it, say the same thing about the export.

## 3. Sources (gate, multi-select)

Ask which sources to connect:
- HubSpot (deals, contacts, calls, emails, meetings, notes; read-only)
- Granola (meeting notes and transcripts)
- A folder of call transcripts from Gong, Fireflies, Fathom or Google Meet (.md, .txt, .vtt, .json exports)
- A CSV export from Salesforce, Pipedrive or any other CRM (two files, see docs/other-crms.md; the report is the same as with HubSpot)
- The demo dataset (32 fictional deals, 4 reps, no connection needed)

If the user is on HubSpot, say that HubSpot does not hand over call transcripts through its API, so the calls themselves come from Granola or the transcripts folder; without either, scores rest on emails, notes and meeting summaries and the report says so.

## 4. Framework and window (gate)

Ask two questions in one call: framework (MEDDPICC, recommended; or MEDDIC, six elements) and window (last quarter, last 6 months, last 12 months, or custom dates). Apply with `fs.py config set framework "meddpicc"` and `fs.py config set window '{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}'`.

## 5. Connect each chosen source, one at a time

**HubSpot.** Run `fs.py doctor --source hubspot --json`. If the token is missing, say that this is the one step that usually needs the HubSpot admin, and give them the exact page: Settings, Integrations, Private Apps, Create a private app, then the six read scopes listed in `docs/hubspot.md` (deals, contacts, companies, owners, deal schemas, sales email; nothing with write). Explain the three places the token can live in plain terms: an environment variable (set once per terminal session, nothing on disk), the plugin option `hubspot_token` (set with `/plugin configure flow-sales`, stored by Claude Code), or `.flow-sales/secrets.json` in this folder with permissions 600 (simplest; keep the folder out of git). Ask which they want; then wait (tell them to type `! export HUBSPOT_ACCESS_TOKEN=...` or restart the session) or take the pasted token and write `secrets.json` with `{"hubspot_token": "..."}` and chmod 600, never echoing the token back. Re-run doctor until the token check passes. If doctor reports missing scopes, list them and stop this source. If doctor lists unmapped stage ids, ask the user to map each one to a phase (discovery, evaluation, proposal, commit, won, lost), up to four per question, and apply with `fs.py config set stagePhases.<stageId> "<phase>"`. Ask which pipelines to include (from doctor's pipeline list) and set `sources.hubspot.pipelines`. Set `sources.hubspot.enabled true`. Then run `fs.py pull hubspot` and report the counts.

**Granola.** Ask which route (gate): the Granola MCP server (all plans; sign in with `/mcp`), the Granola public API (Business and Enterprise; needs a `grn_` key in `GRANOLA_API_KEY` or `secrets.json`), or an export folder (CSV or markdown exports, or files saved earlier). Then:
- MCP route: the plugin ships the server as `granola` in its `.mcp.json`; if its tools are not available, tell the user to run `/mcp` and authenticate with Granola, then continue. Export the window in 30-day slices: call `list_meetings` with `time_range: "custom"`, `custom_start`, `custom_end` and `involvement: {"captured_by_me": true}`; collect the meeting ids; call `get_meetings` in batches of up to 10 ids; save each `get_meetings` response verbatim (the whole text block, unchanged) to `.flow-sales/cache/granola/<first-meeting-uuid>.txt`; for each meeting call `get_meeting_transcript` and save the response verbatim to `.flow-sales/cache/granola/<uuid>-transcript.txt` (skip with a note when the plan has no transcripts). Never retype or summarise tool output into these files; copy it exactly. Then run `fs.py import granola --export-dir .flow-sales/cache/granola`.
- API route: confirm the key is present with `fs.py doctor --source granola`, set `sources.granola.mode "api"`, run `fs.py import granola`.
- Export folder route: ask for the path, run `fs.py import granola --export-dir <path>`.
Report the counts (meetings parsed, transcripts present, internal-only meetings skipped, written as unlinked). Note that the local Granola cache is encrypted on current macOS builds, so it is not an option.

**Transcripts folder.** Ask for the folder path, confirm it exists, run `fs.py import transcripts --folder <path>`. Say which tools' exports were recognised.

**CSV.** Ask for the two file paths, run `fs.py import csv --deals <f> --interactions <f>`.

**Demo.** Run `fs.py import demo`.

## 6. Reps, training date, what may be read (gate)

Run `fs.py status --json` and read `data/reps.json` to list reps. Ask: include all reps or pick some (set `reps` to `"all"` or a JSON list of rep ids). Ask for the training date, if any (the date the team was trained on the framework; enables the before-and-after views; set `trainingDate` or leave null). Then ask three things, each as a real question with its consequence stated, not a default to inherit:

- "May FlowSales read email bodies and internal notes? Calls and meetings are always read." Options: yes, both; notes but not email bodies; email bodies but not notes; neither, calls and meetings only. Say that anything only ever evidenced in email scores lower when email is off. Apply `content.emailBodies` and `content.internalNotes`.
- "Should names be replaced in the report?" Options: no, real names (the report coaches by name); yes, reps only; yes, reps, contacts and companies. Recommend yes for a first run when the reps have not been told. Apply `anonymize`.
- "How many days before a piece of evidence goes stale?" Options: 45 (default, fits a one-to-three month cycle); 30; 90; or their average sales cycle in days. Say that a deal element drops one level when its last supporting evidence is older than this. Apply `attribution.decayDays`.

Ask for the organisation's own email domains so the linker never treats colleagues as buyers (set `org.internalDomains` as a JSON list); suggest the rep email domains you saw.

## 7. Link interactions to deals

Run `fs.py link --json` to apply the automatic links (CRM associations, attendee emails, company domains, times, titles). Report how many linked and how many are ambiguous. Do not resolve the ambiguous ones here: say that `/flow-sales:audit` asks about them before it scores, and that `/flow-sales:link` can revisit them at any time.

## 8. Finish

Run `fs.py status` and show the counts in one short table. Then say exactly what happens next, in three lines: `/flow-sales:audit` scores everything in the window and opens the report (state the rough duration from the interaction count: about one minute per deal, five deals at a time); every run is logged in `.flow-sales/runs.jsonl`; deleting `.flow-sales/` removes everything FlowSales knows, so back the folder up like any other file if the history matters.

Keep the tone plain. No em dashes. Do not write to the CRM. Do not store a token anywhere the user did not choose.
