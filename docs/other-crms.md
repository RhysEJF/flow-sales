# Other CRMs, CSV exports and local transcripts

FlowSales reads HubSpot directly. Every other CRM comes in through one of two file-based ports, both read-only and both local:

- **CSV**: two files, one of deals and one of interactions. `fs.py import csv --deals deals.csv --interactions interactions.csv`
- **Transcripts folder**: a directory of `.md`, `.txt`, `.vtt` or `.json` meeting transcripts. `fs.py import transcripts --folder ./transcripts`

Both write the same canonical records HubSpot produces (docs/CONTRACTS.md section 5), so everything downstream (link, plan-assessment, rollup, report, standup, retro) behaves the same. Sample files live in `docs/examples/`; try them with `fs.py import csv --deals docs/examples/deals.csv --interactions docs/examples/interactions.csv`.

## 1. The port contract in plain English

FlowSales needs to know four things about a sales team:

1. **The deals**: what was being sold, for how much, to which company, which rep owned it, when it opened, when and how it closed, and which pipeline stage it went through. Stages are mapped to six phases (discovery, evaluation, proposal, commit, won, lost) by `stagePhases` in `.flow-sales/config.json`.
2. **The people**: the reps (by email) and the buyer contacts on each deal (by email). Emails are how interactions get attached to deals when the CRM does not say which deal a call belonged to.
3. **The interactions**: every call, meeting, email and note, with a timestamp, the people involved, and the actual text. The text is what the judge reads; a call without a transcript scores nothing above level 1.
4. **The link** between an interaction and a deal, when the CRM knows it. When it does not, leave `deal_id` empty and `fs.py link` proposes a deal from participant emails, company domain, timing and title, asking you to confirm anything below the auto-accept threshold.

What FlowSales never needs: pipeline value forecasts, custom fields, activity counts, or write access. It never sends anything back.

## 2. The CSV files

### deals.csv

| column | required | meaning |
|---|---|---|
| `id` | yes | the CRM's deal id. Stored as `csv:<id>` |
| `name` | yes | deal name |
| `amount` | | number, no currency symbol (`42000`) |
| `currency` | | ISO code (`GBP`, `EUR`, `USD`) |
| `pipeline` | | pipeline name; defaults to `default` |
| `stage` | | the CRM stage id. Mapped to a phase through `stagePhases` in config, then by keywords in `stage_label` (won, lost, discovery, demo, proposal, contract, ...), else `evaluation` |
| `stage_label` | | human label for the stage |
| `outcome` | | `won`, `lost` or `open`. Derived from the stage when empty |
| `created_at` | yes | ISO 8601 (`2026-03-02T10:00:00Z` or `2026-03-02`) |
| `closed_at` | | ISO 8601, empty for open deals |
| `owner_email` | | the rep's email. Rep id becomes `rep:<email>` |
| `owner_name` | | the rep's display name |
| `contact_emails` | | semicolon-separated buyer emails (`priya@acme.example;dev@acme.example`) |
| `contact_names` | | semicolon-separated names in the same order |
| `company_name` | | account name |
| `company_domain` | | account web domain (`acme.example`); used for domain matching |
| `stage_history` | optional | semicolon list of `stage@ISO` moves (`appointmentscheduled@2026-03-02T10:00:00Z;closedwon@2026-06-14T00:00:00Z`). Without it a closed deal gets a two-point history (created, closed) and an open deal a single point, which is enough for the judge but makes "coverage at phase end" coarse |

### interactions.csv

| column | required | meaning |
|---|---|---|
| `id` | yes | the CRM's activity id. Stored as `csv:<id>` |
| `deal_id` | | the deal's `id` from deals.csv. Empty means "let the linker decide" |
| `type` | yes | `call`, `email`, `meeting`, `note` or `transcript` |
| `direction` | | `inbound`, `outbound`, `internal` or `unknown` (notes default to internal) |
| `at` | yes | ISO 8601 timestamp |
| `duration_sec` | | seconds, for calls and meetings |
| `title` | | subject or meeting title |
| `body` | | the text. Multi-line bodies are fine inside double quotes. For calls, meetings and transcripts, one line per turn as `Speaker Name: what they said` also fills the `transcript` segments the judge uses for speaker attribution |
| `participants` | | semicolon-separated `Name <email>` entries; a bare email also works |
| `rep_email` | | the rep who ran it. Falls back to the internal participant, then the deal owner |

Rules:

- Emails whose domain matches a rep's domain (or `org.internalDomains` in config) are internal and never count as buyer matches.
- Re-importing the same ids replaces the previous records; the files are the source of truth.
- Both files are optional on any given run: `--deals` alone refreshes deals, `--interactions` alone adds activity against deals already in the store.
- Bad rows (unknown type, unparseable date, missing id) stop the import before anything is written, with the line number.

## 3. What the canonical JSON looks like

Every row becomes one of these (full schema in docs/CONTRACTS.md section 5):

```json
{ "id": "csv:D-1042", "source": "csv", "name": "Acme Logistics reporting", "amount": 42000.0, "currency": "GBP",
  "pipeline": "default", "stage": "closedwon", "stageLabel": "Closed Won", "phase": "won",
  "stageHistory": [ { "stage": "appointmentscheduled", "label": "appointmentscheduled", "phase": "discovery", "at": "2026-03-02T10:00:00Z" } ],
  "outcome": "won", "createdAt": "2026-03-02T10:00:00Z", "closedAt": "2026-06-14T00:00:00Z",
  "ownerId": "rep:sam@vendor.example", "contactIds": ["c:priya@acme.example"], "companyId": "co:acme.example", "companyDomain": "acme.example" }

{ "id": "csv:I-1", "source": "csv", "type": "call", "dealId": "csv:D-1042", "direction": "outbound", "at": "2026-03-04T14:00:00Z",
  "durationSec": 1860, "title": "Acme discovery call",
  "body": "Sam Rep: Thanks for the time, Priya...\nPriya Shah: Month-end close takes us 11 days...",
  "transcript": [ { "speaker": "Sam Rep", "t": null, "text": "Thanks for the time, Priya..." } ],
  "participants": [ { "name": "Priya Shah", "email": "priya@acme.example", "role": "buyer" }, { "name": "Sam Rep", "email": "sam@vendor.example", "role": "rep" } ],
  "repId": "rep:sam@vendor.example" }
```

Linked interactions are stored in `data/interactions/<dealIdSafe>.json` with a `crm-association` link in `data/links.json`; unlinked ones wait in `data/interactions/_unlinked.json`.

## 4. Export tips per CRM

**Pipedrive.** Deals: Deals list view, add the columns Title, Value, Currency, Pipeline, Stage, Status, Add time, Won time / Lost time, Owner email, Person email, Organization name and Organization website, then Export (CSV). Map Status (open, won, lost) to `outcome`, Stage to `stage`, Won/Lost time to `closed_at`. Activities: Activities list view with Type, Subject, Note, Due date, Deal ID, Participants; Pipedrive stores emails under Mail, so export the Mail thread list separately and give each row a `deal_id`. Call recordings and transcripts arrive through the transcripts folder route.

**Attio.** Deals is a custom object in most workspaces. Open the list, add attributes for Name, Value, Stage, Owner, Associated people (email), Associated company (domain), Created at and Closed at, then Export to CSV. Attio's Notes and Meetings export as separate lists; join them on the record id to fill `deal_id`. Attio's stage attribute exports the label, so put the same text in `stage` and `stage_label` and add `stagePhases` entries in config for those labels.

**Close.** Opportunities: Reports, Opportunities, Export CSV, which includes Lead name, Value, Status type (active, won, lost), Status label, Date created, Date won, User email and Lead contacts. Use Status type for `outcome` and Status label for `stage`. Activities: Reports, Activity, Export with Call, Email and Note types selected; Close includes the call transcript text when call recording is on. Every activity row carries the Lead id, not the opportunity id, so either map lead to opportunity yourself or leave `deal_id` empty and let the linker use contact emails.

**Salesforce.** Build two reports. Opportunities report with Opportunity ID, Opportunity Name, Amount, Currency ISO Code, Stage, Is Won, Is Closed, Created Date, Close Date, Owner Email, Account Name, Account Website, and Contact Roles (Contact Email, Contact Name). Activities report (Tasks and Events) with Activity ID, Subject, Type, Date, Related To ID, Assigned Email, Description, and, if Einstein Activity Capture or a call tool is installed, the transcript field. Export both as Details Only CSV, rename the headers to the ones above (`Related To ID` becomes `deal_id`), and set `outcome` from Is Won and Is Closed. The Stage History related list, exported as a third report, converts directly into `stage_history`.

**Anything else.** If the CRM can produce a list of deals and a list of activities with timestamps and emails, it fits. Rename the headers, keep the ids, and the adapter does the rest.

## 5. The transcripts folder

`fs.py import transcripts --folder <dir>` walks the folder recursively and turns every `.md`, `.txt`, `.vtt` and `.json` file into one Interaction of type `transcript`, source `transcripts`, id `tx:<sha1 of the relative path>`. Moving a file changes its id; editing it does not.

**Timestamp** (first match wins): front matter `date:` (`2026-03-04T14:00:00Z`, `2026-03-04 14:00` or `2026-03-04`); a date in the filename (`2026-03-04-acme-discovery.md`, `2026-03-04-1400-acme.txt`); the file's modification time.

**Title**: front matter `title:`, else the filename without its date and extension (`acme discovery`).

**Participants**: front matter `participants:` (a list, or a comma-separated line) of `Name <email>` entries, or any `Name <email>` lines above the first speaker line. Emails at a rep domain get role `rep` and set `repId`; others are buyers.

**Deal**: front matter `deal_id:` with a FlowSales deal id (`hs:12345`, `csv:D-1042`). Without it the transcript goes to `_unlinked` and `fs.py link` finds the deal from the participants, the domain, the time and the title.

**Segments** by file type:

- `.md` / `.txt`: one turn per line as `Speaker: text`, optionally prefixed with a timestamp `[00:12:31] Speaker: text`. Lines without a speaker continue the previous turn. A file with no speaker lines is imported as prose.

  ```markdown
  ---
  title: Acme discovery
  date: 2026-03-04 14:00
  participants:
    - Priya Shah <priya@acme.example>
    - Sam Rep <sam@vendor.example>
  deal_id: csv:D-1042
  ---
  Sam Rep: Thanks for the time, Priya.
  Priya Shah: Month-end close takes us 11 days.
  ```

- `.vtt`: standard WebVTT cues. The speaker comes from `<v Priya Shah>` voice tags or a `Priya Shah:` prefix in the cue text; `t` is the cue start in seconds.

- `.json`: either a list of `{ "speaker", "text", "t" }` objects, or an object with a `segments` (or `transcript`) list plus optional `title`, `date`, `participants` (strings or `{name, email}`), `deal_id` and `duration`.

A normalised copy of every file is written to `.flow-sales/cache/transcripts/<id>.json`. Re-importing the folder replaces records with the same id, so a corrected file overwrites its earlier version.

## 6. Writing a new adapter

An adapter is one Python module under `scripts/flowsales/crm/` with a `run(ctx, args) -> int` function, standard library only. `fs.py import <source>` calls it through `scripts/flowsales/crm/import_cmd.py`, which enables `sources.<source>` in config and appends the run to `runs.jsonl` when it returns 0.

1. **Read your source** into canonical records (docs/CONTRACTS.md section 5). Use `flowsales.util.parse_iso` and `to_iso` for timestamps, `store.config.phase_for_stage(stage_id, label)` for phases, `flowsales.util.transcript_to_body(segments)` to build `body` from segments. Ids: `<prefix>:<id>` with a prefix registered in `scripts/flowsales/schema/validate.py` (`ID_PREFIXES`), reps `rep:<email>`, contacts `c:<id>`, companies `co:<id>`.
2. **Validate before writing**: `from flowsales.schema.validate import validate_records`; `errors = validate_records("deal", deals)` (and `interaction`, `rep`, `contact`, `company`). Print the errors and return 1 if any; never write a half-valid store.
3. **Write through the Store** (`flowsales.store.Store`): `save_deals(Store.upsert(store.load_deals(), deals))` and the same for reps, contacts, companies; `save_interactions(deal_id, items)` for interactions the source already associates with a deal, plus a link record `{interactionId, dealId, method: "crm-association", confidence: 1.0, status: "auto", ...}` in `store.load_links()["links"]`; `save_unlinked(...)` for the rest. Cache raw pages under `store.cache_dir / "<source>"` if you want incremental pulls.
4. **Report**: print a short summary (respect `ctx["json"]`), and set `ctx["summary"] = {"read": [...], "wrote": [...], "notes": "..."}` so the runs log shows what happened. Return 0.
5. **Register**: add the module to `ADAPTERS` in `import_cmd.py` and the source name to the `import` subcommand choices in `scripts/fs.py`, add a `sources.<name>` block to `default_config()` in `config.py`, and a test in `tests/`. `scripts/flowsales/crm/csv_adapter.py` is the smallest complete example; `transcripts_folder.py` shows the parsing helpers you can reuse (`parse_person`, `parse_speaker_lines`, `parse_vtt`, `parse_front_matter`).
