# HubSpot

How FlowSales reads a HubSpot portal: deals, stage history, contacts, companies, owners, and the calls, emails, meetings and notes on each deal. Read-only. Nothing is written back.

```
python3 scripts/fs.py doctor --source hubspot        # token found, scopes present, portal reachable, stage ids mapped
python3 scripts/fs.py pull hubspot                    # everything in the window into .flow-sales/cache/hubspot and data/
python3 scripts/fs.py pull hubspot --since 2026-09-01 # incremental refresh (the standup and retro skills use this)
```

## 1. Create a private app with read scopes

1. In HubSpot: Settings > Integrations > Legacy apps > Private apps > Create a private app. Name it FlowSales.
2. On the Scopes tab tick exactly these six read scopes:

| Scope | Why |
| --- | --- |
| `crm.objects.deals.read` | deals, amounts, stages and the stage history |
| `crm.objects.contacts.read` | buyer names, emails and titles on each deal |
| `crm.objects.companies.read` | company names and domains (the linker uses domains) |
| `crm.objects.owners.read` | reps |
| `crm.schemas.deals.read` | pipelines and stage labels, so stages can be mapped to phases |
| `sales-email-read` | email bodies; without it emails arrive as subjects only |

Calls, meetings and notes come through the deals, contacts and companies read scopes; there is no separate scope to tick for them.

3. Create the app and copy the access token once. HubSpot will not show it again.

Timing: HubSpot removes private-app creation from the UI on 2026-09-28 for new accounts and on 2026-10-26 for existing accounts. Existing private apps keep working. After those dates the same read access is created as a Service Key; the token is used the same way below.

## 2. Give FlowSales the token

Three places, checked in this order:

1. The environment variable named in `config.sources.hubspot.tokenEnv` (default `HUBSPOT_ACCESS_TOKEN`).
2. The plugin's user config option `hubspot_token`: `/plugin configure flow-sales` inside Claude Code, or `claude plugin install flow-sales@flow-sales --config hubspot_token=<token>`. Claude Code passes it to the CLI as `CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN` and stores it in the system keychain.
3. `.flow-sales/secrets.json` with `{"hubspot_token": "..."}` and permissions 600. The setup skill writes this for you if you paste the token; it never echoes the token back.

Then `fs.py doctor --source hubspot`. It validates the token, lists the portal id and scopes, names any missing scope, and lists deal pipelines and stage ids that still need a phase (`fs.py config set stagePhases.<stageId> "<phase>"`).

## 3. What a pull does

For every deal in the configured pipelines whose activity falls inside `config.window`:

- Deal properties, the stage history (`hs_date_entered_*` per stage), owner, associated contacts and companies.
- Engagements associated with the deal: calls (`hs_call_title`, `hs_call_body`, `hs_call_summary`, the recording URL if present), emails (subject and body with `sales-email-read`), meetings (title, body, attendees, start and end), notes.
- Everything is cached under `.flow-sales/cache/hubspot/` as raw API pages and mapped to the canonical records in `docs/CONTRACTS.md` section 5. Interactions that HubSpot already associates with the deal get a `crm-association` link with confidence 1.0.

Rate limits: private apps get about 110 requests per 10 seconds and a shared daily quota; the client backs off on 429 and the cache makes re-runs cheap.

## 4. Transcripts: pair HubSpot with Granola or a folder

HubSpot's transcript API is only reachable by OAuth public apps, and there is no documented way to find a transcript id from a call, so a private app cannot read call transcripts. What you get from HubSpot for a call is the rep's notes, the AI call summary where Conversation Intelligence is on, and the recording URL. FlowSales scores those honestly (a summary is rep-side evidence, level 1 at most unless the buyer is quoted) and the report's Method tab shows how many deals had transcripts.

For the calls themselves, add Granola (`docs/granola.md`) or a folder of transcript files (`fs.py import transcripts --folder <dir>`). The linker attaches them to deals by attendee email, company domain, meeting time or title, and merges a transcript into the matching HubSpot meeting when both exist.

## 5. Test accounts

Any HubSpot account can create up to ten developer test accounts (90-day Enterprise trials, empty). `scripts/dev/seed_hubspot.py` seeds one with the demo dataset so the pull can be exercised end to end; it needs the write scopes for deals, contacts, companies and engagements on a separate private app in that test account. Never point the seeder at a production portal.

## 6. Privacy

Only the six read scopes above are requested. Email bodies, call notes and internal notes can each be switched off in `config.content` before the first pull. See `docs/privacy.md` for what leaves the machine (nothing except calls to HubSpot itself and the model calls your Claude Code session already makes).
