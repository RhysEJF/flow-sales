---
name: setup
description: Connect FlowSales to your data (HubSpot by signing in as yourself, Granola, a folder of Gong, Fireflies or Fathom transcripts, a CSV export from Salesforce or any other CRM, or the demo dataset), say who you are (a rep, or setting it up for the team), agree who will see the report and what may be read, join or create the team folder, choose the framework and time window, map pipeline stages, pick reps and a training date, and pull the first data. Run this once per project directory. Anyone can go first.
disable-model-invocation: true
argument-hint: "[--demo]"
---

You are running FlowSales setup for the user. Everything is local: the store is `.flow-sales/` in the current directory. Ask with AskUserQuestion at every gate below, one gate at a time, and never guess a token, a path or a date. Use the CLI at `${CLAUDE_PLUGIN_ROOT}/scripts/fs.py` (call it as `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py" ...`; add `--json` when you need to parse output). If `$ARGUMENTS` contains `--demo`, skip gates 2, 3 and 5 entirely, use the demo dataset, ask nothing, and say so in one line.

Say what each step does before you ask its question. The person may be a rep who wants the morning briefing, or the ops person setting it up for everyone. Either can go first; nothing here assumes someone else installed before them.

## 1. Create the store

Run `fs.py init`. Tell the user where the store is, that it is git-ignored, and that nothing in it leaves the machine except the interaction text sent to the model during audit.

## 2. Who you are, who sees this, and do the reps know (gate)

Ask, in one call:

1. "Are you setting this up for your own deals, or for the team?" Options: my own deals, I am a rep; the team, I run sales ops or manage the team; both.
2. "Have the reps been told that FlowSales will read their calls, emails and notes and score them against the framework?" Options: yes, they know; not yet, I will tell them before the first audit; this is a pilot on my own deals only.
3. "Who will see the finished report?" Options: only me; sales managers; the reps, each their own page; leadership or the board too.

Record with `fs.py config set me.role "<rep|team|both>"`, `fs.py config set consent.repsInformed <true|false|"pilot">` and `fs.py config set consent.audience "<answer>"`. For a rep, also ask for their work email (the address on their HubSpot user) and set `me.email`; it selects their own deals later. If the reps have not been told, say plainly that the report names every rep next to their weakest elements, recommend switching anonymised names on for the first run (gate 6), and mention the report's names-hidden Impact export for anyone outside the sales team.

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

**HubSpot, connector route (default for everyone).** Nobody needs a token. Say: "Sign in to HubSpot as yourself; FlowSales sees what HubSpot lets you see." The plugin ships the HubSpot connector (`hubspot` in its `.mcp.json`, the server at mcp.hubspot.com). If its tools are not available in this session, tell the user how to sign in: in Claude Code run `/mcp`, pick hubspot and authenticate; in the Claude desktop app, Customize, Connectors, HubSpot. Then continue:

1. Call `get_user_details` and save the reply verbatim to `.flow-sales/cache/hubspot-mcp/user-1.json`. Note the user's email and owner id. If `me.role` is rep and `me.email` is unset, set it from here.
2. Call `search_owners` (all owners, paging through) and save each reply to `owners-<n>.json`. Call `get_properties` for the deal property `dealstage` and save it as `properties-dealstage.json` (stage ids and labels).
3. Deals in the window, with `search_crm_objects` on `deals`, properties `dealname, amount, deal_currency_code, pipeline, dealstage, hs_is_closed, hs_is_closed_won, closedate, createdate, hubspot_owner_id, hs_lastmodifieddate`: closed deals (`hs_is_closed` true) by `closedate` inside the window, then open deals by `createdate` inside the window. For a rep (`me.role` rep), add the filter `hubspot_owner_id` equals their owner id. Page through (200 per page) and save every reply as `deals-<n>.json`.
4. For every deal, its engagements: `search_crm_objects` on each of `calls`, `emails`, `meetings`, `notes` with the filter `associations.deal` equals the deal id, requesting the body properties (`hs_call_title, hs_call_body, hs_call_duration, hs_timestamp, hubspot_owner_id` for calls; `hs_email_subject, hs_email_text, hs_email_direction, hs_timestamp, hubspot_owner_id` for emails; `hs_meeting_title, hs_meeting_body, hs_internal_meeting_notes, hs_meeting_start_time, hs_timestamp, hubspot_owner_id` for meetings; `hs_note_body, hs_timestamp, hubspot_owner_id` for notes; skip email bodies or internal notes when the content permissions in gate 7 say so). Save each reply as `<type>-deal-<dealId>-<n>.json`; the file name is what attaches them to the deal. If `get_crm_objects` for deals accepts an `associations` list instead, fetching deals with `contacts, companies, calls, emails, meetings, notes` associations and saving as `deals-detail-<n>.json` does the same job.
5. Contacts and companies on those deals (`get_crm_objects` by the associated ids, 100 per call, properties `firstname, lastname, email, jobtitle, company` and `name, domain`) saved as `contacts-<n>.json` and `companies-<n>.json`.
6. Run `fs.py import hubspot-cache` and report the counts and any warnings. If it lists unmapped stage ids, ask the user to map each to a phase (discovery, evaluation, proposal, commit, won, lost), up to four per question, and apply with `fs.py config set stagePhases.<stageId> "<phase>"`.

The tool names above are HubSpot's documented ones. If a tool's argument names differ from the description, read its own guidance (`tool_guidance`) first and adapt; whatever the reply looks like, save it unchanged and let the import parse it. Never retype or summarise a reply into a file.

**HubSpot, private-app route (ops, or a machine that runs unattended).** Run `fs.py doctor --source hubspot --json`. If the token is missing, say this route needs the HubSpot admin, give them the exact page (Settings, Integrations, Private Apps, Create a private app, the six read scopes in `docs/hubspot.md`, nothing with write), and the three places the token can live in plain terms: an environment variable (set once per terminal session, nothing on disk), the plugin option `hubspot_token` (`/plugin configure flow-sales`, stored by Claude Code), or `.flow-sales/secrets.json` in this folder with permissions 600 (keep the folder out of git). Ask which; then wait (tell them to type `! export HUBSPOT_ACCESS_TOKEN=...` or restart the session) or take the pasted token, write `secrets.json` as `{"hubspot_token": "..."}` and chmod 600, never echoing it back. Re-run doctor until the token check passes; list missing scopes and stop this source if any. Map unmapped stage ids as above. Ask which pipelines to include and set `sources.hubspot.pipelines`. Set `sources.hubspot.enabled true`, then `fs.py pull hubspot` (add `--owner me` for a rep) and report the counts.

**Granola.** Ask which route (gate): the Granola connector (all plans; sign in with `/mcp` in Claude Code or Connectors in the desktop app), the Granola public API (Business and Enterprise; needs a `grn_` key in `GRANOLA_API_KEY` or `secrets.json`), or an export folder. Then:
- Connector route: the plugin ships the server as `granola` in its `.mcp.json`; if its tools are not available, tell the user to sign in, then continue. Export the window in 30-day slices: call `list_meetings` with `time_range: "custom"`, `custom_start`, `custom_end` and `involvement: {"captured_by_me": true}`; collect the meeting ids; call `get_meetings` in batches of up to 10 ids; save each reply verbatim to `.flow-sales/cache/granola/<first-meeting-uuid>.txt`; for each meeting call `get_meeting_transcript` and save the reply verbatim to `.flow-sales/cache/granola/<uuid>-transcript.txt` (skip with a note when the plan has no transcripts). Never retype or summarise tool output into these files. Then run `fs.py import granola --export-dir .flow-sales/cache/granola`.
- API route: confirm the key with `fs.py doctor --source granola`, set `sources.granola.mode "api"`, run `fs.py import granola`.
- Export folder route: ask for the path, run `fs.py import granola --export-dir <path>`.
Report the counts. Note that the local Granola cache is encrypted on current macOS builds, so it is not an option.

**Transcripts folder.** Ask for the folder path, confirm it exists, run `fs.py import transcripts --folder <path>`. Say which tools' exports were recognised.

**CSV.** Ask for the two file paths, run `fs.py import csv --deals <f> --interactions <f>`.

**Demo.** Run `fs.py import demo`.

## 6. Reps, training date, what may be read (gate)

Run `fs.py status --json` and read `data/reps.json` to list reps. If `me.role` is rep, match `me.email` to a rep and set `me.repId`; if no rep matches, ask which one they are. Ask: include all reps or pick some (set `reps` to `"all"` or a JSON list of rep ids; a rep on their own deals can leave it at all, their pull is already just their deals). Ask for the training date, if any (the date the team was trained on the framework; enables the before-and-after views; set `trainingDate` or leave null). Then ask three things, each as a real question with its consequence stated:

- "May FlowSales read email bodies and internal notes? Calls and meetings are always read." Options: yes, both; notes but not email bodies; email bodies but not notes; neither. Say that anything only ever evidenced in email scores lower when email is off. Apply `content.emailBodies` and `content.internalNotes`.
- "Should names be replaced in the report?" Options: no, real names; yes, reps only; yes, reps, contacts and companies. Recommend yes for a first run when the reps have not been told. Apply `anonymize`.
- "How many days before a piece of evidence goes stale?" Options: 45 (default); 30; 90; or their average sales cycle in days. Apply `attribution.decayDays`.

Ask for the organisation's own email domains so the linker never treats colleagues as buyers (set `org.internalDomains` as a JSON list); suggest the rep email domains you saw.

## 7. Link interactions to deals

Run `fs.py link --json` to apply the automatic links. Report how many linked and how many are ambiguous. Do not resolve the ambiguous ones here: say that `/flow-sales:audit` and `/flow-sales:daily-sync` ask about them before they score, and that `/flow-sales:link` can revisit them at any time.

## 8. Finish

Run `fs.py status` and show the counts in one short table.

**Team folder, only when `me.role` is team or both, never on `--demo`, never for a rep.** Run `fs.py team candidates --json` first. Then one question, with "not now" as the first option: "Later, teammates who install FlowSales can reuse the deals judged here instead of paying to judge them again. That works through a folder your team already syncs (Google Drive, OneDrive, Dropbox), holding one judged file per deal, nothing else. Set that up now?" Options: not now (it can be done any time with `/flow-sales:status`, which says how); yes, use the folder found at <path> (only when candidates were found); yes, create one at a path I give you. On yes, `fs.py team join <path>` or `fs.py team init <path>` and one line on what happened. In a cloud session (the workspace is not the user's own machine) say so and leave it at not now: the folder has to be one the desktop app can see, added with "Add folder", and that is a step for later. Then say exactly what happens next, in three lines, depending on who they are: a rep runs `/flow-sales:daily-sync` every morning (two minutes; it pulls their own deals, reuses anything the team has judged, judges the rest, then briefs them); the team person runs `/flow-sales:audit` once for the benchmark (state the rough duration from the interaction count and the cost the planner prints) and then weekly; everyone can run `/flow-sales:status` when in doubt. Every run is logged in `.flow-sales/runs.jsonl`; deleting `.flow-sales/` removes everything FlowSales knows on this machine, and the team folder keeps the judged deals.

Keep the tone plain. No em dashes. Do not write to the CRM. Do not store a token anywhere the user did not choose.
