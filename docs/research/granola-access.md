# Granola access reference for the Flow sales plugin

Compiled 2026-09-07. Purpose: everything a Claude Code plugin needs to ingest Granola meetings (notes, summaries, transcripts, attendees) and link each one to a CRM deal. Sources are official Granola docs first, then community code, then live probes run on this Mac on 2026-09-07. Anything not confirmed by an official source or a live probe is marked UNVERIFIED.

## 0. State of play in one screen

- Granola has three official read surfaces: a hosted MCP server (all plans, OAuth), a public REST API with webhooks (Business and Enterprise, `grn_` keys), and a per-user CSV export (all plans). Links: https://docs.granola.ai/help-center/sharing/integrations/mcp, https://docs.granola.ai/introduction, https://docs.granola.ai/help-center/sharing/exporting-notes
- The local desktop cache that community tools historically read (`~/Library/Application Support/Granola/cache-v3.json`, later `cache-v6.json`) is no longer a usable source on current macOS builds. Around May 2026 Granola moved the live cache and token store into AES-256-GCM `.enc` files, and from desktop 7.427 (rolled out around 2026-07-16) the data-encryption key lives in the macOS data-protection keychain under Granola's code-signed access group `QZ7DHHLN25.granola`, readable only by Granola-signed code. Evidence: https://github.com/openclaw/graincrawl/issues/43, https://github.com/openclaw/graincrawl/pull/50, https://github.com/mynameiswhm/granola2markdown/issues/1, https://github.com/EnotionZ/granola-local-mcp
- Verified locally on 2026-09-07 (see section 3.6): this Mac has `cache-v6.json.enc` (245 KB, live), `supabase.json.enc`, `stored-accounts.json.enc`, an encrypted `granola.db`, a 1.9 KB plaintext `cache-v6.json` stub frozen at install time (2026-05-27) containing no documents, and no `storage.dek`.
- Practical consequence: on macOS the plugin should treat the official public API (if the user is on Business) or the official MCP server as primary, keep a cache adapter only for legacy plaintext caches and for Windows, and offer CSV or markdown import as the manual fallback. Section 7 lays this out.
- Attendee emails are available on every official surface (MCP `list_meetings` and `get_meetings`, API `attendees[].email` and `calendar_event.invitees[].email`, Zapier payload). Calendar event ids and scheduled times are only on the public API and the local cache, not on MCP.

## 1. Official Granola MCP server

### 1.1 Facts

| Item | Value | Source |
| --- | --- | --- |
| Type | Remote, Granola-hosted, Streamable HTTP | https://docs.granola.ai/help-center/sharing/integrations/mcp |
| URL | `https://mcp.granola.ai/mcp` | same |
| Launch | 2026-02-04 ("Introducing Granola MCP", author Jack) | https://www.granola.ai/blog/granola-mcp |
| Auth | OAuth 2.0 with metadata discovery and dynamic client registration; browser sign-in; no API key or service account for MCP. Enterprise can use Enterprise-Managed Authorization (EMA, tested with Claude plus Okta). | same doc |
| Live probe 2026-09-07 | Unauthenticated POST returns 401 with `WWW-Authenticate: Bearer ... resource_metadata="https://mcp.granola.ai/.well-known/oauth-protected-resource"`. Protected-resource metadata: `authorization_servers: ["https://mcp-auth.granola.ai"]`, `scopes_supported: ["mcp"]`. Auth server metadata at `https://mcp-auth.granola.ai/.well-known/oauth-authorization-server`: `authorization_endpoint /oauth2/authorize`, `token_endpoint /oauth2/token`, `registration_endpoint /oauth2/register`, grants `authorization_code`, `refresh_token`, `device_code`, `jwt-bearer`, PKCE `S256`, client auth `none`, `client_secret_post`, `client_secret_basic`, `private_key_jwt`. | curl on this machine |
| EMA values | Resource URL `https://mcp.granola.ai/mcp`, Issuer `https://mcp-auth.granola.ai`, ID-JAG audience `https://mcp-auth.granola.ai`, scope `mcp` | MCP doc |
| Claude Code install | `claude mcp add granola --transport http https://mcp.granola.ai/mcp`, then `/mcp` and Authenticate | MCP doc |
| Plans | Basic (free): personal notes from the last 30 days, some folder, search and transcript tools paid-only. Business: personal plus public notes. Enterprise: admin chooses scopes in Settings > Workspace > General > Apps and connectors > MCP access for members; if neither scope is enabled members cannot use MCP. | MCP doc |
| Workspace scope | Follows the active workspace selected in the desktop app; never combines workspaces | MCP doc |
| Rate limit | "currently average around 100 requests per minute across all tools", varies by plan and client, subject to change | MCP doc |
| Data model | Meeting ids are the document UUIDs (with or without hyphens). Citation links look like `https://notes.granola.ai/d/<uuid>`. | https://github.com/maton-ai/api-gateway-skill/blob/HEAD/references/granola-mcp/README.md |

### 1.2 Full tool list (6 tools)

Tool descriptions from the official doc; input schemas from two independent mirrors of the live server: Maton (older 4-tool snapshot, https://github.com/maton-ai/api-gateway-skill/tree/HEAD/references/granola-mcp/schemas) and Composio (6-tool snapshot, version 20260805, https://docs.composio.dev/toolkits/granola_mcp.md).

| Tool | Plan | Inputs | Returns |
| --- | --- | --- | --- |
| `query_granola_meetings` | all | `query` (string, required), `document_ids` (uuid[], optional, limits context) | Natural-language answer with inline citations `[[n]](https://notes.granola.ai/d/<uuid>)` |
| `list_meeting_folders` | paid | none documented | Folder id, title, description, note count, including nested folders |
| `list_meetings` | all (folder filter paid) | `time_range` enum `this_week`, `last_week`, `last_30_days` (default), `custom`; `custom_start`, `custom_end` (ISO dates, required for custom); `folder_id` (paid); `involvement` object with `captured_by_me` and `listed_as_participant` booleans (true values OR together, false values are AND exclusions); `workspace_only` boolean (Team Space only) | XML-ish text: `<meetings_data from=".." to=".." count="n">` containing `<meeting id="<uuid>" title=".." date="Feb 4, 2026 7:30 PM">` with `<known_participants>` lines formatted `John Doe (note creator) from Acme <john@acme.com>` |
| `get_meetings` | all | `meeting_ids` (uuid[], 1 to 10) | Same meeting envelope plus `<summary>` markdown (AI enhanced notes) and private notes when available; attendees with emails |
| `get_meeting_transcript` | paid | `meeting_id` (uuid) | `<transcript meeting_id="..">` with lines `[00:00:15] Name: text`. Speaker labels: `Me` is the note-taker, `Them` is unidentified others, named speakers by name when speaker tags identified them. Free tier gets `isError: true` with "Transcripts are only available to paid Granola tiers" |
| `get_account_info` | all | none | Email, active workspace, and `mcp_note_access.scopes` (`personal`, `public`) for the connected session |

Notes for the plugin:

- Responses are text blocks, not structured JSON. Expect to parse the XML-like envelope and the `Name (role) from Company <email>` participant lines. The `from Company` fragment is Granola's own People and Companies enrichment, useful for deal matching.
- No calendar event id, no scheduled start or end, no folder membership per meeting, no note web URL in `list_meetings` (only the citation links from `query_granola_meetings`). Duration must be inferred from transcript timestamps.
- Basic plan: 30-day window and no transcript. Business or Enterprise: full history, transcripts, folders.
- MCP is scoped to notes the user can access in the active workspace only; shared-folder notes from teammates are included only under the `public` scope on paid plans.
- The Maton mirror observed a `Mcp-Session-Id` header that can be reused between calls and reports about 100 requests per minute, matching the official figure.

## 2. Official public API and webhooks

### 2.1 Facts

| Item | Value | Source |
| --- | --- | --- |
| Base URL | `https://public-api.granola.ai/v1` | https://docs.granola.ai/introduction |
| Auth | `Authorization: Bearer grn_YOUR_API_KEY`. Live probe 2026-09-07 without a key: HTTP 401 `{"code":"MISSING_API_KEY","message":"Missing or invalid Authorization header. Expected: Bearer <api_key|token>"}` | curl, and doc |
| Key creation | Desktop app: Settings > Connectors > API keys > Create new key, choose scopes | https://docs.granola.ai/help-center/sharing/integrations/granola-api |
| Plan | Business or Enterprise only ("You need a Business or Enterprise plan to create API keys") | same |
| Scopes | Personal notes (owned, directly shared, private folders shared with you) and Public notes (visible to everyone in the workspace, Team space). Enterprise admins control which scopes members may use. | same |
| Workspace API keys | Admin-created, non-expiring, not tied to a user; read public notes and spaces with "Allow Granola API access" on (default on for new spaces); cannot read private notes | same |
| Rate limits | 25 requests burst per 5 seconds, 5 requests per second sustained (300 per minute), 429 on excess | https://docs.granola.ai/introduction |
| Only summarised notes | "The API only returns notes that have a generated AI summary and transcript." Processing or never-summarised notes are excluded from List and 404 on Get. | same |
| Sandbox | None | help-center API page |
| OpenAPI | `https://docs.granola.ai/api-reference/openapi.json` lists paths `/v1/notes`, `/v1/notes/{note_id}`, `/v1/notes/{note_id}/transcript`, `/v1/folders`, `/v1/audit`, `/v1/webhook-endpoints`, `/v1/webhook-endpoints/{id}` | fetched 2026-09-07 |

### 2.2 Endpoints

`GET /v1/notes` (https://docs.granola.ai/api-reference/list-notes): query params `created_before`, `created_after`, `updated_after` (date or date-time), `folder_id` (`fol_` plus 14 chars, includes child folders), `cursor`, `page_size` (1 to 30, default 10). Returns `{notes: [NoteSummary], hasMore, cursor}` where NoteSummary is `{id: "not_" + 14 chars, object: "note", title, owner: {name, email}, created_at, updated_at}`.

`GET /v1/notes/{note_id}` (https://docs.granola.ai/api-reference/get-note): optional `include=transcript`. Returns the Note object:

- `id` (`not_...`), `object`, `title` (nullable), `owner {name, email}`, `created_at`, `updated_at`
- `web_url` such as `https://notes.granola.ai/d/f3e45e0f-24cc-480b-9a6c-8b1f5e3d7a2c`. The UUID in `web_url` is the same document UUID that MCP, the desktop app and the private API use, so it bridges `not_` ids to UUIDs (confirmed by the Obsidian plugin's migration logic: https://github.com/tomelliot/obsidian-granola-sync/blob/main/README.md).
- `calendar_event` (nullable): `event_title`, `invitees [{email}]`, `organiser` (email), `calendar_event_id` (for Google looks like `2su99n6iiik37iiknmb5t4fkfh_20260127T153000Z`), `scheduled_start_time`, `scheduled_end_time`
- `attendees [{name (nullable), email}]`
- `folder_membership [{id, object: "folder", name, parent_folder_id}]` including ancestor folders
- `summary_text`, `summary_markdown` (nullable)
- `private_notes_text`, `private_notes_markdown`: the owner's own typed notes, returned only when the key belongs to the note creator, null for shared notes and workspace keys
- `transcript` (nullable array) of `{speaker: {source: "microphone" | "speaker", attribution: "me" | "them" (omitted when unknown), diarization_label: "Speaker A" (iOS only), name: "Alice Smith" (only when identified)}, text, start_time, end_time}`. Large transcripts return HTTP 413 `TRANSCRIPT_TOO_LARGE`; page them from the transcript endpoint.

`GET /v1/notes/{note_id}/transcript` (https://docs.granola.ai/api-reference/get-transcript): `cursor`, `page_size` (1 to 100, default 50). Returns `{transcript: [Transcript], hasMore, cursor}`.

`GET /v1/folders` (https://docs.granola.ai/api-reference/list-folders): `cursor`, `page_size` (1 to 30). Returns `{folders: [{id, object, name, parent_folder_id}], hasMore, cursor}`, sorted alphabetically.

`GET /v1/audit`: workspace audit events (`aud_` ids, `action` such as `workspace.member_added`, `occurred_at`, `collected_at`), one-year retention window. Present in the OpenAPI file; no help-centre page found. Likely Enterprise, UNVERIFIED.

API changelog (https://docs.granola.ai/api-reference/changelog): initial release with List Notes and Get Note (admin keys, 5 rps); then List Folders, `folder_id` filter, folder hierarchy; then Personal and Public scopes for any Business or Enterprise member; then `speaker.attribution`; then Get Transcript plus the 413 behaviour. Dates are not printed on the page.

### 2.3 Webhooks (https://docs.granola.ai/webhooks)

- Business and Enterprise. Create in Settings > Connectors > Webhooks, per folder via the folder's Integrations menu, or `POST /v1/webhook-endpoints` with `{url, scopes: ["personal", "public"], events?, folder_ids?}`. Response includes `signing_secret` (`whsec_...`) once only.
- Events: `note.generated` (first AI summary), `note.edited` (summary edited or regenerated, `data.changed_fields` currently always `["summary"]`), `note.access_granted` (shared with you directly or via a folder). Subscribe to both `note.generated` and `note.access_granted` to discover notes.
- Payload carries no content: `{event_id, event_type, note_id, occurred_at}`; fetch the note with the API.
- Signed per the Standard Webhooks spec: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,` plus base64 HMAC-SHA256 of `{id}.{timestamp}.{body}` keyed with the base64-decoded secret after `whsec_`).
- 15 second response window, exponential retries for four days, endpoint disabled after four days of failure, missed events not replayed. URL must be public HTTPS.

## 3. Community and open-source readers

### 3.1 Inventory (GitHub stats fetched 2026-09-07)

| Project | Data source | Language | Last push | Status and notes |
| --- | --- | --- | --- | --- |
| pedramamini/GranolaMCP https://github.com/pedramamini/GranolaMCP | local `cache-v3.json` only, no API | Python | 2025-07-12 | 45 stars. MCP tools `search_meetings`, `get_transcript`, `get_meeting_notes`, `get_statistics`, `list_participants`, `export_markdown`. PR #30 (2026-03-18) adds `cache-v6.json` support and notes the README env var never worked (use `--cache-path`). Effectively unmaintained; dead on encrypted caches. Same project as `granola-mcp` on PyPI. |
| proofsh/granola-mcp-server https://github.com/proofsh/granola-mcp-server | local `cache-v*.json` | Python | 2026-06-01 | 95 stars, PyPI `granola-mcp-server`, `uvx granola-mcp-server`. Tools `search_meetings`, `get_meeting_details`, `get_meeting_transcript`, `get_meeting_documents`, `analyze_meeting_patterns`. No `.enc` handling found in README. |
| r12consulting/mcp-granola (fork of NimbleBrainInc/mcp-granola) https://github.com/r12consulting/mcp-granola | local cache v3 to v6, macOS only, hot reload on mtime | Python | 2026-03-20 | Upstream NimbleBrainInc archived 2026-05-27 with the note "Removed from mpak, use Granola's native remote MCP endpoint". Cleanest reference implementation of cache key paths (section 3.2). |
| chrisguillory/granola-mcp | private API with token from `supabase.json` | Python | repo now 404 | README documented `/v2/get-documents`, `/v1/get-document-panels`, `/v1/get-document-transcript`, plus delete and undelete via `/v1/update-document`. |
| accrue-money/granola-mcp, npm `granola-mcp-plus` 1.2.0 https://www.npmjs.com/package/granola-mcp-plus | private API; v1.2.0 (2026-05-15) reads the JWT from plaintext `stored-accounts.json` | TypeScript | 2026-08-04 | Tools for documents, transcripts (raw utterances with source), folders including shared, workspaces. Dead on installs where only `stored-accounts.json.enc` exists (this Mac). |
| EnotionZ/granola-local-mcp https://github.com/EnotionZ/granola-local-mcp | private API, decrypts `supabase.json.enc` via `storage.dek` | TypeScript | deprecated | README: "does not work as of Granola 7.427.3", recommends the official remote MCP. |
| moona3k/granola-export https://github.com/moona3k/granola-export | private API, token from `supabase.json` (PR #1 adds `.enc` via `storage.dek`) | Python | 2026-04-26 | Best written reference for private endpoints and data shapes (`references/endpoints.md`, `data-shapes.md`, `auth.md`). macOS only. |
| openclaw/graincrawl https://github.com/openclaw/graincrawl | private API, public API, desktop cache, explicit encrypted-json unlock | Go | 2026-09-05 | Active (v0.4.2). Fails closed on 7.427+ by design (PR #50). SPEC.md documents the companion CLI, OPFS SQLCipher store and cache v6 layout. |
| tomelliot/obsidian-granola-sync https://github.com/tomelliot/obsidian-granola-sync | official public API since 2.1.0 (was local credentials) | TypeScript | 2026-09-01 | 80 stars, v3.0.0. README: "Granola broke the old credential-based login in app version 7.427.0, so as of 2.1.0 this plugin uses Granola's official API." PRs #123, #130, #132 (May 2026) document the `.enc`, `stored-accounts.json` and Windows DPAPI schemes. |
| dmwyatt/granz https://github.com/dmwyatt/granz | private API; own OAuth login; on Windows and Linux falls back to decrypting `supabase.json.enc`; "There is no such fallback on macOS" | Rust | 2026-09-07 | Active. Confirms the Windows DPAPI path still works as of late August 2026 and that macOS is closed. |
| theantichris/granola https://github.com/theantichris/granola | notes via private API, transcripts via cache | Go | 2025-10-01 | 43 stars. Issue #24 documents the May 2026 encryption switch. Documents Windows and Linux paths. |
| mikedemarais/granola-ts-client (npm `granola-ts-client` 0.11.2) https://github.com/mikedemarais/granola-ts-client | private API client | TypeScript | 2025-08-18 | `getDocuments`, `getDocumentTranscript`, `getWorkspaces`, `updateDocument`; token helpers for macOS and Linux. |
| mikedemarais/granola-to-markdown https://github.com/mikedemarais/granola-to-markdown | local `cache-v3.json` | TypeScript | 2025-04-10 | Small script; its TypeScript interfaces are the clearest record of cache field names (section 3.2). |
| getprobo/reverse-engineering-granola-api https://github.com/getprobo/reverse-engineering-granola-api | private API docs | Python | archived 2026-02-05 | Archived with the note that Granola released an official API. Documents WorkOS refresh-token rotation. |
| joelhooks/granola-cli https://github.com/joelhooks/granola-cli | official MCP via mcporter OAuth | TypeScript | 2026-02-19 | Agent-first CLI over the 4 original MCP tools. |
| Official-API CLIs: `@doist/granola-cli`, `@toolittlecakes/granola-cli`, aliou/granola-cli, alavida-ai/granola-plugin (ships a Claude Code plugin), averagechris/granola-cli | public API with `grn_` key | mixed | 2026 | Show the ecosystem consolidating on the public API. https://github.com/alavida-ai/granola-plugin |
| CRM ingestion references: `@odla-ai/granola` (public API plus Standard Webhooks, projects attendees to CRM records, idempotent ingest), `@excelium-tech/granola` (Twenty CRM connector, polls every 15 minutes, resolves attendee emails to Person records, matches `calendar_event` to CalendarEvent) | public API | TypeScript | 2026-08 | https://www.npmjs.com/package/@odla-ai/granola, https://www.npmjs.com/package/@excelium-tech/granola |

Other npm packages found (registry search 2026-09-07): `granola-toolkit` 0.67.0 (kkarimi, repo renamed to kkarimi/gran; public API key plus local sync; macOS, Linux, Windows binaries), `granola-to-minutes`, `@armsteadj1/granola-sync`, `spoon-cli` (MCP), `granola-api` (MCP OAuth client), `@daanvanhulsen/granola-mcp` (May 2025, single transcript tool, token copied from DevTools), `@iflow-mcp/btn0s-granola-mcp`, `@pipedream/granola`, `@7plx/n8n-nodes-granola`, `@intentsolutionsio/granola-pack` (24 Claude Code skills, still describes `cache-v3.json`).

### 3.2 Local cache JSON structure (plaintext era, pre-May-2026, and Windows where decryptable)

File: `~/Library/Application Support/Granola/cache-v3.json` (2025), `cache-v6.json` (2026). Both are written by the Electron app; v3 wraps the state as a JSON string, v6 as an object.

```
top level: { "cache": <string in v3 | object in v6>, "version": <int, 8 on this Mac's stub> }
cache (after json.loads when it is a string):
  state.documents            map<docUUID, Document>
  state.meetingsMetadata     map<docUUID, { id, creator {name, email}, attendees [{name, email}] }>
  state.transcripts          map<docUUID, TranscriptEntry[]>
  state.documentPanels       map<docUUID, map<panelId, Panel>>
  state.documentLists        map<listId, docUUID[]>          (folders)
  state.documentListsMetadata map<listId, { title, ... }>
  state.entities             {} on the 2026 stub (see 3.6)
Document (same 46-field shape as the private API /v2/get-documents):
  id, user_id, workspace_id, created_at, updated_at, deleted_at, title,
  type ("meeting" | null, null = standalone note), valid_meeting (bool),
  transcribe (bool, "currently transcribing", not "has transcript"),
  public, privacy_mode_enabled, creation_source ("auto_calendar" | "manual"),
  notes (ProseMirror doc), notes_plain, notes_markdown,
  people { creator {name, email} | organizer {email, displayName},
           attendees [{ email, displayName | name, responseStatus, self, person_id }],
           manual_attendee_edits [{ action: "add" | "remove", email, displayName }] },
  google_calendar_event { id, summary, description, start {dateTime, timeZone},
           end {dateTime, timeZone}, attendees [{email, displayName, responseStatus, self, organizer}],
           organizer {email}, creator {email}, conferenceData, hangoutLink, htmlLink } | null,
  attachments [], audio_file_handle (vestige, no audio is stored), status,
  hubspot_note_url, affinity_note_id, attio_shared_at  (CRM sync markers)
TranscriptEntry:
  id, document_id, text, source ("microphone" = you | "system" = others),
  speaker (string, present when speaker tags identified someone),
  start_timestamp, end_timestamp (ISO 8601 absolute), is_final, sequence_number,
  transcriber_user_id
Panel (AI summary):
  id, document_id, title ("Summary", ...), template_slug (e.g. "v2:meeting-summary-consolidated"),
  content (ProseMirror JSON, sometimes a bare string or HTML), original_content (pre-edit),
  suggested_questions, user_feedback, created_at, updated_at
```

Sources: r12consulting `data.py` (https://raw.githubusercontent.com/r12consulting/mcp-granola/main/src/mcp_granola/data.py), pedramamini `parser.py`, mikedemarais `index.ts`, moona3k `references/data-shapes.md` (https://github.com/moona3k/granola-export/blob/main/references/data-shapes.md), theantichris PR #21 (v6 is an object). Field name variants for attendees (`displayName` vs `name`, `people.creator` vs `people.organizer`) appear across versions, so read both.

Important 2026 change: a commit in mvanhorn/printing-press-library (2026-05-13, https://github.com/mvanhorn/printing-press-library/commit/664b98240dbb212d5fd6469323b96c061d8ffd75) reports that "Granola desktop stopped storing meeting documents in cache-v6.json around the same time the .enc encryption rolled out. The cache now holds transcripts/folders/recipes/panels/chats only; documents are fetched lazily from https://api.granola.ai/v2/get-documents." graincrawl added "tolerate Granola cache v8 fallback" (https://github.com/openclaw/graincrawl/commit/9b4b6dab18b4aef5e94e052e1c302826124171e6). Treat `state.documents` as optional even when the cache can be decrypted.

### 3.3 Private desktop API (undocumented, used by the desktop app)

Base `https://api.granola.ai`, all POST with JSON bodies, `Authorization: Bearer <WorkOS access_token>`, gzip responses, optional headers `X-Client-Version: 7.x`, `X-Granola-Platform: darwin`, `X-Granola-Workspace-Id`. Reference: https://github.com/moona3k/granola-export/blob/main/references/endpoints.md and https://github.com/openclaw/graincrawl/blob/main/SPEC.md

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /v2/get-documents` | `{limit: 100, offset: 0, include_last_viewed_panel: true}` or `{include_shared_with_me: true}` | `{docs: [Document], deleted: [...], shared: [...]}`; offset pagination; owned docs only unless `include_shared_with_me` |
| `POST /v1/get-documents-batch` | `{document_ids: [...]}` | up to about 100 documents including shared ones |
| `POST /v1/get-document-transcript` | `{document_id}` | bare array of TranscriptEntry sorted by `start_timestamp`; 404 when no transcript |
| `POST /v1/get-document-panels` | `{document_id}` | array of Panel |
| `POST /v2/get-document-lists` | `{}` | `{lists: [{id, title, document_ids, workspace_id, shared_with}]}` (v1 returns "Not implemented") |
| `POST /v1/get-workspaces`, `/v1/get-user-info`, `/v1/get-feature-flags`, `pecan.api.granola.ai/v1/get-people`, `/v1/get-google-events`, `maple.api.granola.ai/v1/get-action-items` | `{}` | auxiliary data (people directory, calendar events, action items) |
| `POST /v1/get-document`, `/v1/get-documents` (v1), `/v1/get-documents-delta` | | 404, 500 or `{"error":"deprecated"}`; avoid |

Token acquisition, historical: read `~/Library/Application Support/Granola/supabase.json`, whose top-level values are JSON-stringified (double decode): `json.loads(data["workos_tokens"])["access_token"]`. Fields: `access_token` (JWT, `iss https://auth.granola.ai/user_management/<client_id>`), `refresh_token`, `expires_in` 3600 (reported extended to about 6 hours on 2026 builds), `obtained_at`, `session_id`, `sign_in_method`. `cognito_tokens` is a vestigial pre-WorkOS key. Refresh via `POST https://auth.granola.ai/oauth2/token` (form: `grant_type=refresh_token`, `refresh_token`, `client_id` from the JWT) or `https://api.workos.com/user_management/authenticate`; refresh tokens rotate and are single use, so never reuse one. Sources: https://josephthacker.com/hacking/2025/05/08/reverse-engineering-granola-notes.html, https://github.com/moona3k/granola-export/blob/main/references/auth.md, https://github.com/getprobo/reverse-engineering-granola-api

Token acquisition, 2026 timeline:

1. May 2026 (desktop 7.2xx): feature flags `encrypted_supabase_storage` and `encrypted_cache_storage` turned on. Live data moved to `supabase.json.enc`, `cache-v6.json.enc`, `user-preferences.json.enc`, later `stored-accounts.json.enc` and `window-state.json.enc`; plaintext files became frozen stubs. Envelope: AES-256-GCM, `IV(12) || ciphertext || tag(16)`, 32-byte DEK. DEK stored in `storage.dek` as an Electron safeStorage `v10` blob: macOS key = PBKDF2-SHA1(Keychain generic password service "Granola Safe Storage" account "Granola Key", salt "saltysalt", 1003 iterations, 16 bytes), AES-128-CBC, IV sixteen 0x20 bytes. Auth also moved from `supabase.json` to `stored-accounts.json` with `accounts[].tokens` JSON-stringified. Sources: https://github.com/theantichris/granola/issues/24, https://github.com/moona3k/granola-export/pull/1, https://github.com/tomelliot/obsidian-granola-sync/pull/123, https://github.com/tomelliot/obsidian-granola-sync/pull/124, https://github.com/tomelliot/obsidian-granola-sync/pull/130
2. July 2026 (desktop 7.427.x, auto-update around 2026-07-16): on macOS the app decrypts `storage.dek`, imports it via a native `keychain.node` (`getOrCreateDek`, `importDek`) into the data-protection keychain (service `com.granola.app.dek`, access group `QZ7DHHLN25.granola`), then deletes `storage.dek`. Reads from any non-Granola-signed process fail with `errSecMissingEntitlement` (-34018). `granola.db` became the primary store, opened with better-sqlite3-multiple-ciphers using the DEK. Feature flags now on: `encrypted_cache_storage`, `encrypted_preferences_storage`, `encrypted_supabase_storage`, `ydoc_sqlite_storage`, `disable_storage_process`. Sources: https://github.com/openclaw/graincrawl/issues/43, https://github.com/mynameiswhm/granola2markdown/issues/1, https://github.com/servosity/msp-skills/issues/196
3. Windows: the DEK is wrapped by DPAPI. Chain: `%APPDATA%\Granola\Local State` -> `os_crypt.encrypted_key` (base64, strip the `DPAPI` prefix, `CryptUnprotectData` CurrentUser) -> AES-256-GCM decrypt `storage.dek` (strip `v10`) -> base64 DEK -> AES-256-GCM decrypt `stored-accounts.json.enc` or `supabase.json.enc`. Verified by a Windows user on 2026-05-26 (https://github.com/tomelliot/obsidian-granola-sync/pull/132) and still the documented fallback in granz as of 2026-08-30. Whether Granola has since moved the Windows DEK into Credential Manager the way it did on macOS is UNVERIFIED.

Bundled companion CLI (UNVERIFIED beyond one source): graincrawl's SPEC reports `/Applications/Granola.app/Contents/Resources/bin/granola` with `granola notes list`, `granola notes get`, `granola notes transcript get`, talking to the running app over a socket (`granola-companion-cli.sock`) with metadata in `Granola/companion-cli/companion-cli.json`, gated by the `companion_cli` feature flag and inactive on their install. No official documentation exists. If Granola ever enables it, it would be the sanctioned local path.

### 3.4 What the Granola web app exposes

`https://notes.granola.ai/d/<uuid>` is the canonical share and web URL per note (also the `web_url` in the public API and the citation target in MCP). mikedemarais notes that at `app.granola.so` an `access_token` cookie exists; UNVERIFIED for 2026.

### 3.5 Maintenance summary

- Alive and aligned with official surfaces: obsidian-granola-sync (public API), graincrawl (private plus public API, fails closed on macOS 7.427+), granz (own OAuth plus Windows fallback), the various public-API CLIs.
- Alive but blind on current macOS: proofsh/granola-mcp-server, r12consulting/mcp-granola, granola-mcp-plus, granola-toolkit local sync.
- Dead or archived: pedramamini/GranolaMCP (2025), NimbleBrainInc/mcp-granola (archived, points to official MCP), EnotionZ/granola-local-mcp (deprecated), getprobo reverse engineering (archived), chrisguillory (404).

### 3.6 Live check on this Mac (2026-09-07)

- `~/Library/Application Support/Granola/` exists, `.initial-setup-complete` dated 2026-05-27.
- Present: `cache-v6.json` (1,938 bytes, mtime 2026-05-27, a stub), `cache-v6.json.enc` (245,814 bytes, mtime 2026-08-20), `supabase.json.enc` (2,773 bytes, 2026-08-20), `stored-accounts.json.enc` (3,174 bytes), `user-preferences.json.enc`, `granola.db` plus `-wal` (3.5 MB) and `-shm`, `local-state.json` (only `rendererOriginMigrationCompleted`), `Local State` (only `uninstall_metrics`), `IndexedDB`, `WebStorage`, `Session Storage`.
- Absent: `storage.dek`, plaintext `supabase.json`, `stored-accounts.json`, `companion-cli/`.
- Keychain has a generic password with service "Granola Safe Storage" and account "Granola Key" (metadata only was read).
- Plaintext stub structure: `{"cache": {"state": {...52 keys...}, "version": 8}}`. `state` has `transcripts {}`, `documentLists {}`, `documentListsMetadata {}`, `entities {}`, `generatingPanels {}`, `attioRecords null`, `zapierConnections null`, `sync_operations_log []`, and no `documents` or `meetingsMetadata` key at all. This matches the reports that documents no longer live in the JSON cache.
- The Granola.app bundle was not found in `/Applications` or `~/Applications` and no Granola process was running, so the installed version and the companion binary could not be checked here.

Conclusion: on this machine the only working reads are the official MCP server, the official public API (needs Business), and the CSV export.

## 4. Native CRM features

### 4.1 HubSpot (https://docs.granola.ai/help-center/sharing/integrations/hub-spot)

- Requires a Google Workspace or Microsoft 365 account (not personal Gmail or Outlook.com). Connect via Settings > Connectors > HubSpot (OAuth in a browser). Business plan or above per pricing (https://www.granola.ai/pricing lists "Advanced integrations with Attio, Notion, Slack, HubSpot, Affinity, and Zapier" under Business; the billing page says Basic has Slack only).
- Settings > HubSpot: choose the HubSpot entity type, Meeting (default) or Note.
- Per note: HubSpot button, pick contact, company or deal records; Granola links the note to those records. Per folder: Integration Settings > HubSpot, choose which record types; every note added afterwards is attached to matching Contact, Company or Deal records. Not retroactive.
- Matching is by attendee email: "Granola matches meeting attendees to HubSpot records by email address. If no matching records are found, no data will be created in HubSpot." Sync status and errors in Settings > HubSpot.
- What is pushed: the enhanced notes (summary). The private API document carries `hubspot_note_url` once synced.

### 4.2 Attio (https://docs.granola.ai/help-center/sharing/integrations/attio, https://www.granola.ai/integrations/attio)

- OAuth via Settings > Connectors. Launched 2025-09-08 with People and Companies (https://www.granola.ai/updates/three-new-features-customer-relationships). Business plan.
- Per note: Attio button, Granola suggests the people or companies in the meeting, note is added to that record. Per folder: Integrations > Attio, choose Company, People or associated Deals; auto-share for notes added afterwards.
- Matching by attendee email; no match means nothing is created. Granola's Attio guide (https://www.granola.ai/blog/connect-granola-attio-complete-integration-guide) states: AI summary goes to an Attio note on the matched record, action items are inside the note, participant emails are used for matching only, the full transcript stays in Granola, standard objects only (custom objects need Zapier).
- Private API markers: `attio_shared_at`; the desktop cache has `attioRecords` and `attioListPreferences` state keys.

### 4.3 Affinity (https://docs.granola.ai/help-center/sharing/integrations/affinity, https://support.affinity.co/s/article/how-to-integrate-affinity-with-granola)

- Per-user Affinity API key pasted in Settings > Connectors; same email on both accounts. Granola only adds notes, never edits or deletes.
- Per note: Affinity button, Granola suggests People and Company records "based on the email addresses of meeting attendees from your calendar event"; review, then save. Notes land on person and company records, not on the meeting (so Affinity Ascend suggestions are not triggered). Affinity notes appear as Manual capture. Desktop only.

### 4.4 Salesforce (https://www.granola.ai/integrations/salesforce, https://www.granola.ai/blog/connect-granola-salesforce-zapier)

- No generally available native connector as of February 2026 blog; the integration page now says "Granola is rolling out a native Salesforce connector to selected workspaces. To register interest, choose Join waitlist on Salesforce in Settings > Connectors." Otherwise via Zapier (Create Record on Opportunity, Contact or Task; Zapier Professional needed because Salesforce is a premium app).

### 4.5 Zapier (https://docs.granola.ai/help-center/sharing/integrations/zapier)

- Paid plans, desktop apps only. Triggers: "Note Added to Granola Folder" (only notes added after the Zap exists; requires Collaborator or Owner on the folder) and "Note Shared to Zapier" (manual from the note sidebar). Multi-workspace users must select the workspace in the trigger.
- Payload: Title; Creator (name and email); Attendees (list, each with name and email); Calendar event (title and date/time); My Notes (private typed notes); Summary (markdown); Transcript (full); Link (share link). This is the richest no-code export and includes attendee emails.
- Granola exposes no raw webhooks outside the public API; Zapier polls (about 2 minutes on paid Zapier plans, 15 on free).

### 4.6 People and Companies (https://docs.granola.ai/help-center/people-and-companies)

- Sidebar views that list every attendee and company from meetings, with profile pictures, job titles and company info enriched "from various data sources" in the background.
- Populated only from calendar events: "They weren't listed as an attendee on the calendar event", "The note wasn't created from a calendar event", "They declined the meeting" are the documented reasons someone is missing. No manual add.
- Not exposed by the public API as a separate resource. The MCP `list_meetings` output does carry `from <Company>` per participant, and the private API has `pecan.api.granola.ai/v1/get-people` and `berry.api.granola.ai/v1/get-about-me-profile`.

### 4.7 Does Granola store attendee emails on each meeting

Yes. Public API: `attendees[].email` plus `calendar_event.invitees[].email` and `calendar_event.organiser`. MCP: `<known_participants>` lines include `<email>`. Zapier: attendees with name and email. Local cache and private API: `people.attendees[].email`, `google_calendar_event.attendees[].email`, `meetingsMetadata[id].attendees[].email`. Ad-hoc notes without a calendar event have an empty attendee list unless the user adds people manually (`people.manual_attendee_edits`).

## 5. Export options without MCP or API

- CSV (https://docs.granola.ai/help-center/sharing/exporting-notes): Settings > Profile > Generate CSV, choose workspaces, emailed within a few hours. Official text: "The CSV includes the title, note summary, transcript, and other basic details for each note", only notes you own, full history including notes older than 30 days on Basic, only notes that have a summary, no admin or workspace-wide export. The billing page describes it as "titles and summaries", an inconsistency. A July 2026 free-plan test (https://hirekai.ai/blog/export-granola-notes) found 75 rows with full transcripts of about 21,000 characters each, an empty `notes` column, no speaker labels, one export per 24 hours and a 24-hour download link. Column names beyond that are UNVERIFIED.
- Markdown or JSON: no official markdown or JSON export in the app. Per-note copy exists (copy summary, copy whole transcript from the transcript panel: https://docs.granola.ai/help-center/taking-notes/transcription). Notion (one note at a time into a dedicated database) and Slack (summary post) are push integrations, not exports.
- API: the public API is the official JSON route (Business and Enterprise), `GET /v1/notes/{id}?include=transcript` returns summary markdown, attendees, calendar event and speaker-attributed transcript.
- Speaker labels: transcripts are `Me` and `Them` by default (microphone vs system audio). Speaker tags add real names live only, for Google Meet via the Granola browser extension (macOS and Windows) and for Zoom via the Zoom desktop app plus macOS Accessibility (macOS only): https://docs.granola.ai/help-center/taking-notes/speaker-attribution and https://docs.granola.ai/help-center/taking-notes/speaker-attribution-zoom. iOS uses diarization buckets `Speaker A/B`. The CSV export carries no speaker labels; the API, MCP and cache do.
- Ad-hoc meetings: Granola never records unless a note is opened. New Note or the "call detected" notification starts an ad-hoc note with no calendar event, no scheduled end time (auto-stop then relies on the call app releasing the microphone, or 15 minutes of silence), and no attendees unless added manually: https://docs.granola.ai/help-center/taking-notes/transcription. In-person meetings are supported on desktop via the microphone and on iOS and Android.
- Transcript retention: users can enable auto-deletion of transcripts (1 day to 1 year, one-week cooldown); Enterprise admins can set a workspace policy that deletes immediately. Notes survive, transcripts do not, and the public API then excludes such notes because it requires a transcript. https://docs.granola.ai/help-center/consent-security-privacy/transcript-auto-deletion
- Audio is never stored; transcription is real time and audio is deleted (https://www.granola.ai/blog/granola-mcp-claude-chatgpt-cursor).
- Account transfer moves all notes and transcripts to another Granola account (destructive): https://docs.granola.ai/help-center/transfer-notes-between-accounts

## 6. Platform coverage and file locations

| Platform | Status | Data directory | Notes |
| --- | --- | --- | --- |
| macOS | Original platform | `~/Library/Application Support/Granola/` | Files listed in 3.6. Live cache and tokens unreadable by third parties since 7.427 (July 2026). Zoom speaker tags macOS only. |
| Windows | Launched 2025-06-11 (https://www.granola.ai/updates, "Introducing Granola for Windows") | `%APPDATA%\Granola\` (Roaming), files `Local State`, `storage.dek`, `stored-accounts.json.enc`, `supabase.json.enc`, `cache-v*.json` and `.enc`; WSL sees `/mnt/c/Users/<user>/AppData/Roaming/Granola` | Per-user NSIS installer (`Granola-<ver>-win-x64.exe /S`), winget listing (https://addremoveprograms.com/application/granola/, 7.498.1 on 2026-08-20). DPAPI decryption path documented in obsidian-granola-sync PR #132 and granz. Whether Windows still writes `storage.dek` on the newest builds is UNVERIFIED. |
| iOS | Live (iPhone, Apple Watch, phone calls) | n/a | Single audio stream, diarization labels. Sharing to CRMs must be done from desktop. https://docs.granola.ai/help-center/ios/getting-started |
| Android | Launched 2026-07-01 (https://www.granola.ai/blog/introducing-granola-for-android) | n/a | In-person notes only. |
| Linux | No desktop app; granola.ai lists "macOS, Windows, iOS, Android" | community tools guess `~/.config/Granola/` | Only relevant under WSL. |

Managed installs (https://docs.granola.ai/help-center/getting-started/managed-installations): unauthenticated endpoints `https://api.granola.ai/v1/get-versions` (returns `{"production": "7.205.0", "beta": ...}` style JSON), `https://api.granola.ai/v1/download-latest` (macOS) and `/v1/download-latest-windows`. Useful for the plugin's doctor command to print the current production version next to the installed one.

Plans and prices (https://www.granola.ai/pricing, https://docs.granola.ai/help-center/managing-your-account/subscriptions-and-billing): Basic free with 30-day in-app history and Slack only; Business 14 USD per user per month with unlimited history, CRM and Zapier integrations, MCP in all apps, API access; Enterprise from 35 USD with SSO, admin controls for sharing and API access. Monthly billing only, per workspace, per seat.

## 7. Recommended ingestion design

### 7.1 Source adapters, in the order the plugin should try them on macOS

The brief asked for local cache first, MCP second, manual export third. The evidence above forces a change on current macOS builds: the local cache cannot be decrypted by third-party code since July 2026, and even where it can be, documents are no longer stored in it. Proposed order, with a `doctor` step that picks the first adapter whose preconditions hold:

1. Official public API adapter (Business or Enterprise). Preconditions: a `grn_` key in the plugin's secret store. Why first: structured JSON, attendee emails, `calendar_event_id`, scheduled times, folder membership, speaker-attributed transcript, `updated_after` incremental sync, and webhooks for near-real-time. Poll `GET /v1/notes?updated_after=<watermark>&page_size=30`, then `GET /v1/notes/{id}?include=transcript`, falling back to the paged transcript endpoint on 413. Stay under 5 requests per second and 25 burst; retry on 429. Optionally register a webhook (`note.generated`, `note.access_granted`, `note.edited`) pointing at a relay if the user has one; verify Standard Webhooks signatures.
2. Official MCP adapter (all plans, including Basic). Preconditions: `claude mcp add granola --transport http https://mcp.granola.ai/mcp` completed and authenticated. Use `list_meetings` with `time_range: custom` windows (walk backwards in 30-day slices; Basic only returns 30 days), `get_meetings` in batches of 10, `get_meeting_transcript` on paid plans. Parse the XML-ish envelope. Budget under 100 requests per minute. Prefer `involvement: {captured_by_me: true}` for the user's own sales calls. Store the meeting UUID as the primary id.
3. Local cache adapter, behind detection. Enable only when a readable cache exists: plaintext `cache-v*.json` whose `cache.state.documents` is non-empty (pre-May-2026 installs), or on Windows where `Local State` plus `storage.dek` plus `cache-v6.json.enc` can be decrypted with DPAPI. On macOS with `storage.dek` absent and `.enc` files present, report "Granola 7.427+ keeps its key in the app-scoped keychain; use the API or MCP" and never fall back to the stale plaintext stub silently. Never write to the Granola directory, copy files to a temp dir before parsing, never log tokens.
4. Manual import adapter. Accept the Granola CSV (Settings > Profile > Generate CSV), markdown files produced by any of the export tools in section 3, or a pasted transcript. CSV rows have no speaker labels and no emails beyond what the summary text contains; treat them as low-confidence Interactions that need a human to pick the deal.

Keep the private desktop API out of the default path: it is undocumented, its token is unreachable on current macOS, and refresh tokens rotate single-use.

### 7.2 Canonical Interaction mapping

Target record: `{id, at, title, participants[{name, email}], transcript, notes, durationSec, source}`.

| Field | Public API | MCP | Local cache (legacy or Windows) | CSV |
| --- | --- | --- | --- | --- |
| `id` | `not_...` id; also store the UUID parsed from `web_url` (`/d/<uuid>`) so API, MCP and cache records dedupe on the UUID | meeting UUID | `documents[uuid].id` | hash of title plus date (UNVERIFIED whether the CSV has an id column) |
| `at` | `calendar_event.scheduled_start_time`, else first transcript `start_time`, else `created_at` | `date` attribute of `<meeting>` (locale string, parse), else first transcript timestamp | `google_calendar_event.start.dateTime`, else first `transcripts[uuid][].start_timestamp`, else `created_at` | date column |
| `title` | `title`, else `calendar_event.event_title` | `title` attribute | `title`, else `google_calendar_event.summary` | title column |
| `participants` | union of `attendees[]` (name, email), `calendar_event.invitees[]` (email only), `owner`, `calendar_event.organiser` | parse `Name (role) from Company <email>` lines; keep `company` as an extra attribute | `people.attendees[]` (email, displayName or name), `meetingsMetadata[uuid].attendees[]`, `google_calendar_event.attendees[]`, plus `people.creator` | none reliable |
| `transcript` | join items as `[HH:MM:SS] <speaker.name or (attribution me -> owner.name, them -> "Them")>: text`, HH:MM:SS relative to the first `start_time` | lines already formatted `[00:00:15] Name: text` | sort `transcripts[uuid]` by `sequence_number` or `start_timestamp`; speaker = `speaker` field if set, else `source == "microphone"` -> owner name, else "Them" | transcript column, single voice |
| `notes` | `summary_markdown` (append `private_notes_markdown` when non-null, flagged private) | `<summary>` block from `get_meetings` plus private notes if present | `documentPanels[uuid][*].content` (ProseMirror to markdown, `original_content` may be HTML) plus `notes_markdown` (user's own notes) | summary column |
| `durationSec` | `scheduled_end_time - scheduled_start_time`, else last transcript `end_time - first start_time` | last transcript timestamp | last `end_timestamp - first start_timestamp`, else calendar end minus start (never use `created_at`/`updated_at`) | none |
| `source` | `granola:public-api` | `granola:mcp` | `granola:cache` | `granola:csv` |

Extra fields worth keeping on the record for linking and dedup: `web_url`, `calendar_event_id`, `organiser`, `folder_membership[]`, `owner.email`, `workspace` (from `get_account_info`), and for cache records the CRM markers `hubspot_note_url`, `attio_shared_at`, `affinity_note_id`.

### 7.3 Fields available for linking a meeting to a CRM deal

- Attendee emails: on every official surface. Derive domains, drop the user's own domain and workspace members, then match external domains to CRM companies and emails to CRM contacts. This is exactly how Granola's own HubSpot, Attio and Affinity integrations match ("by email address").
- Organiser email and calendar event id: public API (`calendar_event.organiser`, `calendar_event_id`) and cache (`google_calendar_event.organizer.email`, `google_calendar_event.id`). The calendar event id lets the plugin join against a CRM's calendar sync (Twenty's connector does this with `eventExternalId` and `iCalUid`).
- Time fields: `scheduled_start_time` and `scheduled_end_time` (API, cache), transcript timestamps (all), `created_at` and `updated_at` (all). Use the meeting time against deal open and close dates when a company has several deals.
- Title and event title: keyword match against deal names.
- Folder membership: API `folder_membership[].name`, cache `documentLists`, MCP `list_meeting_folders`. A folder naming convention such as `Deals/<deal name>` gives a deterministic link and doubles as the trigger for Granola's own folder-based CRM auto-share.
- Company enrichment: MCP participant lines carry `from <Company>`; People and Companies is in-app only otherwise.
- Existing CRM links: cache and private API expose `hubspot_note_url`, `attio_shared_at`, `affinity_note_id`, which tell the plugin a note is already attached to a CRM record.

Suggested linking rule: score candidates by (a) any attendee email equal to a deal contact email, (b) external domain equal to the deal's company domain, (c) meeting time inside the deal's active window, (d) folder or title match. Auto-link only when one deal scores clearly above the rest; otherwise store the candidates and ask the user once, then remember the attendee-to-deal mapping so later meetings with the same people link automatically. Skip internal-only meetings (all attendees share the user's domain) and ad-hoc notes with no attendees unless the user tags them.

### 7.4 Edge cases to handle

- Basic plan: MCP and the in-app history stop at 30 days; the CSV export reaches older notes. The API needs Business.
- Public API returns only notes that have both a summary and a transcript; ad-hoc notes without transcripts and notes whose transcript was auto-deleted disappear from it. Use MCP `get_meetings` or the CSV for those.
- Ids differ by surface: `not_` ids (API) versus UUIDs (MCP, cache, web URL). Normalise on the UUID.
- Transcripts: `TRANSCRIPT_TOO_LARGE` paging on the API; `Me`/`Them` only unless speaker tags were on during the call; iOS gives `Speaker A/B`.
- Workspaces: MCP follows the desktop app's active workspace; API keys are per workspace; plans are per workspace.
- Rate limits: 5 rps sustained and 25 burst on the API, about 100 rpm on MCP.
- Privacy: transcripts include other people who did not consent to downstream processing; keep raw transcripts local, send only what the CRM needs, and respect `privacy_mode_enabled` and `sharing_link_visibility: private` markers when present.
