---
name: setup
description: Connect FlowSales to your data (HubSpot, Granola, a transcripts folder, a CSV export, or the demo dataset), choose the framework and time window, map pipeline stages, pick reps and a training date, and pull the first data. Run this once per project directory before audit.
disable-model-invocation: true
argument-hint: "[--demo]"
---

You are running FlowSales setup for the user. Everything is local: the store is `.flow-sales/` in the current directory. Ask with AskUserQuestion at every gate below, one gate at a time, and never guess a token, a path or a date. Use the CLI at `${CLAUDE_PLUGIN_ROOT}/scripts/fs.py` (call it as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py" ...`; add `--json` when you need to parse output). If `$ARGUMENTS` contains `--demo`, skip the source gate and use the demo dataset.

## 1. Create the store

Run `fs.py init`. Tell the user where the store is and that it is git-ignored and never leaves the machine.

## 2. Sources (gate, multi-select)

Ask which sources to connect:
- HubSpot (deals, contacts, calls, emails, meetings, notes; read-only)
- Granola (meeting notes and transcripts; local cache or export)
- A folder of transcripts (Gong, Fireflies, Fathom, Google Meet exports; .md, .txt, .vtt, .json)
- A CSV export from another CRM (see docs/other-crms.md)
- The demo dataset (32 fictional deals, 4 reps, no connection needed)

## 3. Framework and window (gate)

Ask two questions in one call: framework (MEDDPICC, recommended; or MEDDIC, six elements) and window (last quarter, last 6 months, last 12 months, or custom dates). Apply with `fs.py config set framework "meddpicc"` and `fs.py config set window '{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}'`.

## 4. Connect each chosen source, one at a time

**HubSpot.** Run `fs.py doctor --source hubspot --json`. If the token is missing, explain the three places it can live (the `HUBSPOT_ACCESS_TOKEN` environment variable; the plugin's user config option `hubspot_token`, set with `/plugin configure flow-sales` or `claude plugin install flow-sales@flow-sales --config hubspot_token=...`, which reaches the CLI as `CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN`; or `.flow-sales/secrets.json` with permissions 600) and point to `docs/hubspot.md` for creating a private app with the read scopes. Ask whether the user wants to set the environment variable themselves (then wait: tell them to type `! export HUBSPOT_ACCESS_TOKEN=...` or restart the session) or paste the token now to store it in `secrets.json` (write the file with `{"hubspot_token": "..."}` and chmod 600, and never echo the token back). Re-run doctor until the token check passes. If doctor reports missing scopes, list them and stop this source. If doctor lists unmapped stage ids, ask the user to map each one to a phase (discovery, evaluation, proposal, commit, won, lost), up to four per question, and apply with `fs.py config set stagePhases.<stageId> "<phase>"`. Ask which pipelines to include (from doctor's pipeline list) and set `sources.hubspot.pipelines`. Set `sources.hubspot.enabled true`. Then run `fs.py pull hubspot` and report the counts.

**Granola.** Ask which route (gate): the Granola MCP server (all plans; sign in with `/mcp`), the Granola public API (Business and Enterprise; needs a `grn_` key in `GRANOLA_API_KEY` or `secrets.json`), or an export folder (CSV or markdown exports, or files saved earlier). Then:
- MCP route: the plugin ships the server as `granola` in its `.mcp.json`; if its tools are not available, tell the user to run `/mcp` and authenticate with Granola, then continue. Export the window in 30-day slices: call `list_meetings` with `time_range: "custom"`, `custom_start`, `custom_end` and `involvement: {"captured_by_me": true}`; collect the meeting ids; call `get_meetings` in batches of up to 10 ids; save each `get_meetings` response verbatim (the whole text block, unchanged) to `.flow-sales/cache/granola/<first-meeting-uuid>.txt`; for each meeting call `get_meeting_transcript` and save the response verbatim to `.flow-sales/cache/granola/<uuid>-transcript.txt` (skip with a note when the plan has no transcripts). Never retype or summarise tool output into these files; copy it exactly. Then run `fs.py import granola --export-dir .flow-sales/cache/granola`.
- API route: confirm the key is present with `fs.py doctor --source granola`, set `sources.granola.mode "api"`, run `fs.py import granola`.
- Export folder route: ask for the path, run `fs.py import granola --export-dir <path>`.
Report the counts (meetings parsed, transcripts present, internal-only meetings skipped, written as unlinked). Note that the local Granola cache is encrypted on current macOS builds, so it is not an option.

**Transcripts folder.** Ask for the folder path, confirm it exists, run `fs.py import transcripts --folder <path>`.

**CSV.** Ask for the two file paths, run `fs.py import csv --deals <f> --interactions <f>`.

**Demo.** Run `fs.py import demo`.

## 5. Reps, training date, content (gate)

Run `fs.py status --json` and read `data/reps.json` to list reps. Ask: include all reps or pick some (set `reps` to `"all"` or a JSON list of rep ids). Ask for the training date, if any (the date the team was trained on the framework; enables before-and-after views; set `trainingDate` or leave null). Ask whether email bodies and internal notes may be read (default yes) and whether names should be anonymised in reports (default no); apply the `content.*` and `anonymize` keys. Ask for the organisation's own email domains so the linker never treats colleagues as buyers (set `org.internalDomains` as a JSON list); suggest the rep email domains you saw.

## 6. Link interactions to deals

Run `fs.py link --dry-run --json`. If it reports pending candidates, say how many and invoke the link skill (`/flow-sales:link`) so the user can resolve them; otherwise run `fs.py link` to apply the automatic links.

## 7. Finish

Run `fs.py status` and show the counts. Tell the user the next step is `/flow-sales:audit`, that every run is logged in `.flow-sales/runs.jsonl`, and that deleting `.flow-sales/` removes everything FlowSales knows.

Keep the tone plain. No em dashes. Do not write to the CRM. Do not store a token anywhere the user did not choose.
