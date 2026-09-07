# HubSpot sales-data access for a Claude Code plugin: reference

Compiled 2026-09-07 from developers.hubspot.com, knowledge.hubspot.com, the npm registry (package tarball inspected), live probes of `mcp.hubspot.com`, and community threads where the official docs are silent. Every claim carries a source URL; items marked **[UNVERIFIED]** or **[INFERRED]** could not be confirmed against an official source in this session.

Conventions: `2026-03` in a path is HubSpot's date-based API version name, not a date to edit. Legacy `/crm/v3/` and `/crm/v4/` paths still work (see section 2.0).

---

## 0. TL;DR for the design decision

| Question | Answer |
|---|---|
| Is there an official HubSpot MCP server? | Yes, two CRM-facing ones: the **remote** server at `https://mcp.hubspot.com` (GA 2026-04-13, OAuth 2.1 + PKCE, 16 tools) and the **local** npm package `@hubspot/mcp-server` (v0.4.0, last published 2025-06-18, still labelled beta, private-app token). A third, the *Developer* MCP server (`hs mcp setup`), is for building HubSpot apps, not for CRM data. |
| Can MCP read engagements (calls/emails/meetings/notes)? | Remote: yes (read + create/update) since GA, but **blocked entirely if the account has Sensitive Data turned on**. Local npm: engagement objects are not in its advertised object list, but its object tools accept any `objectType` string and proxy straight to `/crm/v3/objects/{objectType}`, so `calls`, `emails`, `meetings`, `notes` should work [INFERRED from source]; `hubspot-get-engagement` reads any engagement by ID via the legacy v1 engagements API. |
| Property history, pipelines, owners via MCP? | Remote: owners yes (`search_owners`); pipelines only indirectly (stage IDs/labels come back as the `dealstage` property's enumeration options via the property-definition tool); **no property-history tool**. Local: no history, no pipelines tool, owner lookup only for the token's own user. **`propertiesWithHistory` is REST-only.** |
| Can transcripts be read via API? | There is a transcript GET endpoint (`/crm/extensions/calling/2026-03/transcripts/{transcriptId}`, scope `crm.extensions_calling_transcripts.read`) whose response enum includes `HUBSPOT_GENERATED`, but (a) HubSpot documents it as OAuth **public-app** only and its OpenAPI spec lists no private-app security scheme, and (b) there is **no documented way to get a transcriptId from a call**; the `hs_call_transcription_id` property is null in most portals per community reports through Dec 2025. Realistic path today: `hs_call_recording_url` -> download -> transcribe yourself, plus the AI summary in `hs_call_summary` / the Notetaker recap API (2026-09-beta). |
| Minimum read scopes for a private app | `crm.objects.deals.read`, `crm.objects.contacts.read`, `crm.objects.companies.read`, `crm.objects.owners.read`, `crm.schemas.deals.read`, `sales-email-read` (needed for email bodies). Engagement objects are gated by the contacts/companies/deals read scopes; the `crm.objects.calls.read`-style scopes exist in OpenAPI specs but are not selectable in the app UI. |
| Test data | Developer test accounts: free, up to 10, 90-day Enterprise trials, blank (no sample data), all CRM write APIs work so you can seed calls/emails/meetings/notes; HubSpot Calling and CI cannot be exercised there, and transcripts cannot be seeded through a private app. |
| Deadline to note | **Legacy private-app creation is being removed from the UI on 2026-09-28 (new accounts) / 2026-10-26 (existing accounts)**; replacement is "Service Keys". Existing private apps keep working. |

---

## 1. The official HubSpot MCP servers

### 1.1 Three different things share the name

| Name | What it is | Auth | Source |
|---|---|---|---|
| **HubSpot MCP server (remote)** | HubSpot-hosted Streamable HTTP server at `https://mcp.hubspot.com` for CRM data. Public beta Sept 2025, GA 2026-04-13. | OAuth 2.1 + PKCE via an "MCP Auth App" created in the account (Development > MCP Auth Apps) | https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server ; https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available |
| **`@hubspot/mcp-server` (local npm, stdio)** | Node process run with `npx -y @hubspot/mcp-server`; proxies to HubSpot REST. Package description literally says "MCP Server for developers building HubSpot Apps" but the tools are CRM tools. | `PRIVATE_APP_ACCESS_TOKEN` env var (private app token) | https://www.npmjs.com/package/@hubspot/mcp-server |
| **Developer MCP server (local)** | Installed with `hs mcp setup` (HubSpot CLI >= 8.2.0); tools for scaffolding apps/CMS assets in your IDE. Not for CRM records. | CLI auth | https://developers.hubspot.com/docs/developer-tooling/local-development/developer-mcp/setup |
| **HubSpot connector for Claude** | Packaged connector in claude.ai/Claude Desktop (Settings > Connectors). Runs on the remote MCP server underneath. Needs a paid Anthropic plan; first connection by a HubSpot Super Admin / App Marketplace user. | OAuth | https://knowledge.hubspot.com/integrations/set-up-and-use-the-hubspot-connector-for-claude |

Overview page: https://developers.hubspot.com/ai-tools/mcp

### 1.2 Remote server (`https://mcp.hubspot.com`)

**Setup (official):**
1. In HubSpot: Development > MCP Auth Apps > Create MCP auth app (name, optional description, redirect URL(s), icon). HubSpot generates a client ID + client secret. For MCP Inspector testing add redirect `http://localhost:6274/oauth/callback/debug`.
2. Point an MCP client at `https://mcp.hubspot.com/` (transport: Streamable HTTP) with that client ID/secret. **PKCE (S256) is mandatory.**
3. During the OAuth flow the user picks the HubSpot account and grants permissions. "You don't explicitly define the app's scopes. Instead, available scopes are automatically determined by the tools available in the MCP server at the time of installation and the permissions that the user chooses to grant." Tool additions can require re-install (`REQUIRES_REAUTHORIZATION`).
Source: https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server

**Live probe results (2026-09-07, unauthenticated):**
- `GET https://mcp.hubspot.com/.well-known/oauth-protected-resource` -> `{"resource":"https://mcp.hubspot.com","authorization_servers":["https://mcp.hubspot.com"],"scopes_supported":[],"resource_documentation":"https://developers.hubspot.com/mcp"}`
- `GET https://mcp.hubspot.com/.well-known/oauth-authorization-server` -> issuer `https://mcp.hubspot.com`; `authorization_endpoint` `https://mcp.hubspot.com/oauth/authorize/user`; `token_endpoint` `https://mcp.hubspot.com/oauth/v3/token`; `grant_types_supported` `authorization_code, refresh_token, client_credentials`; `token_endpoint_auth_methods_supported` `["client_secret_post"]`; `code_challenge_methods_supported` `["S256"]`; **no `registration_endpoint`** (so no advertised Dynamic Client Registration). `POST /oauth/v3/register` with `{}` returns 400 rather than 404, so an unadvertised registration endpoint may exist [UNVERIFIED].
- `POST https://mcp.hubspot.com/` and `POST https://mcp.hubspot.com/anthropic` both return `401` with `WWW-Authenticate: Bearer resource_metadata="https://mcp.hubspot.com/.well-known/oauth-protected-resource"`. The `/anthropic` path therefore exists but is undocumented by HubSpot; several third-party guides (e.g. https://gtmepulse.com/insights/claude-code-mcp-hubspot/ , https://mcptrove.com/server/hubspot-mcp ) say `claude mcp add --transport http hubspot https://mcp.hubspot.com/anthropic` followed by `/mcp` sign-in works without supplying a client ID/secret. **[UNVERIFIED]** whether that route works without pre-registered credentials; the official docs only describe the MCP-Auth-App route.

**Data the remote server exposes (official, as of 2026-09-01 doc revision):**
- Read: contacts, companies, deals, tickets, users, carts, invoices, orders, line items, products, quotes, subscriptions, segments (lists); **activities: calls, emails, meetings, notes, tasks**; blog posts, landing pages, site pages, campaigns, marketing events; conversations (inbox/help desk messages and threads, with inbox-permission restrictions); marketing emails (drafts, previews, analytics, health diagnostics).
- Write: contacts, companies, deals, tickets, line items, products; activities (calls, emails, meetings, notes, tasks); marketing email drafts. **No delete.**
- "Behind the scenes, the HubSpot MCP server is based on the CRM search API, which currently doesn't include vector search capabilities."
- "If your HubSpot account has Sensitive Data turned on, activity objects (calls, emails, meetings, notes, and tasks) and conversation data will be blocked from access through the MCP server. This restriction is specific to the MCP server and does not apply to the standard CRM APIs."
- All actions respect the authenticated user's HubSpot permissions.
- Claude connector KB adds: bulk create/update capped at 10 records per action; custom validation rules (pipeline stage validations, association label validations) are not applied on writes; "Custom objects, unstructured data, and associated engagements are all not yet available" (FAQ text; the object table on the same page shows engagements Read/Create/Update = yes, so the FAQ line is likely stale) [UNVERIFIED which is current].

**Tool list.** The official page lists 16 tools by description only; names below are from third-party enumerations of the live server (https://daeda.tech/hubspot-mcp/ , https://tryglen.com/mcp/servers/hubspot , https://chatforest.com/reviews/hubspot-mcp-server/) and match each official description. Only `get_user_details` is named in HubSpot's own docs.

| Tool (name per third parties) | Official one-line description |
|---|---|
| `get_user_details` | Authenticated user's info, account details, per-object read/write access. Call first. |
| `search_crm_objects` | Search/filter CRM records with filter groups, text query, sorting, pagination. Based on the CRM search API. Max 5 filter groups x 6 filters; AND within a group, OR across groups; max 200 results/page. |
| `get_crm_objects` | Fetch one or more CRM objects by ID; max 100 IDs per request. |
| `manage_crm_objects` | Create or update CRM records or activities. |
| `search_properties` | Keyword search of property definitions (names, labels, descriptions); max 5 keywords. |
| `get_properties` | Full property definitions incl. data types and enumeration values (large; fetch specific names). |
| `search_owners` | Find owners by name/email or by ID; max 100 results. |
| `get_campaign_contacts_by_type` | Paginated contact IDs for a campaign by attribution type. |
| `get_campaign_analytics` | Campaign metrics or revenue attribution for one or more campaigns. |
| `get_campaign_asset_types` | Asset type names usable as campaign assets. |
| `get_campaign_asset_metrics` | Metrics/properties for CRM objects associated with a campaign. |
| (conversations search) | Search conversations/messages from inboxes by CRM object, time range, or keyword; aggregate by channel/inbox/status. |
| (list inboxes/channels) | List inboxes, channels, channel instances (call before conversation search). |
| (marketing email analytics) | Account-level aggregate send stats, MX-group health diagnostics, per-contact delivery/engagement for a send. |
| (manage marketing emails) | List templates/subscription types/from addresses; create/update/clone drafts; edit/preview content; A/B variants. Needs extra app permissions. |
| `submit_feedback` | Send feedback about the MCP server to HubSpot. |

A doc mirror (hubspot.mintlify.io) also shows two newer descriptions, "Search HubSpot schema to discover available object types" and "Query HubSpot CRM data ... cross-object associations", suggesting schema and association tools have been or are being added [UNVERIFIED].

**Practical read pattern through the remote server for a deal walk:** `search_crm_objects` on `calls`/`emails`/`meetings`/`notes` filtered on the pseudo-property `associations.deal EQ {dealId}` (the CRM search API supports `associations.{objectType}` filters; see 2.6), then `get_crm_objects` for full bodies. There is no tool for `propertiesWithHistory`, so stage-change timelines are not available via MCP.

**Limits:** none published for the MCP layer itself; the Claude connector KB says "All functionality in Claude is subject to HubSpot's API usage limits and guidelines" (section 2.8; note the search API's 5 req/s per account cap applies since the server is search-based).

**Claude Code specifics (from https://code.claude.com/docs/en/mcp):**
- Add: `claude mcp add --transport http hubspot https://mcp.hubspot.com` then `/mcp` to run the browser OAuth flow; or `claude mcp login hubspot` (v2.1.186+), `--no-browser` for SSH/headless.
- If a server lacks Dynamic Client Registration (HubSpot advertises none), supply pre-registered credentials: `claude mcp add --transport http --client-id <id> --client-secret --callback-port 8080 hubspot https://mcp.hubspot.com` (`--client-secret` prompts; or `MCP_CLIENT_SECRET=...` env). `.mcp.json` form: `{"type":"http","url":"https://mcp.hubspot.com","oauth":{"clientId":"...","callbackPort":8080}}` (the secret is never stored in the file). The MCP Auth App's redirect URL must match Claude Code's callback (`http://localhost:8080/callback` when `callbackPort` is 8080 [INFERRED]).
- Headless `claude -p` / Agent SDK runs cannot complete OAuth; sign in once interactively first.
- Output caps: `MAX_MCP_OUTPUT_TOKENS` default 25,000 (warning at 10,000); a server can raise per-tool via `_meta["anthropic/maxResultSizeChars"]` up to 500,000 chars.
- Plugins can bundle MCP servers via `.mcp.json` at plugin root or `mcpServers` in `.claude-plugin/plugin.json`, with `${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PLUGIN_DATA}`, `${VAR}` / `${VAR:-default}` expansion in `command`, `args`, `env`, `url`, `headers`, `headersHelper`; http/sse/ws transports supported (https://code.claude.com/docs/en/plugins-reference). A bundled remote OAuth server whose auth server requires `client_secret_post` cannot ship its secret in the plugin, so **a plugin bundling the remote HubSpot server depends on the unverified `/anthropic` public-client route or on the user running `claude mcp add ... --client-secret` themselves.**

### 1.3 Local server `@hubspot/mcp-server` (stdio)

- npm: https://www.npmjs.com/package/@hubspot/mcp-server ; registry: https://registry.npmjs.org/@hubspot/mcp-server . Latest **0.4.0, published 2025-06-18**; 8 versions since 2025-04-25; ~14k weekly downloads; MIT; no `repository` field; https://github.com/HubSpot/mcp-server is an empty repo. README still says "beta ... subject to the Early Adopter Program terms". Not marked deprecated.
- Binary name `mcp-hubspot`. Deps: `@modelcontextprotocol/sdk ^1.0.1`, `dotenv`, `zod`.
- Env (from `dist/utils/client.js`): `PRIVATE_APP_ACCESS_TOKEN` (or `HUBSPOT_ACCESS_TOKEN`), optional `BASE_URL_OVERRIDE` (default `https://api.hubspot.com`). Sends `Authorization: Bearer <token>`.
- Claude Desktop / `.mcp.json` config (official README):

```json
{ "mcpServers": { "hubspot": {
    "command": "npx", "args": ["-y", "@hubspot/mcp-server"],
    "env": { "PRIVATE_APP_ACCESS_TOKEN": "<your-private-app-access-token>" } } } }
```

Claude Code: `claude mcp add hubspot -e PRIVATE_APP_ACCESS_TOKEN=pat-... -- npx -y @hubspot/mcp-server` (stdio) or the same JSON in a plugin `.mcp.json` with `"PRIVATE_APP_ACCESS_TOKEN": "${HUBSPOT_PRIVATE_APP_TOKEN}"`.

**Full tool list (README; endpoints verified by reading `dist/` of 0.4.0):**

| Category | Tool | Description | Underlying call |
|---|---|---|---|
| OAuth | `hubspot-get-user-details` | Validates token; returns user, hub, app, scopes, owner, account info | `POST /oauth/v2/private-apps/get/access-token-info` then `GET /crm/v3/owners/{userId}?idProperty=userId&archived=false` |
| Objects | `hubspot-list-objects` | Paginated list of records for an object type | `GET /crm/v3/objects/{objectType}` (properties, associations, after, limit) |
| Objects | `hubspot-search-objects` | Filtered search (filterGroups, query, sorts) | `POST /crm/v3/objects/{objectType}/search` |
| Objects | `hubspot-batch-create-objects` | Create many records | `POST /crm/v3/objects/{objectType}/batch/create` |
| Objects | `hubspot-batch-update-objects` | Update many records | `POST /crm/v3/objects/{objectType}/batch/update` |
| Objects | `hubspot-batch-read-objects` | Read many by ID | `POST /crm/v3/objects/{objectType}/batch/read` (no `propertiesWithHistory` exposed) |
| Objects | `hubspot-get-schemas` | Custom object schemas | `GET /crm/v3/schemas` |
| Properties | `hubspot-list-properties` | All properties for an object type | `GET /crm/v3/properties/{objectType}` |
| Properties | `hubspot-get-property` | One property definition | `GET /crm/v3/properties/{objectType}/{propertyName}` |
| Properties | `hubspot-create-property` / `hubspot-update-property` | Create/update custom property | `POST`/`PATCH /crm/v3/properties/...` |
| Associations | `hubspot-batch-create-associations` | Create associations in bulk | `POST /crm/v4/associations/{from}/{to}/batch/create` |
| Associations | `hubspot-list-associations` | Associations from one record to an object type | `GET /crm/v4/objects/{objectType}/{objectId}/associations/{toObjectType}?limit=500[&after=]` |
| Associations | `hubspot-get-association-definitions` | Valid association types/labels between two objects | `GET /crm/v4/associations/{from}/{to}/labels` |
| Engagements | `hubspot-create-engagement` | Create **NOTE or TASK** only ("EMAIL, CALL, MEETING are NOT supported yet") | `POST /engagements/v1/engagements` (legacy) |
| Engagements | `hubspot-get-engagement` | Any engagement by ID | `GET /engagements/v1/engagements/{id}` (legacy; returns `engagement`, `associations`, `metadata` incl. body/subject/recordingUrl fields) |
| Engagements | `hubspot-update-engagement` | Update an engagement | `PATCH /engagements/v1/engagements/{id}` |
| Workflows | `hubspot-list-workflows` / `hubspot-get-workflow` | v4 automation flows | `GET /automation/v4/flows[/{id}]` |
| Links | `hubspot-generate-feedback-link` / `hubspot-get-link` | Feedback URL; deep links into the HubSpot UI | local |

Also ships one MCP prompt: "HubSpot Sales Coach" ("AI assistant that helps identify at-risk deals in HubSpot").

**Object-type coverage (from `dist/types/objectTypes.js`):** the advertised list `HUBSPOT_OBJECT_TYPES` = appointments, companies, contacts, courses, deals, leads, line_items, listings, marketing_events, **meetings**, orders, postal_mail, products, quotes, services, subscriptions, tickets, users. `calls`, `emails`, `notes`, `tasks`, `communications` appear only in the ID map (`calls 0-48, emails 0-49, meetings 0-47, notes 0-46, tasks 0-27, communications 0-18`). Every `objectType`/`toObjectType` parameter is `z.string()` with the list only in the description, and the tools interpolate the string directly into `/crm/v3/objects/{objectType}` / `/crm/v4/objects/{objectType}/...`, so passing `calls`, `emails`, `notes` should work end-to-end **[INFERRED from source; not executed]**. Property history: not exposed. Pipelines: no tool (use `hubspot-get-property deals dealstage` to read stage options). Owners: only the token's own owner.

**Verdict for the plugin:** the local server is a thin proxy with no history/pipeline coverage and a year-old release; for a deal-history walk, direct REST (section 2) is simpler and fully featured, and the same private-app token works for both.

### 1.4 Developer MCP server
`npm install -g @hubspot/cli` (>= 8.2.0), `hs mcp setup`, pick clients (Claude Code, Codex CLI, Cursor, Gemini CLI, VS Code, Windsurf); registers as `HubSpotDev` (`/mcp` in Claude Code). Requires Developer Platform v2025.2+. Not relevant to reading CRM data. https://developers.hubspot.com/docs/developer-tooling/local-development/developer-mcp/setup

---

## 2. REST endpoints to walk a deal's history

### 2.0 Versioning and base URL
- Base: `https://api.hubapi.com` (all versions). Third parties cite `https://api-eu1.hubapi.com` for EU-hosted portals [UNVERIFIED this session].
- Since 2026-03-30 HubSpot uses date-based versions: current GA `/2026-03/`, betas `/2026-09-beta/`; new GA every March and September; each GA version is Current 6 months, Supported 12 more (18-month minimum). Legacy `v1-v4` paths "are still supported and available at their previous URLs"; "current v4 APIs become unsupported with the release of /2027-03/". Path shape changes: `/crm/v3/objects/deals` -> `/crm/objects/2026-03/deals`; `/crm/v4/associations/...` -> `/crm/associations/2026-03/...`; `/crm/v3/owners` -> `/crm/owners/2026-03`; `/crm/v3/pipelines/deals` -> `/crm/pipelines/2026-03/deals`; `/crm/v3/properties/deals` -> `/crm/properties/2026-03/deals`.
  Sources: https://developers.hubspot.com/docs/developer-tooling/platform/versioning ; https://developers.hubspot.com/blog/a-developers-guide-to-hubspots-date-based-api-versioning ; https://developers.hubspot.com/blog/date-based-api-versioning-migration-playbook ; https://developers.hubspot.com/docs/api-reference/latest/overview
- Auth: `Authorization: Bearer <private app token | OAuth access token>`.
- Object type IDs usable in place of names: contacts `0-1`, companies `0-2`, deals `0-3`, tickets `0-5`, notes `0-46`, meetings `0-47`, calls `0-48`, emails `0-49`, tasks `0-27`, communications `0-18`, postal mail `0-116`, users `0-115`, line items `0-8`, products `0-7`, quotes `0-14`, leads `0-136`. https://developers.hubspot.com/docs/api-reference/latest/crm/using-object-apis

### 2.1 Deals
Guide: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/deals/guide (legacy: https://developers.hubspot.com/docs/api-reference/legacy/crm/objects/deals/guide). Object definition: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/deals/object-definition . Scope: `crm.objects.deals.read`.

- `GET /crm/objects/2026-03/deals/{dealId}?properties=...&propertiesWithHistory=dealstage,closedate,amount,hubspot_owner_id&associations=contacts,companies,calls,emails,meetings,notes`
- `GET /crm/objects/2026-03/deals?limit=100&after=...&properties=...` (list; default 10, max 100; **max 50 when `propertiesWithHistory` is used** — error text "You can only request at most 50 objects in one request for properties with history", https://github.com/HubSpot/hubspot-api-python/issues/143 , https://community.hubspot.com/t/400-response-when-calling-objects-deals-with-propertieswithhistory-and-limit/114363 )
- `POST /crm/objects/2026-03/deals/batch/read` body `{"properties":[...],"propertiesWithHistory":["dealstage"],"inputs":[{"id":"7891023"}]}`; max 100 inputs (50 with history [INFERRED from the same error]); `idProperty` for custom unique IDs; **batch read cannot return associations**.
- Search: `POST /crm/objects/2026-03/deals/search` (section 2.6 for grammar). Example for closed-won deals in a window:

```json
{ "filterGroups": [ { "filters": [
    { "propertyName": "hs_is_closed_won", "operator": "EQ", "value": "true" },
    { "propertyName": "closedate", "operator": "BETWEEN", "value": "1767225600000", "highValue": "1774915199000" },
    { "propertyName": "pipeline", "operator": "EQ", "value": "default" } ] } ],
  "properties": ["dealname","amount","closedate","dealstage","pipeline","hubspot_owner_id","createdate","hs_deal_stage_probability"],
  "sorts": [ { "propertyName": "closedate", "direction": "DESCENDING" } ],
  "limit": 200 }
```
  Use `dealstage IN [...]` for stage filters (enumeration values are case-sensitive; `IN` on string properties requires lowercase values). Dates as epoch milliseconds or ISO strings; the doc's own BETWEEN example uses milliseconds.

**`propertiesWithHistory` response shape** (OpenAPI `ValueWithTimestamp`): per property an array, newest first, of `{ "value", "timestamp" (ISO 8601), "sourceType" (e.g. CRM_UI, INTEGRATION, API, IMPORT, WORKFLOWS, ...), "sourceId" (e.g. "userId:6666802" or an app id), "sourceLabel", "updatedByUserId" }`. Example for `dealstage`: https://community.hubspot.com/t5/APIs-Integrations/Get-historical-data-for-deal-stages/m-p/985871 . Reference: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/deals/batch/get-deals . No documented cap on history entries returned.

**Deal properties.** Internal names verified in official docs/examples: `dealname`, `amount`, `closedate`, `pipeline`, `dealstage`, `hubspot_owner_id`, `hs_all_collaborator_owner_ids`, `createdate`, `hs_lastmodifieddate`, `hs_object_id`, `description`, `dealtype`, `hs_is_closed_won`, `hs_pinned_engagement_id`. Seen in real API dumps (not on an official page fetched here): `hs_is_closed`, `hs_is_closed_lost`, `hs_deal_stage_probability`, `hs_forecast_amount`, `hs_projected_amount`, `hs_deal_score` (label "Deal score", the AI predictive score), `hs_tcv`, `hs_mrr`, `hs_v2_date_entered_{stageId}`, `hs_num_of_associated_line_items`, `num_associated_contacts`, `hs_object_source*`. Commonly used but **verify with `GET /crm/properties/2026-03/deals`**: `hs_v2_date_exited_{stageId}`, `hs_v2_latest_time_in_{stageId}`, `hs_v2_cumulative_time_in_{stageId}`, `hs_date_entered_{stageId}` / `hs_time_in_{stageId}` (older variants), `hs_forecast_category`, `hs_forecast_probability`, `hs_next_step`, `hs_priority`, `closed_lost_reason`, `closed_won_reason`, `notes_last_contacted`, `notes_last_updated`, `notes_next_activity_date`, `num_contacted_notes`, `num_notes`, `hs_num_associated_deal_splits`, `hs_created_by_user_id`, `hs_updated_by_user_id`, `hs_analytics_source`. The KB lists the human labels and semantics (stage-calculated properties need Professional/Enterprise): https://knowledge.hubspot.com/properties/hubspots-default-deal-properties

### 2.2 Pipelines and stages
Guide: https://developers.hubspot.com/docs/api-reference/latest/crm/pipelines/guide . Scope: the object's read scope (`crm.objects.deals.read` for deal pipelines).
- `GET /crm/pipelines/2026-03/deals` -> pipelines `{id,label,displayOrder,createdAt,updatedAt,stages[...]}`
- `GET /crm/pipelines/2026-03/deals/{pipelineId}` ; `GET /crm/pipelines/2026-03/deals/{pipelineId}/stages` ; `.../stages/{stageId}`
- Stage: `{id, label, displayOrder, metadata: {probability "0.0"-"1.0", isClosed "true"/"false"}}`. Deal pipelines up to 100 stages.
- Audit trail of pipeline/stage edits: `GET .../{pipelineId}/audit`, `.../stages/{stageId}/audit` (reverse-chronological; `rawObject` JSON snapshot).
- Stage IDs are opaque: old portals use `appointmentscheduled`, `qualifiedtobuy`, `presentationscheduled`, `decisionmakerboughtin`, `contractsent`, `closedwon`, `closedlost` in pipeline `default`; the doc example shows numeric IDs (`11348542`...). Always resolve IDs -> labels via this API; `dealstage` history values are stage IDs.

### 2.3 Owners
Guide: https://developers.hubspot.com/docs/api-reference/latest/crm/owners/guide . Scope: `crm.objects.owners.read`. Read-only.
- `GET /crm/owners/2026-03?limit=100&after=...[&archived=true]` (legacy `/crm/v3/owners`), `GET /crm/owners/2026-03/{ownerId}`; `?idProperty=userId` to look up by user ID (used by the npm server).
- Fields: `id` (owner ID; what `hubspot_owner_id` stores), `email`, `type` (PERSON), `firstName`, `lastName`, `userId` (null when archived), `userIdIncludingInactive`, `createdAt`, `updatedAt`, `archived`, `teams[{id,name,primary}]`.
- `propertiesWithHistory.hubspot_owner_id[].value` and `updatedByUserId` need this map (owner ID vs user ID differ). Teams: `settings.users.teams.read`; users API: `crm.objects.users.read`.

### 2.4 Associations (v4 / 2026-03)
Guide (latest): https://developers.hubspot.com/docs/api-reference/latest/crm/associations/associate-records/guide ; legacy v4: https://developers.hubspot.com/docs/api-reference/legacy/crm/associations/associate-records/guide ; schema/labels: https://developers.hubspot.com/docs/api-reference/latest/crm/associations/associations-schema/guide
- Single: `GET /crm/objects/2026-03/{fromObjectType}/{objectId}/associations/{toObjectType}?limit=500&after=...` (legacy `/crm/v4/objects/deals/{dealId}/associations/calls`). Returns `results[{toObjectId, associationTypes[{category: HUBSPOT_DEFINED|USER_DEFINED, typeId, label|null}]}]` with `paging`.
- Batch: `POST /crm/associations/2026-03/{fromObjectType}/{toObjectType}/batch/read` body `{"inputs":[{"id":"..."}]}`, **up to 1,000 inputs**; response `results[{from:{id}, to:[{toObjectId, associationTypes[...]}]}]` (legacy `/crm/v4/associations/deals/calls/batch/read`).
- Labels between two objects: `GET /crm/associations/2026-03/{from}/{to}/labels` (e.g. contact->deal labels such as "Decision maker", "Champion" if the customer defined them).
- Alternative for small walks: the `associations=contacts,companies,calls,...` query param on `GET /crm/objects/2026-03/deals/{id}` returns associated IDs inline (not on batch read).
- Limits: batch read 1,000 inputs; batch create 2,000; associations API daily cap 500,000 (Pro/Ent), 1,000,000 with API Limit Increase; burst 100/10 s (Free/Starter), 150/10 s (Pro/Ent), 200/10 s with the increase (cannot be raised further).

**HubSpot-defined `associationTypeId` values needed for a deal walk** (official table):

| From -> To | typeId | Reverse | typeId |
|---|---|---|---|
| Deal -> contact | 3 | Contact -> deal | 4 |
| Deal -> company (unlabeled) | 341 | Company -> deal | 342 |
| Deal -> primary company | 5 | Primary company -> deal | 6 |
| Deal -> call | 205 | Call -> deal | 206 |
| Deal -> email | 209 | Email -> deal | 210 |
| Deal -> meeting | 211 | Meeting -> deal | 212 |
| Deal -> note | 213 | Note -> deal | 214 |
| Deal -> task | 215 | Task -> deal | 216 |
| Deal -> communication (SMS/WhatsApp/LinkedIn) | 86 | Communication -> deal | 85 |
| Deal -> postal mail | 458 | Postal mail -> deal | 457 |
| Deal -> ticket | 27 | Ticket -> deal | 28 |
| Deal -> line item | 19 | Line item -> deal | 20 |
| Deal -> quote | 63 | Quote -> deal | 64 |
| Contact -> call / email / meeting / note / task | 193 / 197 / 199 / 201 / 203 | Call/Email/Meeting/Note/Task -> contact | 194 / 198 / 200 / 202 / 204 |
| Company -> call / email / meeting / note / task | 181 / 185 / 187 / 189 / 191 | ... -> company | 182 / 186 / 188 / 190 / 192 |
| Contact -> company (unlabeled / primary) | 279 / 1 | Company -> contact (all labels / primary) | 280 / 2 |

### 2.5 Engagement objects: endpoints
Each of calls, emails, meetings, notes, tasks is a standard CRM object with the same endpoint family (guides: calls https://developers.hubspot.com/docs/api-reference/latest/crm/activities/calls/guide ; emails https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/email (legacy path; latest under `/latest/crm/activities/emails/guide`); meetings https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/meetings ; notes https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/notes ):
- `GET /crm/objects/2026-03/{calls|emails|meetings|notes|tasks}/{id}?properties=...&associations=deals,contacts`
- `GET /crm/objects/2026-03/{type}?limit=100&properties=...&after=...`
- `POST /crm/objects/2026-03/{type}/batch/read` `{"properties":[...],"inputs":[{"id":"..."}]}` (<= 100)
- `POST /crm/objects/2026-03/{type}/search` (section 2.6)
- `PUT /crm/objects/2026-03/{type}/{id}/associations/{toObjectType}/{toObjectId}/{associationTypeId}` to associate on creation of seed data.
- Legacy alternative returning body + associations in one call: `GET /engagements/v1/engagements/{id}` (used by the npm server) [legacy API; still functional].
- Scopes: the guides list `crm.objects.contacts.read`/`.write`; emails additionally `sales-email-read` "required to get the content of email engagements" (section 4.2).

### 2.6 Engagement properties (verified against the guides unless marked)

**Calls (`0-48`)** — https://developers.hubspot.com/docs/api-reference/latest/crm/activities/calls/guide

| Property | Meaning |
|---|---|
| `hs_timestamp` | Required. Call time; Unix ms or UTC ISO. Determines timeline position. |
| `hs_call_title` | Title. |
| `hs_call_body` | Description/notes typed by the rep (not the transcript). |
| `hs_call_duration` | Duration in milliseconds. |
| `hs_call_direction` | `INBOUND` / `OUTBOUND`. |
| `hs_call_disposition` | Outcome, stored as a GUID. Defaults: Busy `9d9162e7-6cf3-4944-bf63-4dff82258764`, Connected `f240bbac-87c9-4f6e-bf70-924b57d47db7`, Left live message `a4c4c377-d246-4b32-a13b-75a56a4cd0ff`, Left voicemail `b2cf5968-551e-4856-9783-52b3da59a7d0`, No answer `73a0d17f-1163-4015-bdd5-ec830791da20`, Wrong number `17b47fee-58de-441e-a44c-c6300d46f273` (GUIDs from the calls guide; confirm per portal via `GET /calling/v1/dispositions`) [UNVERIFIED this session]. |
| `hs_call_status` | `BUSY, CALLING_CRM_USER, CANCELED, COMPLETED, CONNECTING, FAILED, IN_PROGRESS, NO_ANSWER, QUEUED, RINGING`. |
| `hs_call_recording_url` | HTTPS URL of the recording (.mp3/.wav playable on records). |
| `hs_call_from_number` / `hs_call_to_number` | Phone numbers. |
| `hs_call_source` | Must be `INTEGRATIONS_PLATFORM` when set; required for the integrator recording/transcription pipeline. |
| `hs_call_callee_object_id` / `hs_call_callee_object_type` | Associated record for the callee/dialer. |
| `hubspot_owner_id` | Owner (shown as creator). |
| `hs_activity_type` | Call type per account settings. |
| `hs_attachment_ids` | Semicolon-separated file IDs. |
| `hs_call_has_voicemail` | true/false/null (inbound calling). |
| `hs_call_external_id`, `hs_call_external_account_id`, `hs_call_app_id` | Required on integrator-logged calls that use the Recordings & Transcripts API. |
| `hs_body_preview`, `hs_body_preview_html` | Generic engagement preview (searchable/not filterable respectively). |
| `hs_call_summary` | AI (Notetaker/CI) conversation summary — named in the Notetaker recap API doc. |
| `hs_call_has_transcript`, `hs_call_transcription_id` | Exist on the object (community-confirmed via properties API) but undocumented; `hs_call_transcription_id` reported null in most portals. [community] |
| `hs_createdate`, `hs_lastmodifieddate`, `hs_object_id` | System. |

**Emails (`0-49`)** — https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/email

| Property | Meaning |
|---|---|
| `hs_timestamp` | Required. |
| `hs_email_direction` | `EMAIL` (sent from CRM), `INCOMING_EMAIL`, `FORWARDED_EMAIL`. Required on create. |
| `hs_email_subject` | Subject. |
| `hs_email_text` | Plain-text body. |
| `hs_email_html` | HTML body (not filterable in search). |
| `hs_email_status` | `BOUNCED, FAILED, SCHEDULED, SENDING, SENT`. |
| `hs_email_headers` | JSON-escaped string with from/to/cc/bcc `{email, firstName, lastName}`. |
| `hs_email_from_email`, `hs_email_from_firstname`, `hs_email_from_lastname`, `hs_email_to_email`, `hs_email_to_firstname`, `hs_email_to_lastname` | Read-only, derived from headers. |
| `hubspot_owner_id`, `hs_attachment_ids` | As above. |
| `hs_body_preview` | Not filterable in search for emails. |

Reading bodies requires the `sales-email-read` scope.

**Meetings (`0-47`)** — https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/meetings

| Property | Meaning |
|---|---|
| `hs_timestamp` | Required; when the meeting occurred (should match start time). |
| `hs_meeting_title` | Title. |
| `hs_meeting_body` | Description (sent to attendees). |
| `hs_internal_meeting_notes` | Internal notes, not shared with attendees. |
| `hs_meeting_external_url` | Calendar event URL (Google/Outlook). |
| `hs_meeting_location` | Address / room / video link / phone. |
| `hs_meeting_start_time`, `hs_meeting_end_time` | Times. |
| `hs_meeting_outcome` | `SCHEDULED, COMPLETED, RESCHEDULED, NO_SHOW, CANCELED`. |
| `hs_activity_type`, `hubspot_owner_id`, `hs_attachment_ids` | As above. |
| Recording/transcript/summary fields on meetings | Not documented. Relevant because from 2026-07-31 (one KB page) / 2026-08-31 (another) Notetaker- and Zoom/Meet/Teams-synced recordings create **only a meeting record**, no companion call record. [UNVERIFIED property names; date discrepancy between KB pages] |

**Notes (`0-46`)** — https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/notes

| Property | Meaning |
|---|---|
| `hs_timestamp` | Required. |
| `hs_note_body` | Text, max 65,536 characters. |
| `hubspot_owner_id`, `hs_attachment_ids` | As above. |

**Tasks (`0-27`)**: `hs_timestamp` (required), `hs_task_subject`, `hs_task_body`, `hs_task_status`, `hs_task_priority`, `hs_task_type`, `hubspot_owner_id` (subject/body verified via the search defaults table; others commonly used).

**Search behaviour for engagements** (https://developers.hubspot.com/docs/api-reference/latest/crm/search-the-crm): default returned properties are only `hs_createdate, hs_lastmodifieddate, hs_object_id` (always pass `properties`); free-text `query` searches `hs_call_title`+`hs_body_preview` (calls), `hs_email_subject` (emails), `hs_meeting_title`+`hs_meeting_body` (meetings), `hs_note_body` (notes), `hs_task_body`+`hs_task_subject` (tasks); filtering on `hs_body_preview_html` is unsupported for all engagements, and on `hs_email_html`/`hs_body_preview` for emails. Association filter: pseudo-property `associations.{objectType}` (doc example `associations.contact EQ 123`; use `associations.deal` for deal-scoped engagement queries [INFERRED by analogy]).

**Search grammar and limits** (same page): `POST /crm/objects/2026-03/{object}/search`; body `filterGroups[].filters[]{propertyName, operator, value|highValue|values}`, `query`, `properties[]`, `sorts[{propertyName,direction ASCENDING|DESCENDING}]` (one sort only), `limit` (default 10, max 200), `after` (integer cursor from `paging.next.after`). Operators: `LT, LTE, GT, GTE, EQ, NEQ, BETWEEN (value+highValue), IN/NOT_IN (values[])`, `HAS_PROPERTY, NOT_HAS_PROPERTY, CONTAINS_TOKEN, NOT_CONTAINS_TOKEN` (wildcards `*`). Max 5 filterGroups x 6 filters, 18 total; 3,000-char body; **10,000 total results per query** (400 beyond); **5 requests/second per account** (shared by every integration and user in the portal); archived records excluded; indexing lag of "a few moments"; search responses carry no rate-limit headers.

### 2.7 A complete walk (request budget)
1. Deals: search (closed-won in window) -> `dealstage`, `closedate`, `amount`, `hubspot_owner_id`, `pipeline` — 1 request per 200 deals.
2. History: batch read with `propertiesWithHistory: ["dealstage","closedate","amount","hubspot_owner_id"]` — 1 request per 50 deals.
3. Stage labels/probabilities: 1 request (`/crm/pipelines/2026-03/deals`). Owners: 1-2 requests.
4. Associations: 6 batch reads (contacts, companies, calls, emails, meetings, notes) per 1,000 deals.
5. Engagement bodies: batch reads of <= 100 IDs per type; ask only for the properties you need (`hs_email_html` can be large).
6. Contacts/companies: batch read for names, titles, `jobtitle`, `hs_buying_role` (contact buying-role property [UNVERIFIED name]) and contact->deal labels (`GET /crm/associations/2026-03/contacts/deals/labels`).
For 500 deals with ~40 engagements each: ~3 + 10 + 3 + 6 + 200 = ~220 requests, comfortably inside the 10-second burst budget when throttled to ~15 req/s, and far under daily caps.

### 2.8 Rate limits and headers
Source: https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines ; https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview ; https://developers.hubspot.com/changelog/increasing-our-api-limits

| Auth type | Per 10 s | Per day (shared across all private apps in the account) |
|---|---|---|
| Private app, Free/Starter | 100 per app | 250,000 |
| Private app, Professional | 190 per app | 625,000 (changelog text says 650,000; the tables say 625,000) |
| Private app, Enterprise | 190 per app | 1,000,000 |
| With API Limit Increase (max 2 purchases) | 250 per app (usage-guidelines page) / 200 (legacy private-apps page) [docs disagree] | +1,000,000 per purchase |
| Public OAuth app (marketplace) | 110 per installed account | n/a (excludes search) |
| CRM Search | 5 requests/second per account | — |
| Associations API | 100/10 s (Free/Starter), 150/10 s (Pro/Ent), 200/10 s with increase | 500,000 Pro/Ent; 1,000,000 with increase |

Headers on every non-search response: `X-HubSpot-RateLimit-Daily`, `-Daily-Remaining` (not on OAuth-authenticated requests), `X-HubSpot-RateLimit-Interval-Milliseconds`, `X-HubSpot-RateLimit-Max`, `X-HubSpot-RateLimit-Remaining`; `-Secondly*` headers present but deprecated/not enforced. 429 on breach; `Retry-After` value is in milliseconds (https://developers.hubspot.com/docs/api-reference/error-handling). Daily usage endpoint: `GET /account-info/2026-03/api-usage/daily/private-apps` (legacy `/account-info/v3/...`).

---

## 3. Call recordings and transcripts

### 3.1 Conversation Intelligence (CI): who gets what
KB (updated 2026-07-20): https://knowledge.hubspot.com/calling/review-call-recordings-and-transcripts
- Recordings from HubSpot Calling, the Zoom/Google Meet integrations, or integrated third-party calling providers can be reviewed on all plans.
- **Transcription and analysis require a Sales Hub or Service Hub Professional or Enterprise subscription, and only calls made by users with an assigned Sales/Service seat are automatically transcribed.** AI call summary (purpose, key points, decisions, sentiment, next steps): Pro/Ent. Tracked terms: Enterprise only. Conversational enrichment of contact/company records from transcripts: Enterprise (beta). Transcript inline comments/sharing: Pro/Ent.
- Zoom sync needs a Zoom Business/Enterprise account with cloud recording (and "audio transcripts" enabled) plus "Sync data from recordings and transcripts" in the Zoom integration; Google Meet Business/Enterprise similar; Microsoft Teams also supported via meeting sync (https://knowledge.hubspot.com/calling/sync-conversation-transcripts-into-hubspot , https://knowledge.hubspot.com/meetings-tool/configure-conversation-recording-and-transcription-options).
- Notetaker (HubSpot's meeting bot; Pro/Ent + seat): joins Google Meet/Teams/Zoom, max 40 meetings/user/day, 3-hour cap, recordings kept 2 years, sub-processor Hyperdoc Inc.; produces summary, CRM property update suggestions ("smart deal progression"), action items, follow-up drafts (https://knowledge.hubspot.com/meetings-tool/record-and-take-notes-in-meetings-with-meeting-notetaker).
- Toggling "Transcription and analysis" on retro-transcribes only the past 7 days. Integrations that send finished transcripts can populate HubSpot even with the toggle off.
- Record-type change: "starting July 31, 2026 ... HubSpot will only create a meeting record" for Notetaker/video-conferencing recordings (previously a call record + a meeting record). Another KB page says August 31, 2026. [date discrepancy]

### 3.2 Recordings via API
- Native/CI recordings and integrator recordings surface as `hs_call_recording_url` on the call object (HTTPS .mp3/.wav). Community reports downloading the file with a plain GET on that URL (n8n example) and transcribing it with an LLM/ASR (https://community.hubspot.com/t/retrieving-call-transcripts/76772). Whether the URL requires a HubSpot session or is a signed/public link varies by source [UNVERIFIED].
- Integrator side ("Recordings & Transcripts API", https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/calling-extensions/recordings-and-transcriptions): register an authenticated-URL endpoint with `POST /crm/extensions/calling/2026-03/{appId}/settings/recording` (`urlToRetrieveAuthedRecording` containing `%s`), log the call with `hs_call_external_id`, `hs_call_external_account_id`, `hs_call_app_id`, `hs_call_source=INTEGRATIONS_PLATFORM`, associate it, then `POST /crm/extensions/calling/2026-03/recordings/ready {"engagementId"}` so HubSpot transcribes it. Changelog 2023-11-15: the `hs_call_recording_url` route for integrator transcription sunset on 2024-09-30 (https://developers.hubspot.com/changelog/new-recording-transcripts-api-replaces-hs_call_recording_url-for-call-engagements).

### 3.3 Transcripts via API
- Endpoints (https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/calling-extensions/third-party-transcripts ; OpenAPI https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/transcriptions/create-transcript and https://developers.hubspot.com/docs/api-reference/legacy/crm/extensions/transcriptions/get-transcript):
  - `POST /crm/extensions/calling/2026-03/transcripts` `{engagementId, transcriptCreateUtterances[{speaker{id,name,email?}, text, languageCode?, startTimeMillis, endTimeMillis}]}` — scope `crm.extensions_calling_transcripts.write`
  - `GET /crm/extensions/calling/2026-03/transcripts/{transcriptId}` (legacy `GET /crm/v3/extensions/calling/transcripts/{transcriptId}`) — scope `crm.extensions_calling_transcripts.read`; response `{id, engagementId, transcriptSource: HUBSPOT_GENERATED | INTEGRATOR_GENERATED, createdAt, updatedAt, transcriptUtterances[{id, speaker{id,name,email}, text, languageCode, startTimeMillis, endTimeMillis}]}`
  - `DELETE .../transcripts/{transcriptId}`
- Auth: "Calls to the transcription API must be authenticated with OAuth, and your public app must include the following scopes". The OpenAPI security block lists only the `oauth2` scheme, whereas ordinary CRM endpoints list both `oauth2` and `private_apps`. **[INFERRED] Private-app tokens cannot call the transcripts API**; the `crm.extensions_calling_transcripts.*` scopes are absent from the published scope table.
- No endpoint lists transcripts by call. Community threads through Dec 2025 report `hs_call_has_transcript = true` with `hs_call_transcription_id = null`, and staff pointing to `hs_call_recording_url` + self-transcription (https://community.hubspot.com/t/retreiving-tanscript/143803 ; https://community.hubspot.com/t/accessing-transcript-url-via-hubspot-api/102411). A 2023 tip (`GET /crm/v3/objects/notes/{hs_call_transcription_id}`) only works when that ID is populated.
- AI summary / action items: **Notetaker conversations recap API (beta)** `GET /notetaker/2026-09-beta/conversation/recap/{objectTypeId}/{objectId}` (`0-48` calls, `0-47` meetings) -> `{summary:{value,status,errorMessage}, actionItems:{items[{title,assignee}],status,errorMessage}}`, statuses `SUCCEEDED | NOT_FOUND | IN_PROGRESS | FAILED`; accounts without Notetaker get empty results, not errors. Summary text is "stored in the `hs_call_summary` CRM property" (so `GET /crm/objects/2026-03/calls/{id}?properties=hs_call_summary` should return it [INFERRED]). Scopes for this API are not stated [UNVERIFIED]. https://developers.hubspot.com/docs/api-reference/2026-09-beta/meetings/notetaker/guide

### 3.4 Third-party recorders (Zoom/Gong/Fireflies)
- Zoom/Google Meet/Teams: synced by HubSpot's own integrations; recordings appear on the timeline and, with a Pro/Ent seat, CI transcribes them (section 3.1). They are then HubSpot-generated transcripts subject to the same API gap.
- Gong, Fireflies, tl;dv, etc.: marketplace apps that write their own activities (typically a note or call with summary text, sometimes a transcript link) [UNVERIFIED per vendor]. MEDDICC.com's integration matrix is representative: "AI call summaries: sync to CRM when applied; Call recordings: do not sync" (https://meddicc.com/knowledge/supported-crm-integrations).

### 3.5 What a Sales Hub Professional account realistically yields via a private app
| Artifact | Available? |
|---|---|
| Call metadata (title, direction, duration, disposition, status, timestamp, owner) | Yes |
| Rep-typed call notes `hs_call_body`, meeting `hs_meeting_body` / `hs_internal_meeting_notes`, `hs_note_body`, email `hs_email_text/html` | Yes (emails need `sales-email-read`) |
| Recording URL `hs_call_recording_url` | Yes for HubSpot Calling/CI-integrated sources; download behaviour unverified |
| Verbatim transcript | Not reliably (no lookup path; transcripts API is public-app OAuth only) |
| AI call summary `hs_call_summary` + action items | Likely, via property read and the 2026-09-beta recap API, once Notetaker/CI has processed the call |
| Meeting-object recordings/transcripts after the 2026 record-type change | Property names undocumented |
| Fallback | Download recording -> Whisper/Deepgram/etc. (community-validated) |

---

## 4. Scopes for read-only access

Official scope table (new platform): https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/scopes (legacy table: https://developers.hubspot.com/docs/apps/legacy-apps/authentication/scopes).

### 4.1 Recommended private-app scope set for this plugin (read-only)
| Scope (exact) | Official description / why |
|---|---|
| `crm.objects.deals.read` | "View properties and other details about deals." Deals, deal search, deal pipelines. |
| `crm.objects.contacts.read` | "View properties and other details about contacts." Also the scope the engagement guides list for calls/meetings/notes/emails. |
| `crm.objects.companies.read` | "View properties and other details about companies." |
| `crm.objects.owners.read` | "View details about users assigned to a CRM record." Owners API. |
| `sales-email-read` | "Grants access to read and manage one-to-one email engagements" — required to get the content of email engagements (legacy table wording). |
| `crm.schemas.deals.read` (+ `crm.schemas.contacts.read`, `crm.schemas.companies.read`) | "View details about property settings for deals" — needed to list property definitions (MEDDPICC custom fields, stage enums). |
| `crm.objects.users.read`, `settings.users.teams.read` | Users and teams (optional). |
| `crm.objects.line_items.read`, `crm.objects.quotes.read` | Only if you read commercial detail. |
| `crm.lists.read` | Only if you read segments. |
| `crm.objects.custom.read` | Enterprise only; custom objects. |
| `oauth` | Added by default. |
Not needed for reads: `crm.import`, `crm.export`, `tickets` (unless tickets), `automation`, `timeline`, `content`.

### 4.2 The engagement-scope confusion (important for error handling)
- The OpenAPI specs for activity endpoints list `crm.objects.calls.read`, `crm.objects.emails.read`, `crm.objects.meetings.read`, `crm.objects.notes.read`, `crm.objects.tasks.read` (e.g. https://developers.hubspot.com/docs/api-reference/latest/crm/activities/calls/get-calls), and an Aug-2026 403 body shows `"requiredGranularScopes": ["crm.schemas.emails.read","crm.objects.emails.read","sales-email-read"]`.
- None of those appear in the published scope table, and community threads (Apr 2025, Jul 2025, Nov 2025, Aug 2026) report they are not selectable for private or public apps. HubSpot staff resolved the Aug-2026 case with `crm.objects.contacts.read`, `crm.objects.contacts.write`, `sales-email-read`, reading `GET /crm/objects/2026-03/emails?limit=100` successfully (https://community.hubspot.com/t/crm-emails-api-crm-objects-emails-read-crm-schemas-emails-read-not-available-in-oauth-scope-pick/155041 ; https://community.hubspot.com/t/cant-get-engagments/129828 ; https://community.hubspot.com/t/crm-objects-notes-read-scope-not-visible-available-to-add-to-app-oauth-scope/136122).
- Sensitive-data scopes: the table lists `crm.objects.contacts.sensitive.read` etc. (Enterprise); OpenAPI shows `.v2`-suffixed variants (`crm.objects.contacts.sensitive.read.v2`) [naming in flux].
- Treat `MISSING_SCOPES` responses as authoritative: parse `errors[].context.requiredGranularScopes` and surface them to the user.

### 4.3 Private apps: mechanics and the 2026 sunset
Source: https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview ; https://developers.hubspot.com/changelog/legacy-private-app-creation-sunset
- Create: Development > Legacy apps > Create legacy app > Private (Super Admin only). Up to 20 per account. Token shown once; `Authorization: Bearer pat-na1-...` (EU portals `pat-eu1-...`; prefix per third-party sources).
- Token info: `POST /oauth/v2/private-apps/get/access-token-info` `{ "tokenKey": "<token>" }` -> `{userId, hubId, appId, scopes[]}` (this is what the npm server's `hubspot-get-user-details` calls).
- Tokens do not expire; rotate every 6 months (Rotate and expire now / in 7 days). Scopes shrink automatically if the subscription downgrades. If the creating user is removed, some calls fail with `USER_DOES_NOT_HAVE_PERMISSIONS` until rotated.
- **Sunset:** "Starting in late September 2026, the option to create new legacy private apps will be removed from the HubSpot account UI" — 2026-09-28 for accounts created on/after that date, 2026-10-26 for existing accounts. Existing private apps keep working. Replacement: **Service Keys** (Settings > Integrations > Service Keys; Developer Platform Projects 2026.09+): scoped access, activity logging, 7-day rotation grace, admin-only key visibility. Whether Service Keys use the same bearer header and scope names is not stated [UNVERIFIED]. Plugin docs should describe both.

---

## 5. Developer test accounts and sandboxes

### 5.1 Developer test accounts
Source: https://developers.hubspot.com/docs/getting-started/account-types ; https://developers.hubspot.com/docs/developer-tooling/local-development/configurable-test-accounts ; https://developers.hubspot.com/blog/how-to-safely-experiment-with-ai-in-hubspot-before-you-touch-real-data
- Free; **up to 10 per standard HubSpot account**; since 2026-03-09 legacy developer accounts were migrated into standard accounts, so any HubSpot account can create them: Development > Testing > Test Accounts > Create developer test account. Default = 90-day trials of **Enterprise** features for all Hubs; tick "Customize my test account" to pick a tier per Hub (one tier per Hub) — e.g. simulate Sales Hub Professional.
- CLI: `hs test-account create` (interactive or `--config-path ./x.json`), `hs test-account create-config`, `hs test-account import-data --account <id> --file-path <import.json>` (CSV files + a JSON config in the CRM imports API format; custom properties must exist first). CLI reference: https://developers.hubspot.com/docs/developer-tooling/local-development/hubspot-cli/reference
- Expiry: "expire after 90 days if no API calls are made"; renew from the Test accounts page ("Renew trials") or by any API call; API renewal must be within 30 days of expiry using an OAuth token from an app in the same developer account (wording predates the March-2026 migration).
- Limits: marketing email only to users added to the test account; Content Hub 25 website pages, 25 landing pages, 1 blog/100 posts; workflows 100,000 enrollments/day; "Test accounts cannot sync data with other accounts".
- Sample data: none of substance — described as a "blank slate"; a 2021 thread says a new test account "only comes with two records and very little activity data" (https://community.hubspot.com/t/best-way-to-populate-test-account-with-sample-data-for-integration-development/47982). HubSpot provides sample import CSV/XLSX files for contacts, companies, deals, tickets (KB "Sample import files"); Mockaroo is the community's generator of choice.
- Private apps work in test accounts (they are standard accounts); the same 2026-09/10 sunset applies to creating new ones.

### 5.2 Seeding a demo dataset via API (all supported)
Standard write endpoints are available, so a seed script can create: contacts/companies/deals (`POST /crm/objects/2026-03/{type}` or `batch/create`, <= 100 per batch), then engagements with associations inline:

```json
POST /crm/objects/2026-03/calls
{ "properties": { "hs_timestamp": "2026-06-03T14:05:00.000Z", "hs_call_title": "Discovery call",
    "hs_call_body": "Champion confirmed budget owner is CFO ...", "hs_call_direction": "OUTBOUND",
    "hs_call_duration": "1860000", "hs_call_status": "COMPLETED",
    "hs_call_disposition": "f240bbac-87c9-4f6e-bf70-924b57d47db7", "hubspot_owner_id": "41629779",
    "hs_call_recording_url": "https://example.com/rec/123.mp3" },
  "associations": [ { "to": { "id": 7891023 }, "types": [ { "associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 206 } ] },
                    { "to": { "id": 100451 },  "types": [ { "associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 194 } ] } ] }
```
Emails need `hs_timestamp` + `hs_email_direction` (+ `hs_email_headers` JSON string for sender/recipient); meetings need `hs_timestamp` (+ `hs_meeting_start_time/end_time`, `hs_meeting_outcome`); notes need `hs_timestamp`. Back-dated `hs_timestamp` values are honoured on the timeline. Deal stage history can be manufactured by creating the deal in an early stage and PATCHing `dealstage` in sequence (history timestamps will be "now", not back-dated; `propertiesWithHistory` cannot be back-filled). Transcripts cannot be seeded through a private app (section 3.3); put transcript-like text in `hs_call_body` or a note instead. Scopes for seeding: the corresponding `.write` scopes plus `sales-email-read` for emails.

### 5.3 Calling and CI in test accounts
- HubSpot staff (Oct 2024): "App test accounts have access to using the Calling SDK demo app, but not full calling functionality" (https://community.hubspot.com/t/calling-settings-endpoint/118871/2). HubSpot support (2023): "the calling feature is not available for any sandbox accounts at this time" (https://community.hubspot.com/t5/Calling/Account-is-Restricted-Already/m-p/740859). No official doc statement found [community-sourced]. Consequence: CI transcription cannot be exercised in a test account; use recording URLs + `hs_call_body` in demos.

### 5.4 Sandboxes (Enterprise only)
Source: https://knowledge.hubspot.com/account-management/deploy-sandbox-changes-to-production ; account-types page.
- Standard sandbox: copies production structure (pipelines, properties, workflows, supported assets); optional copy of the 5,000 most recently updated contacts with up to 100 associated deals/companies/tickets each; record IDs differ from production; 100,000 workflow enrollments/day; integrations not auto-connected; up to 200,000 records importable per object type later. **Legacy standard sandboxes unsupported since 2026-04-30.**
- Development sandboxes: CLI-managed (`hs sandbox ...`), Enterprise.
- CMS sandbox: free, unrelated to CRM data.

---

## 6. MEDDPICC / MEDDIC in HubSpot

### 6.1 Native support: none, but the primitives are there
- No MEDDPICC object or template ships with HubSpot. Teams model it as a **deal property group** with a dropdown (score/status) + multi-line text (evidence/notes) per element, optional checkboxes (`..._identified`), a calculation property for the total, **required properties at stage transitions** (Settings > Objects > Deals > Pipelines) as stage gates, **playbooks** (Sales Hub Pro/Ent) whose answers write those properties, and **contact->deal association labels** ("Economic Buyer", "Champion") for the buying committee. Guides: https://www.superwork.co/blog/meddpicc-hubspot (property names like `meddpicc_metrics_score`, `meddpicc_champion_identified`, `meddpicc_score`, `meddpicc_health_percentage`) and https://nimitai.com/blog/meddpicc-template (`meddpicc_metrics` 0-3 + `..._evidence` + `meddpicc_total_score`).
- For the plugin: these are ordinary deal properties — discover with `GET /crm/properties/2026-03/deals` (filter on `groupName`, e.g. `meddpicc`), read with `properties=`, and get change history with `propertiesWithHistory=` (who/when each element was scored). Labels: `GET /crm/associations/2026-03/contacts/deals/labels`.

### 6.2 MEDDICC.com ("Deals" / mOS)
Source: https://meddicc.com/knowledge/setting-up-your-crm-integration ; https://meddicc.com/knowledge/supported-crm-integrations ; https://meddicc.com/knowledge/crm-integration-faq
- Syncs through Merge (20+ CRMs incl. HubSpot). HubSpot auth = a **private app** (Development > Legacy Apps > Private) whose token + Company ID are entered in Merge. Required scopes: `crm.objects.users.read/write`, `crm.objects.contacts.read/write`, `crm.objects.companies.read/write`, `crm.objects.deals.read/write`, `crm.objects.owners.read`, `crm.schemas.deals.read/write`, `sales-email-read`.
- Field convention on the deal object (create before connecting): `metric_status`/`metric_notes`, `economic_buyer_status`/`_notes`, `decision_criteria_*`, `decision_process_*`, `paper_process_*`, `implicate_pain_*`, `champion_*`, `competition_*`; status fields are dropdowns with internal values exactly `strong`/`medium`/`low` (lowercase); notes are multi-line text. Recommended: a dedicated MEDDPICC tab/section on the deal record.
- Sync: deal name, stage, close date, MEDDPICC notes + qualification strength, linked contacts both ways; AI call summaries to CRM "when applied"; call recordings never. Imports deals updated in the last 2 years; ~1 min Deals->CRM, ~15 min CRM->Deals.

### 6.3 "Meddicc Score" marketplace app (meddiccscore.com)
Source: https://ecosystem.hubspot.com/marketplace/listing/meddicc-score ; https://meddiccscore.com/hubspot/ ; https://meddiccscore.com/blog/hubspot-workflow-prevent-unqualified-meddicc-deals/ ; https://meddiccscore.com/blog/setup-guide-legacy/
- Reads the **last 100 deal engagements** (emails, meetings, calls, notes, tasks) and uses an LLM (OpenAI/Google/Anthropic selectable) to pre-fill the framework; supports MEDDICC, MEDDPICC, BANT, GPCTBA/C&I, SPICED, FAINT, CHAMP, SCOTSMAN, ANUM, custom.
- Writes a 0-100 score to the deal property `score_meddicc` (number; must be created manually if the app cannot) and, with "Sync MeddiccScore to HubSpot properties" on, a fixed set: Meddicc Score, MEDDICC Missing Categories, Bad/Medium/Good Categories, Completion Percent, Qualification Status, Next Action. Ships custom workflow actions; org charts / competitor charts; CSV/PDF reports. ~200+ installs, 4.6/5 (per superwork, Nov 2025). Requires its own subscription.

### 6.4 HubSpot's own scoring and AI summaries
- **Predictive "Deal score"** (KB https://knowledge.hubspot.com/records/use-deal-scores): AI probability 0-100 of winning; inputs: amount, close date, create date, time in stage, activity recency/counts (calls, emails, meetings), overdue tasks, scheduled meetings, contact email engagement, owner changes, next-step updates; initial score ~36-48 h after creation; refreshed within 6 h (fast triggers) or 48 h (slow triggers) when it moves >= 3 points; frozen once closed; reopened deals get no score. Score details on hover need Sales Hub Pro/Ent. Property label "Deal score"; internal name observed as `hs_deal_score` in API dumps [UNVERIFIED on an official page]. History and "key factors" are UI-only (Deal score card); no API for the factor breakdown found.
- **Manual deal/company scoring** via the Lead Scoring app (Sales Hub Pro/Ent; legacy manual deal-score property sunset 2025-08-31) — produces a custom score property (https://community.hubspot.com/t/create-a-custom-deal-score/134400).
- **Breeze**: record summaries (deal: name, create date, company, owner, pipeline, stage, amount, close date, type, last activity, forecast category, next step + prose summary of notes/activities) are UI-only (https://knowledge.hubspot.com/records/summarize-records); Deal Insights / at-risk flags and Breeze Assistant Q&A are UI features (https://www.hubspot.com/products/artificial-intelligence/use-cases/sales-identify-at-risk-deals); the API-accessible AI artefacts are `hs_call_summary` and the Notetaker recap API (section 3.3), plus Notetaker's CRM property-update suggestions once a user approves them (they then appear as normal property changes with history).

---

## 7. Open items and things not verified
1. Whether `https://mcp.hubspot.com/anthropic` works in Claude Code without pre-registered client credentials (no DCR advertised; `client_secret_post` required by metadata). Test with `claude mcp add --transport http hubspot https://mcp.hubspot.com/anthropic` then `/mcp`; fall back to an MCP Auth App + `--client-id/--client-secret`.
2. Exact current tool names of the remote server beyond `get_user_details`, and whether the "schema search" / "associations" tools seen in a doc mirror are live. Run `get_user_details` / list tools after connecting.
3. Whether the local npm server's object tools accept `calls`/`emails`/`notes` at runtime (source says yes; not executed).
4. Whether `hs_call_recording_url` is fetchable with a plain HTTPS GET (community says yes for some sources).
5. Whether `hs_call_summary` is readable through the CRM calls endpoint with a private app, and which scopes the Notetaker recap beta requires.
6. Whether private-app tokens are rejected by `/crm/extensions/calling/2026-03/transcripts/{id}` (inferred from docs + OpenAPI security schemes).
7. Meeting-object recording/transcript property names after the July/August 2026 record-type change.
8. Internal names for stage-calculated and scoring properties (`hs_v2_*`, `hs_deal_score`); confirm via `GET /crm/properties/2026-03/deals` in the target portal.
9. Service Keys: header format and scope vocabulary (docs not yet published in the sources reached).
10. EU base URL `api-eu1.hubapi.com`.
11. Default `hs_call_disposition` GUIDs (widely reproduced; confirm with `GET /calling/v1/dispositions`).

---

## 8. Source index
- Remote MCP server doc: https://developers.hubspot.com/docs/apps/developer-platform/build-apps/integrate-with-the-remote-hubspot-mcp-server
- Remote MCP GA changelog (2026-04-13): https://developers.hubspot.com/changelog/remote-hubspot-mcp-server-is-now-generally-available
- MCP overview: https://developers.hubspot.com/ai-tools/mcp ; Developer MCP setup: https://developers.hubspot.com/docs/developer-tooling/local-development/developer-mcp/setup
- Claude connector KB: https://knowledge.hubspot.com/integrations/set-up-and-use-the-hubspot-connector-for-claude
- npm package: https://www.npmjs.com/package/@hubspot/mcp-server (tarball https://registry.npmjs.org/@hubspot/mcp-server/-/mcp-server-0.4.0.tgz)
- Claude Code MCP docs: https://code.claude.com/docs/en/mcp ; plugins reference: https://code.claude.com/docs/en/plugins-reference
- API versioning: https://developers.hubspot.com/docs/developer-tooling/platform/versioning ; https://developers.hubspot.com/docs/api-reference/latest/overview
- Deals guide: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/deals/guide ; batch read spec: https://developers.hubspot.com/docs/api-reference/latest/crm/objects/deals/batch/get-deals ; default deal properties KB: https://knowledge.hubspot.com/properties/hubspots-default-deal-properties
- Using object APIs: https://developers.hubspot.com/docs/api-reference/latest/crm/using-object-apis
- Search: https://developers.hubspot.com/docs/api-reference/latest/crm/search-the-crm ; limit changelog: https://developers.hubspot.com/changelog/increasing-our-api-limits
- Pipelines: https://developers.hubspot.com/docs/api-reference/latest/crm/pipelines/guide
- Owners: https://developers.hubspot.com/docs/api-reference/latest/crm/owners/guide
- Associations: https://developers.hubspot.com/docs/api-reference/latest/crm/associations/associate-records/guide ; https://developers.hubspot.com/docs/api-reference/legacy/crm/associations/associate-records/guide ; https://developers.hubspot.com/docs/api-reference/latest/crm/associations/associations-schema/guide
- Calls: https://developers.hubspot.com/docs/api-reference/latest/crm/activities/calls/guide ; Emails: https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/email ; Meetings: https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/meetings ; Notes: https://developers.hubspot.com/docs/api-reference/legacy/crm/engagements/notes
- Recordings & transcripts: https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/calling-extensions/recordings-and-transcriptions ; third-party transcripts: https://developers.hubspot.com/docs/api-reference/latest/crm/extensions/calling-extensions/third-party-transcripts ; get transcript spec: https://developers.hubspot.com/docs/api-reference/legacy/crm/extensions/transcriptions/get-transcript ; Notetaker recap API: https://developers.hubspot.com/docs/api-reference/2026-09-beta/meetings/notetaker/guide ; 2023 changelog: https://developers.hubspot.com/changelog/new-recording-transcripts-api-replaces-hs_call_recording_url-for-call-engagements
- CI KB: https://knowledge.hubspot.com/calling/review-call-recordings-and-transcripts ; https://knowledge.hubspot.com/calling/sync-conversation-transcripts-into-hubspot ; https://knowledge.hubspot.com/meetings-tool/configure-conversation-recording-and-transcription-options ; https://knowledge.hubspot.com/meetings-tool/record-and-take-notes-in-meetings-with-meeting-notetaker ; https://knowledge.hubspot.com/calling/manage-call-settings-and-preferences
- Community on transcripts: https://community.hubspot.com/t/retrieving-call-transcripts/76772 ; https://community.hubspot.com/t/retreiving-tanscript/143803 ; https://community.hubspot.com/t/accessing-transcript-url-via-hubspot-api/102411
- Scopes: https://developers.hubspot.com/docs/apps/developer-platform/build-apps/authentication/scopes ; https://developers.hubspot.com/docs/apps/legacy-apps/authentication/scopes ; community scope threads: https://community.hubspot.com/t/crm-emails-api-crm-objects-emails-read-crm-schemas-emails-read-not-available-in-oauth-scope-pick/155041 ; https://community.hubspot.com/t/cant-get-engagments/129828
- Private apps: https://developers.hubspot.com/docs/apps/legacy-apps/private-apps/overview ; sunset: https://developers.hubspot.com/changelog/legacy-private-app-creation-sunset
- Usage limits: https://developers.hubspot.com/docs/developer-tooling/platform/usage-guidelines ; error handling: https://developers.hubspot.com/docs/api-reference/error-handling
- Account types / test accounts: https://developers.hubspot.com/docs/getting-started/account-types ; https://developers.hubspot.com/docs/developer-tooling/local-development/configurable-test-accounts ; https://developers.hubspot.com/blog/how-to-safely-experiment-with-ai-in-hubspot-before-you-touch-real-data ; sandboxes KB: https://knowledge.hubspot.com/account-management/deploy-sandbox-changes-to-production ; calling in test accounts: https://community.hubspot.com/t/calling-settings-endpoint/118871/2
- MEDDPICC: https://meddicc.com/knowledge/setting-up-your-crm-integration ; https://meddicc.com/knowledge/supported-crm-integrations ; https://ecosystem.hubspot.com/marketplace/listing/meddicc-score ; https://meddiccscore.com/hubspot/ ; https://www.superwork.co/blog/meddpicc-hubspot ; deal scores KB: https://knowledge.hubspot.com/records/use-deal-scores ; record summaries KB: https://knowledge.hubspot.com/records/summarize-records
