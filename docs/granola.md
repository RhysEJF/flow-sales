# Granola

How FlowSales reads Granola meetings and turns them into Interactions that the linker attaches to deals.

```
python3 scripts/fs.py import granola                      # read .flow-sales/cache/granola (the MCP export folder)
python3 scripts/fs.py import granola --export-dir <dir>   # any folder of MCP text, API JSON, CSV or markdown files
python3 scripts/fs.py import granola --cache <path>       # a legacy plaintext desktop cache (pre May 2026, or Windows)
python3 scripts/fs.py config set sources.granola.mode api # pull from the public API on every import (Business, Enterprise)
python3 scripts/fs.py doctor --source granola             # which surface is usable right now
```

Every mode ends the same way: each meeting becomes a canonical Interaction (`docs/CONTRACTS.md` section 5) with
`id: granola:<uuid>`, is validated, and is upserted into `data/interactions/_unlinked.json`. Meetings whose
participants are all internal (or unknown) are skipped and counted. Ids that already sit inside a deal's
interaction file are left alone and counted as "already linked". The run is logged to `runs.jsonl`.

## 1. The three official surfaces

Granola has three supported ways to read your notes. Pick by plan.

| Surface | Plans | Gives | Use it when |
| --- | --- | --- | --- |
| Hosted MCP server | all (Basic limited to 30 days, no transcripts) | meeting list, attendees with emails and companies, AI summary, private notes, transcript on paid plans | default; the setup skill drives it |
| Public API | Business, Enterprise | everything above plus calendar event id, scheduled start and end, folders, speaker-attributed transcript, incremental sync | you have a `grn_` key |
| CSV export | all | title, summary, transcript without speaker labels, basic details | Basic plan history older than 30 days, or no MCP client |

### 1.1 Hosted MCP server (all plans)

- Remote, Granola-hosted, Streamable HTTP at `https://mcp.granola.ai/mcp`. Auth is OAuth 2.0 with a browser
  sign-in; there is no API key or service account for MCP. Launched 2026-02-04.
  Docs: https://docs.granola.ai/help-center/sharing/integrations/mcp and https://www.granola.ai/blog/granola-mcp
- Install in Claude Code, then authenticate:

  ```
  claude mcp add granola --transport http https://mcp.granola.ai/mcp
  /mcp        (choose granola, Authenticate, sign in in the browser)
  ```

- Plans: Basic (free) sees personal notes from the last 30 days; folder listing, folder filters and transcripts
  are paid-only. Business sees personal plus public (Team space) notes. Enterprise admins choose the scopes in
  Settings > Workspace > General > Apps and connectors > MCP access; if neither scope is enabled members cannot
  use MCP. Enterprise can also use Enterprise-Managed Authorization (Okta style).
- The server follows the workspace that is active in the desktop app and never combines workspaces.
- Rate limit: about 100 requests per minute across all tools, varying by plan and client.
- The six tools:

| Tool | Plan | What the plugin does with it |
| --- | --- | --- |
| `list_meetings` | all (folder filter paid) | `time_range: custom` slices with `custom_start`, `custom_end` and `involvement: {captured_by_me: true}`; returns `<meetings_data>` with `<meeting id title date>` and `<known_participants>` lines like `Jane Doe (attendee) from Acme <jane@acme.com>` |
| `get_meetings` | all | up to 10 ids per call; adds `<summary>` (AI enhanced notes) and private notes |
| `get_meeting_transcript` | paid | `<transcript meeting_id>` with `[00:00:15] Name: text` lines; `Me` is the note-taker, `Them` is unidentified others |
| `get_account_info` | all | email, active workspace and `mcp_note_access.scopes` (`personal`, `public`); the setup skill checks this first |
| `list_meeting_folders` | paid | folder ids and titles, only if you want to limit the export to a folder |
| `query_granola_meetings` | all | natural-language answers with `https://notes.granola.ai/d/<uuid>` citations; not used for import |

Meeting ids are the document UUIDs. Responses are text envelopes, not JSON, which is why the setup skill saves
them verbatim and `granola_parse.parse_mcp_text` does the parsing. MCP does not return calendar event ids,
scheduled times or web URLs; duration comes from transcript timestamps.

### 1.2 Public API (Business and Enterprise)

- Base URL `https://public-api.granola.ai/v1`, header `Authorization: Bearer grn_YOUR_API_KEY`.
  Docs: https://docs.granola.ai/introduction and https://docs.granola.ai/help-center/sharing/integrations/granola-api
- Create a key in the desktop app: Settings > Connectors > API keys > Create new key, and choose the scopes
  (Personal notes, Public notes). Workspace keys created by an admin read public notes only and cannot see
  private notes. You need a Business or Enterprise plan to create keys.
- Rate limits: 25 requests burst per 5 seconds, 5 per second sustained, HTTP 429 above that. The client stays
  at 4.5 requests per second and retries 429 honouring `Retry-After`.
- The API only returns notes that have a generated AI summary and a transcript. Notes still processing, notes
  without a transcript and notes whose transcript was auto-deleted are absent from the list and 404 on get.
- Endpoints the plugin uses (https://docs.granola.ai/api-reference/list-notes,
  https://docs.granola.ai/api-reference/get-note, https://docs.granola.ai/api-reference/get-transcript,
  OpenAPI at https://docs.granola.ai/api-reference/openapi.json):
  - `GET /v1/notes?created_after=<window from>&created_before=<window to>&page_size=30`, paged with `cursor`
    while `hasMore` is true. After the first run `updated_after=<watermark>` is added so only changed notes
    are fetched.
  - `GET /v1/notes/{id}?include=transcript` for the Note object: `web_url` (carries the document UUID, the same
    id MCP uses), `calendar_event` (event title, invitees, organiser, calendar event id, scheduled start and end),
    `attendees`, `folder_membership`, `summary_markdown`, `private_notes_markdown` (only for the note creator's
    own key) and `transcript` items with `speaker.attribution` (`me`, `them`), `speaker.name` when identified,
    `start_time` and `end_time`.
  - `GET /v1/notes/{id}/transcript?page_size=100` paged with `cursor`, used when the note call answers
    HTTP 413 `TRANSCRIPT_TOO_LARGE`.
- Where the plugin reads the key, in this order. The key is never printed, never written to `runs.jsonl` and
  never stored in the note cache.
  1. the environment variable `GRANOLA_API_KEY` (or the variable named in config `sources.granola.keyEnv`)
  2. the plugin user config, exposed as the environment variable `CLAUDE_PLUGIN_OPTION_GRANOLA_API_KEY`
  3. `.flow-sales/secrets.json` with `{"granola_api_key": "grn_..."}` and permissions 600
- Turn it on with `fs.py config set sources.granola.mode api`. Each fetched note is cached as
  `.flow-sales/cache/granola/<uuid>.json` (the UUID from `web_url`, else the `not_` id) and the watermark lives
  in `.flow-sales/cache/granola/_watermark.json`. Delete the watermark file to force a full re-pull of the window.
- Optional config: `sources.granola.apiBaseUrl`, `sources.granola.requestsPerSecond`.
- Webhooks (`note.generated`, `note.edited`, `note.access_granted`, https://docs.granola.ai/webhooks) carry no
  content and need a public HTTPS endpoint, so the plugin does not use them; re-run the import instead.

### 1.3 CSV and markdown exports (all plans)

- CSV: in the desktop app, Settings > Profile > Generate CSV, choose the workspaces, and the file is emailed
  within a few hours (one export per 24 hours, download link valid 24 hours). Granola says it "includes the
  title, note summary, transcript, and other basic details for each note", only for notes you own that have
  a summary, with full history even on Basic. The transcript has no speaker labels and the notes column is
  usually empty. Docs: https://docs.granola.ai/help-center/sharing/exporting-notes; a July 2026 field test:
  https://hirekai.ai/blog/export-granola-notes
- Granola does not document the column names, so the importer detects columns by header keywords:
  id or uuid; title, name, subject, meeting; date, created, start, time, when, scheduled; attendees,
  participants, people, invitees, guests; summary, enhanced, ai notes; transcript; notes, my notes, private;
  creator, owner, author, host; organiser; url, link, share; folder, space, workspace; duration, length.
  A row without an id or a notes.granola.ai URL gets a `csv-<hash>` id, so prefer one surface per meeting to
  avoid a second copy of a meeting already imported over MCP.
- Markdown: Granola has no markdown or JSON export in the app (per-note copy only). Files written by community
  tools import fine: YAML front matter (`title`, `date`, `attendees`, `granola_id` or `url`, `folder`, `owner`)
  plus sections such as `## Summary`, `## My Notes` and `## Transcript` with `[00:00:05] Name: text` lines.
  Docs on per-note copy: https://docs.granola.ai/help-center/taking-notes/transcription
- Speaker names in transcripts exist only when speaker tags were on during the call (Google Meet via the
  Granola browser extension, Zoom via the desktop app on macOS); otherwise you get `Me` and `Them`, and iOS
  gives `Speaker A` and `Speaker B`. Docs: https://docs.granola.ai/help-center/taking-notes/speaker-attribution

## 2. Why the local cache no longer works on macOS

Community tools used to read `~/Library/Application Support/Granola/cache-v3.json` (later `cache-v6.json`), a
plaintext JSON file holding every document, transcript and AI panel. That path is closed on current macOS builds:

- Around May 2026 Granola moved the live cache and the token store into AES-256-GCM encrypted `.enc` files
  (`cache-v6.json.enc`, `supabase.json.enc`, `stored-accounts.json.enc`). The plaintext `cache-v6.json` that
  remains is a stub written at install time with no `documents` key at all.
- From desktop 7.427 (rolled out around 2026-07-16) the data-encryption key lives in the macOS data-protection
  keychain under Granola's code-signed access group, readable only by Granola-signed code. Third-party code
  cannot decrypt the cache any more.
- Evidence: https://github.com/openclaw/graincrawl/issues/43, https://github.com/openclaw/graincrawl/pull/50,
  https://github.com/mynameiswhm/granola2markdown/issues/1, https://github.com/EnotionZ/granola-local-mcp

What the plugin does about it:

- `import granola --cache <path>` refuses a path that ends in `.enc`, does not exist, or holds no documents,
  prints exactly `Granola 7.427+ keeps its cache encrypted; use the Granola MCP export or the public API` and
  exits 1. Nothing is written.
- `--cache` still works for a plaintext cache from before May 2026 and for a Windows cache
  (`%APPDATA%\Granola\`, decryptable by the same user through DPAPI) that you have decrypted yourself.
- The plugin never writes into the Granola folder and never reads Granola's tokens.
- Platform notes: https://docs.granola.ai/help-center/getting-started/managed-installations lists the managed
  install endpoints; Windows launched 2025-06-11 (https://www.granola.ai/updates); there is no Linux desktop app.

## 3. The MCP export procedure (what the setup skill follows)

The setup skill drives the Granola MCP tools from inside Claude Code and saves every tool response verbatim,
which means the text block exactly as the tool returned it, not a paraphrase. Files go under the store's
export folder, `.flow-sales/cache/granola/` by default (`sources.granola.exportDir` or `--export-dir` override it).

1. Install and authenticate the MCP server (section 1.1). Call `get_account_info` and check the email, the
   active workspace and the scopes; switch the desktop app to the right workspace if needed.
2. Read the config window (`fs.py config get window`). Walk it backwards in 30-day slices: for each slice call
   `list_meetings` with `time_range: "custom"`, `custom_start` and `custom_end` as ISO dates, and
   `involvement: {"captured_by_me": true}` so only the user's own sales calls come back. On the Basic plan
   only the last 30 days return anything; stop when a slice is empty and older than 30 days.
   Save each response as `list-<custom_start>-<custom_end>.txt`.
3. Collect every meeting id from the list envelopes. Call `get_meetings` with `meeting_ids` in batches of 10.
   Save each meeting's envelope as `<uuid>.txt`. Saving a whole batch response as `batch-<n>.txt` also works:
   the importer splits multi-meeting envelopes and dedupes on the UUID.
4. On paid plans call `get_meeting_transcript` with each `meeting_id` and save the response as
   `<uuid>-transcript.txt` next to `<uuid>.txt`. The Basic plan answers `isError: true` with "Transcripts are
   only available to paid Granola tiers"; skip transcripts in that case, the summaries still import.
5. Stay under 100 requests per minute (a short pause every 20 calls is enough).
6. Run `python3 scripts/fs.py import granola`. The summary shows files read, meetings parsed, transcripts
   present, skipped internal, written unlinked and already linked. Add `--json` for the machine-readable form.
7. Run `python3 scripts/fs.py link` (or the link skill) to attach the new interactions to deals.

Re-running is safe: files are re-read, meetings are deduped on UUID, an interaction already inside a deal file
is never touched, and unlinked ones are updated in place. To extend the window, export the new slices only.

Optional config: `sources.granola.timezone` (an IANA zone such as `Europe/London`). MCP dates such as
`Feb 4, 2026 7:30 PM` carry no zone; they are read as local time in that zone, UTC when unset.

## 4. What the importer does with each file

| File | Parser | Recognised by |
| --- | --- | --- |
| `.txt`, `.xml` | `parse_mcp_text` | contains `<meetings_data`, `<meeting ` or `<transcript`; a bare `[00:00:15] Name: text` transcript named `<uuid>-transcript.txt` also works |
| `.json` | `parse_public_api_note` | a Note object (or `{"note": ...}`), a list of them, or a `GET /v1/notes` page |
| `.json` | pass-through | meeting dicts in the export shape (`granola_parse.new_meeting`), single or a list |
| `.json` | `parse_mcp_text` | an MCP tool result saved as JSON (`{"content": [{"type": "text", "text": ...}]}`) |
| `.json` | `parse_cache_json` | a legacy plaintext cache dropped into the folder |
| `.csv` | `parse_csv` | header keywords listed in section 1.3 |
| `.md` | `parse_markdown` | front matter plus sections |

Files and folders whose names start with `_` or `.` are skipped (that keeps `_watermark.json` out of the way).
Files that produce no meeting are reported as warnings, never as errors.

Then, for every meeting after the UUID merge: `to_interaction` builds the Interaction; participants get role
`rep` when their email domain is in `org.internalDomains`, matches a rep in `data/reps.json`, or they are the
note creator, else `buyer`; `at` comes from the calendar start, the meeting date, the first transcript
timestamp or the note creation time, in that order; `durationSec` from the calendar span or the transcript
span; `body` is one `Speaker: text` line per transcript segment, or the notes when there is no transcript.
Records are validated with the contract validator; invalid ones (usually a missing date) are listed in the
summary and not written.

## 5. How meetings are linked to deals

The importer never guesses a deal. It writes to `_unlinked.json` and leaves `dealId` null; `fs.py link` applies
the rules in `docs/CONTRACTS.md` section 6, highest confidence wins, and the link skill resolves anything
ambiguous with the user:

1. `time-match` (0.95): a HubSpot meeting engagement on the deal starts within 15 minutes of the interaction
   and shares an attendee email or the title. The two records merge and one Interaction survives with
   `meta.mergedFrom`.
2. `email-match` (0.9): a non-internal participant email equals a contact associated with the deal, and the
   meeting time falls inside the deal's open window (created minus grace to closed plus grace).
3. `domain-match` (0.7): a participant's email domain equals the deal's company domain, same window. Several
   matching deals become `candidates` and the link stays `pending`.
4. `title-match` (0.5): the meeting title contains the deal or company name as a whole word, same window.
5. Anything at or above `linking.autoAcceptConfidence` (0.9 by default) with a single candidate is accepted
   automatically; otherwise it is `pending` and the link skill asks. `link confirm <interactionId> <dealId>` and
   `link reject <interactionId>` record the decision; rejected pairs are never proposed again.

Internal domains (config `org.internalDomains` plus every rep's domain) never count as buyer matches. The
fields each surface provides for this: MCP gives attendee emails, names and Granola's People and Companies
enrichment (`meta.participantCompanies`), the title and the date; the public API adds
`meta.calendar_event_id`, `meta.organiser`, `meta.scheduled_start_time`, `meta.scheduled_end_time` and folders;
the CSV gives whatever the attendees column holds, so those interactions usually need the user to pick the deal.

## 6. Privacy

- Transcripts contain other people who did not agree to downstream processing. Keep the export folder and the
  store local, share the report rather than the raw transcripts, and honour transcript auto-deletion settings
  (https://docs.granola.ai/help-center/consent-security-privacy/transcript-auto-deletion). Granola never stores
  audio; transcription is real time.
- Private notes (`notes`) are the user's own typed notes. `content.internalNotes: false` in the config keeps
  them out of the judge's batches; `content.callTranscripts: false` does the same for transcripts.
- The API key is read from the environment or `secrets.json` (chmod 600) and is never printed, logged or cached.
  The doctor reports where the key was found, not its value.
- MCP and API keys are scoped to one workspace and to the `personal` or `public` scope; shared-folder notes from
  teammates arrive only under `public` on paid plans. Export with `captured_by_me: true` unless the team has
  agreed to pool notes.
- Notes flagged `privacy_mode_enabled` in a legacy cache keep that marker in `meta`; treat them as do-not-share.
- `runs.jsonl` records what every run read and wrote, which is the audit trail for a kill switch.

## 7. Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `Granola 7.427+ keeps its cache encrypted; use the Granola MCP export or the public API` | the cache path is `.enc`, missing or a stub. Use the MCP export (section 3) or the API (section 1.2). |
| `No Granola export folder at ...` | nothing has been exported yet. Run the setup skill, or pass `--export-dir`. |
| `warning: <file>: no meetings recognised` | the file is not a verbatim tool response, has the wrong extension, or is a transcript file whose name has no UUID. Re-save it as `<uuid>.txt` or `<uuid>-transcript.txt`. |
| high `skipped internal-only` | attendee emails are missing (ad-hoc notes without a calendar event) or `org.internalDomains` is wrong. Add attendees in Granola, use `get_meetings` rather than `list_meetings` only, or fix the config. |
| `invalid records skipped ... 'at'` | the date could not be parsed (CSV date column missing or in an unusual format). Check the column, or set `sources.granola.timezone`. |
| times are off by hours | MCP dates have no zone. Set `sources.granola.timezone`. |
| no transcripts | Basic plan (MCP transcripts are paid-only), transcript auto-deletion, or the meeting was never transcribed. The API also hides notes without a transcript; use `get_meetings` for their summaries. |
| API `401 MISSING_API_KEY` or 403 | the key is missing, expired or lacks the scope. Check `fs.py doctor --source granola`, then the key's scopes in the desktop app. |
| API 413 or 429 | handled: 413 pages the transcript endpoint, 429 waits for `Retry-After`. Persistent 5xx exits with code 2 and the watermark is not advanced, so the next run repeats the window. |
| `Transcripts are only available to paid Granola tiers` | MCP on the Basic plan. Skip step 4 of section 3. |
| a meeting appears twice | the same meeting came from two surfaces and one copy lacks the UUID (a CSV row without id or URL). Delete the `csv-` copy from `_unlinked.json` or re-export the CSV with an id column. |
| MCP shows the wrong meetings | the server follows the workspace active in the desktop app. Switch workspace and re-run `list_meetings`. |

`fs.py doctor --source granola` prints which surface is usable (export files present, key found, cache readable)
without exposing the key.
