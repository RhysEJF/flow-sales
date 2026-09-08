# FlowSales contracts

Every module in FlowSales talks through the records, files and commands defined here. Change this file first, then the code. Version: 0.1 (2026-09-07).

## 1. Principles

1. Local-first. Everything lives under `.flow-sales/` in the directory Claude Code was started in (override with `FLOW_SALES_HOME`). Nothing is sent anywhere except the sources the user configured and the model calls their own Claude Code session already makes.
2. Read-only. v0.1 never writes to a CRM or to Granola.
3. Deterministic where possible. Scripts are Python 3.10+ standard library only. The model judges interactions; scripts do everything else (pull, link, validate, roll up, render).
4. Evidence or nothing. A score above 1 needs a verbatim quote that the validator can find in the source text. Unverified quotes cap the score at 1 and are flagged.
5. Propose, then confirm. Ambiguous links, config choices and anything the rep is about to receive go through a human gate in the skill.

## 2. Identifiers

- Deal ids: `hs:<hubspotId>`, `csv:<id>`, `demo:<id>`.
- Interaction ids: `hs:call:<id>`, `hs:email:<id>`, `hs:meeting:<id>`, `hs:note:<id>`, `granola:<documentId>`, `tx:<sha1 of path>`, `csv:<id>`, `demo:<id>`.
- Rep ids: `rep:<ownerId>` for HubSpot owners, `rep:<email>` otherwise.
- Contacts `c:<id>`, companies `co:<id>`.
- Element codes (MEDDPICC): `M` Metrics, `E` Economic Buyer, `DC` Decision Criteria, `DP` Decision Process, `PP` Paper Process, `I` Pain (Identify or Implicate), `CH` Champion, `CO` Competition. MEDDIC uses `M, E, DC, DP, I, CH`.
- Phases (canonical stage buckets): `discovery`, `evaluation`, `proposal`, `commit`, `won`, `lost`. Config maps each CRM stage id to a phase.

## 3. Store layout

```
.flow-sales/
  config.json                      configuration (section 4)
  secrets.json                     optional, chmod 600, only if the user chose to store a token locally
  runs.jsonl                       audit log, one JSON object per command run (section 10)
  cache/hubspot/                   raw API pages, incremental, keyed by object type and id
  cache/granola/                   one JSON per Granola document as exported
  cache/transcripts/               normalised copies of local transcript files
  data/deals.json                  Deal[]            (section 5)
  data/reps.json                   Rep[]
  data/contacts.json               Contact[]
  data/companies.json              Company[]
  data/interactions/<dealIdSafe>.json   Interaction[] linked to that deal (dealIdSafe replaces ':' with '_')
  data/interactions/_unlinked.json      Interaction[] with no accepted link
  data/links.json                  Link[]            (section 6)
  work/batches/<dealIdSafe>.json   assessment batch manifests (section 7); split deals add -p<part>
  assessments/<dealIdSafe>.json    Assessment        (section 8)
  analytics/deal_states.json       DealState[]       (section 9)
  analytics/rep_metrics.json
  analytics/team_metrics.json
  analytics/timeseries.json
  analytics/impact.json
  reports/flowsales-<YYYY-MM-DD>.html
  briefings/<repIdSafe>/<YYYY-MM-DD>.md
  retros/<repIdSafe>/<YYYY>-W<WW>.md
```

## 4. config.json

```json
{
  "version": 1,
  "framework": "meddpicc",
  "window": { "from": "2026-01-01", "to": "2026-09-07" },
  "sources": {
    "hubspot":     { "enabled": true, "baseUrl": "https://api.hubapi.com", "tokenEnv": "HUBSPOT_ACCESS_TOKEN", "pipelines": ["default"], "portalTimezone": "Europe/London" },
    "granola":     { "enabled": true, "mode": "local-cache", "cachePath": null, "exportDir": null },
    "transcripts": { "enabled": false, "folder": null },
    "csv":         { "enabled": false, "dealsFile": null, "interactionsFile": null },
    "demo":        { "enabled": false }
  },
  "stagePhases": { "appointmentscheduled": "discovery", "qualifiedtobuy": "evaluation", "presentationscheduled": "proposal", "decisionmakerboughtin": "commit", "contractsent": "commit", "closedwon": "won", "closedlost": "lost" },
  "reps": "all",
  "trainingDate": null,
  "content": { "emailBodies": true, "callTranscripts": true, "internalNotes": true },
  "anonymize": false,
  "attribution": { "influencedMinBehaviours": 3, "influencedMinInteractions": 2, "decayDays": 45 },
  "judge": { "model": "sonnet", "parallel": 5, "maxInteractionChars": 60000 },
  "linking": { "autoAcceptConfidence": 0.9, "timeGraceDays": 14 },
  "createdAt": "2026-09-07T10:00:00Z",
  "updatedAt": "2026-09-07T10:00:00Z"
}
```

`reps` is `"all"` or a list of rep ids. `trainingDate` is an ISO date or null. Token resolution order: `$HUBSPOT_ACCESS_TOKEN` (or whatever `tokenEnv` names), then `$CLAUDE_PLUGIN_OPTION_HUBSPOT_TOKEN`, then `secrets.json` key `hubspot_token`.

## 5. Canonical records

All timestamps are ISO 8601 UTC strings. All money is a float plus a currency code.

```json
Deal {
  "id": "hs:12345", "source": "hubspot", "name": "Acme expansion",
  "amount": 42000.0, "currency": "GBP",
  "pipeline": "default", "stage": "closedwon", "stageLabel": "Closed Won", "phase": "won",
  "stageHistory": [ { "stage": "appointmentscheduled", "label": "Appointment Scheduled", "phase": "discovery", "at": "2026-03-01T10:00:00Z" } ],
  "outcome": "won", "createdAt": "2026-03-01T10:00:00Z", "closedAt": "2026-06-14T00:00:00Z",
  "ownerId": "rep:41629779", "contactIds": ["c:1", "c:2"], "companyId": "co:7", "companyDomain": "acme.com",
  "meta": {}
}

Interaction {
  "id": "granola:9f2c", "source": "granola", "type": "meeting",
  "dealId": "hs:12345",
  "direction": "outbound", "at": "2026-03-04T14:00:00Z", "durationSec": 1860,
  "title": "Acme discovery",
  "body": "Rhys: ...\nPriya: ...",
  "transcript": [ { "speaker": "Priya", "t": 12.5, "text": "..." } ],
  "notes": "markdown notes if the source has them, else null",
  "summary": "AI summary if the source has one, else null",
  "participants": [ { "name": "Priya Shah", "email": "priya@acme.com", "role": "buyer" }, { "name": "Sam Rep", "email": "sam@vendor.com", "role": "rep" } ],
  "repId": "rep:41629779",
  "recordingUrl": null,
  "meta": { "hubspotType": "meetings" }
}

Rep     { "id": "rep:41629779", "name": "Sam Rep", "email": "sam@vendor.com", "source": "hubspot" }
Contact { "id": "c:1", "name": "Priya Shah", "email": "priya@acme.com", "title": "CFO", "companyId": "co:7", "buyingRole": null }
Company { "id": "co:7", "name": "Acme", "domain": "acme.com" }
```

Rules:
- `type` is one of `call`, `email`, `meeting`, `note`, `transcript`. `direction` is `inbound`, `outbound`, `internal` or `unknown`.
- `body` is the text the judge reads. For transcripts, adapters build `body` as one line per segment: `Speaker: text`. Keep `transcript` for quote verification with speaker attribution.
- `dealId` is null until a link is accepted. Adapters that already know the deal (HubSpot associations, CSV) set it and write a Link with method `crm-association`.
- `repId` is the rep who ran the interaction if known (HubSpot owner, the internal participant, or the deal owner as a fallback set by the linker).
- Adapters never drop an interaction for being empty; they set `body` to `""` and the batch planner skips it.

## 6. Links (the deal to interaction record)

`data/links.json`:

```json
{ "version": 1, "links": [
  { "interactionId": "granola:9f2c", "dealId": "hs:12345",
    "method": "crm-association | email-match | domain-match | time-match | title-match | manual",
    "confidence": 0.95, "status": "auto | confirmed | rejected | pending",
    "evidence": { "matchedEmails": ["priya@acme.com"], "domain": "acme.com", "matchedHubspotMeeting": null, "titleHit": null },
    "candidates": [ { "dealId": "hs:12345", "confidence": 0.95 }, { "dealId": "hs:999", "confidence": 0.4 } ],
    "at": "2026-09-07T10:00:00Z", "by": "linker | user" } ] }
```

Linker rules (highest wins, evidence recorded):
1. `crm-association` (1.0): the source already associates the interaction with the deal.
2. `time-match` (0.95): a HubSpot meeting engagement on the same deal starts within 15 minutes of the interaction and shares at least one attendee email or the same title; the two records are merged (the transcript enriches the HubSpot meeting, one Interaction survives with `meta.mergedFrom`).
3. `email-match` (0.9): at least one non-internal participant email equals a contact associated with the deal, and the interaction time falls inside the deal's open window (createdAt minus grace to closedAt plus grace, or now for open deals).
4. `domain-match` (0.7): a participant's email domain equals the deal's company domain, same window rule. If several deals share the domain and window, all become `candidates` and the link is `pending`.
5. `title-match` (0.5): the interaction title contains the deal name or company name (case-insensitive, whole word), same window rule.
6. Anything at or above `linking.autoAcceptConfidence` with a single candidate is `auto`; otherwise `pending` and the `link` skill asks the user. `manual` links are `confirmed`. Rejected links are kept so the linker does not propose them again.
7. Internal emails (rep domain, the org's own domain from config or from the reps list) never count as buyer matches.

## 7. Assessment batches (input to the judge)

`fs.py plan-assessment` writes `work/batches/<dealIdSafe>.json`, one deal per batch unless a deal exceeds `judge.maxInteractionChars`, in which case its interactions are split across `<dealIdSafe>-p<part>.json` files in time order. Files are named by deal, not by sequence, so a re-plan while judges are running never changes what a running judge's batch file points at; `batchId` is still a running number inside `plan.json`:

```json
{ "batchId": 3, "dealId": "hs:12345", "framework": "meddpicc", "frameworkFile": "<abs path>/frameworks/meddpicc.json", "rubricHash": "sha256:...",
  "deal": { "...Deal minus meta..." },
  "priorState": { "M": 1, "E": 0, "...": 0 },
  "interactions": [ { "interactionId": "granola:9f2c", "at": "...", "type": "meeting", "phaseAtTime": "discovery", "title": "...", "participants": [...], "body": "..." } ],
  "outputFile": "<abs path>/.flow-sales/assessments/hs_12345.json" }
```

`phaseAtTime` comes from the deal's stage history at the interaction's timestamp. `priorState` is the deal's element levels before this batch (for split batches).

## 8. Assessment (output of the judge, one file per deal)

```json
{ "dealId": "hs:12345", "framework": "meddpicc", "rubricHash": "sha256:...", "judgedAt": "2026-09-07T11:00:00Z", "model": "sonnet",
  "interactions": [
    { "interactionId": "granola:9f2c", "at": "2026-03-04T14:00:00Z", "phaseAtTime": "discovery",
      "applicable": ["M", "E", "DC", "I", "CH", "CO"],
      "notApplicableReason": { "DP": "discovery call, process not yet in play", "PP": "discovery call" },
      "elements": {
        "M": { "evidence": 2, "quote": "Month-end close takes us 11 days; we need it under 5 by the next audit.", "speaker": "buyer",
               "whyNotHigher": "Single source, not tied to a KPI owner.", "nextQuestion": "Who reports the close time to the board, and what is it costing you now?",
               "confidence": "high", "behaviour": 1, "behaviourTags": ["asked-metrics"] },
        "E": { "evidence": 0, "quote": null, "speaker": null, "whyNotHigher": "Nobody with budget authority was named.", "nextQuestion": "Who signs a purchase of this size?", "confidence": "high", "behaviour": 0, "behaviourTags": [] }
      },
      "hygiene": { "pitchBeforePain": false, "mutualNextStep": true, "repTalkRatio": null },
      "summary": "Discovery call: pain and a first metric established, no Economic Buyer named." }
  ],
  "dealNotes": "Metrics and pain solid by the second call; Economic Buyer never met before proposal."
}
```

Rules the judge follows (also in `skills/methodology/SKILL.md`):
- Score only elements in `applicable`; list the others in `notApplicableReason`.
- `evidence` uses the 0-3 ladder in the framework file. Above 1 requires `quote` verbatim from `body` and `speaker` of `buyer` or `rep`.
- `behaviour` is 1 only when the rep visibly applied the framework for that element in this interaction; `behaviourTags` come from the fixed vocabulary in section 8.1.
- One sentence each for `whyNotHigher` and `summary`. No scores in prose.

### 8.1 Behaviour tag vocabulary

Each tag has an operational test in `skills/methodology/SKILL.md` ("Behaviour tags: when each one applies"); the judge attaches every tag whose test is met. M: `asked-metrics`, `quantified-impact`. E: `identified-eb`, `asked-eb-access`, `engaged-eb`. DC: `mapped-decision-criteria`, `shaped-decision-criteria`. DP: `mapped-decision-process`, `agreed-mutual-plan`. PP: `asked-paper-process`. I: `identified-pain`, `implicated-pain`. CH: `tested-champion`, `developed-champion`. CO: `named-competition`, `tested-status-quo`, `positioned-differentiation`. Any element: `secured-next-step`, `multi-threaded`, `summarised-and-confirmed`.

### 8.2 Validation (`fs.py validate-assessment <file>`)

- Schema: every listed interaction exists in the batch, every applicable element has an entry, values in range, tags in vocabulary.
- Timestamps: a `judgedAt` later than the validation time (a judge writing local time as UTC) is replaced by the validation time with a warning.
- Source text: the validator reads the deal's batch file(s). When none exists (the plan was rebuilt after the deal was assessed), it verifies against the deal's stored interactions in `data/interactions/<dealIdSafe>.json` instead and adds a warning; it fails only when the deal itself is unknown to the store.
- Quote verification: normalise whitespace and case; a quote is verified if it is a substring of the interaction `body`, else if `difflib.SequenceMatcher` finds a window with ratio at least 0.85. Unverified quotes: set `verified: false`, cap `evidence` at 1, add `"flags": ["quote-unverified"]` on the element. Verified quotes get `verified: true`.
- The validator writes the corrected file in place and prints a JSON report `{ "ok": bool, "errors": [], "warnings": [], "capped": n }`. Exit code 1 on schema errors so the judge agent fixes and re-runs.

## 9. Analytics outputs (`fs.py rollup`)

`deal_states.json` (one per deal):
```json
{ "dealId": "hs:12345", "outcome": "won", "ownerId": "rep:1", "amount": 42000.0, "closedAt": "...", "cycleDays": 105,
  "elements": { "M": { "level": 3, "firstAt": "...", "lastAt": "...", "interactionId": "...", "decayed": false } },
  "total": 19, "maxTotal": 24, "coverage2": 7, "coverage3": 3,
  "gate": "commit-eligible | upside | pipeline | qualify-out",
  "evidenceQualityIndex": 0.8,
  "interactions": 9, "behaviours": 14, "appliedInteractions": 7, "dealAdoption": 0.78,
  "coverageAtPhaseEnd": { "discovery": 3, "evaluation": 5 },
  "stageGaps": [ { "phase": "proposal", "element": "E", "expected": 2, "actual": 1 } ],
  "influenced": { "isInfluenced": true, "rule": "3 behaviours across 2 interactions after 2026-05-01 and E moved 1 to 2", "behaviours": 9, "interactions": 5, "movedElements": ["E", "DP"] } }
```

Definitions:
- Element level = max verified evidence across the deal's interactions. Decay: if the last interaction supporting a level of 2 or more is older than `attribution.decayDays` before `closedAt` (or before the window end for open deals), level drops by 1 and `decayed` is true.
- `coverage2` = elements with level at least 2. `total` = sum of levels.
- `gate`: commit-eligible when all elements at least 2 and E and CH at 3 and PP at 2; qualify-out when total at most 9 after 4 or more interactions, or E or CH still 0 after the evaluation phase; upside when coverage2 at least 6; else pipeline.
- `evidenceQualityIndex` = share of element scores of 2 or more that come from buyer quotes.
- `dealAdoption` = appliedInteractions / interactions, where applied means at least one behaviour tag.
- `coverageAtPhaseEnd[phase]` = coverage2 computed using only interactions before the deal left that phase.
- `influenced` follows the config rule: won deal, at least `influencedMinBehaviours` behaviours across at least `influencedMinInteractions` interactions after `trainingDate` (or inside the window when no training date), and at least one element moved from 0-1 to 2-3 in one of those interactions.

`rep_metrics.json` (one per rep): interactions, appliedInteractions, adoptionRate, adoptionByElement (applied / applicable per element), behaviourTagCounts, dealsWon, dealsLost, dealsOpen, winRate, avgCoverageAtClose (won and lost separately), avgTotalWon, avgTotalLost, beforeTraining {adoptionRate, n}, afterTraining {adoptionRate, n}, adoptionLift, weakestElements (three lowest adoptionByElement), strongestElements, evidenceQualityIndex.

`team_metrics.json`: totals, winRate, winRateByAdoptionTertile [{tertile, n, winRate, medianCycleDays, avgAmount}], winRateByCoverageAtPhaseEnd {discovery: [{coverageBand, n, winRate}], evaluation: [...]}, elementWeakness [{element, avgLevelWon, avgLevelLost, adoptionRate}], beforeAfter {before: {...}, after: {...}}, dataCoverage {interactionsByType, dealsWithTranscripts, dealsWithoutInteractions, unlinkedInteractions}.

`timeseries.json`: weekly buckets (ISO week) per rep and for the team: interactions, applied, adoptionRate, per-element applied counts.

`impact.json` (from `fs.py impact --quarter 2026-Q3`): quarter, trainingDate, rule text, influencedDeals [{dealId, name, amount, currency, ownerId, movedElements, behaviours}], influencedCount, influencedAmount, influencedAmountByCurrency {GBP: n, EUR: n}, wonCount, wonAmount, wonAmountByCurrency, adoptionBefore, adoptionAfter, winRateBefore, winRateAfter, caveats []. Money is never converted: `*Amount` sums raw numbers and is only meaningful when every deal shares a currency; renderers show the `*ByCurrency` breakdown whenever more than one currency is present (team_metrics carries `amountWonByCurrency` and `currencies` the same way).

## 10. CLI (`scripts/fs.py`)

`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py" <command> [options]`. Every command accepts `--home <dir>` (default `$FLOW_SALES_HOME` or `./.flow-sales`) and `--json` (machine-readable stdout). Exit code 0 success, 1 validation or user error, 2 source or network error. Every run appends `{ "at", "command", "args", "ok", "durationMs", "read": [...], "wrote": [...], "notes" }` to `runs.jsonl`.

| Command | Does |
|---|---|
| `init` | create the store and a default config |
| `config get <key>` / `config set <key> <jsonValue>` | dotted keys, e.g. `sources.hubspot.pipelines` |
| `doctor` | python version, token found, HubSpot reachable and scopes present (parses MISSING_SCOPES), Granola cache found, folders exist |
| `pull hubspot [--since <date>]` | deals in window, stage history, associations, engagements, owners, contacts, companies into cache and data |
| `import demo [--seed 7]` | generate the demo dataset into data (and the demo links) |
| `import csv --deals <f> --interactions <f>` | CSV adapter |
| `import granola [--cache <path> \| --export-dir <dir>]` | Granola adapter |
| `import transcripts --folder <dir>` | local transcripts adapter |
| `link [--dry-run]` | run the linker; prints pending candidates as JSON |
| `link confirm <interactionId> <dealId>` / `link reject <interactionId> [<dealId>]` | resolve pending links |
| `plan-assessment [--force] [--sample <n>] [--deal <id>] [--estimate-only]` | write batches for deals whose interactions changed or whose rubric hash differs; prints the volume estimate and `estCostUsd` (low to high at list price, prices from `judge.pricingUsdPerMTok`); `--estimate-only` computes the same totals without clearing or writing anything |
| `validate-assessment <file>` | section 8.2 |
| `rollup` | section 9 |
| `impact --quarter <YYYY-Qn>` | section 9 impact.json plus a markdown summary |
| `report [--open]` | build the HTML report |
| `briefing-data --rep <id> [--date <d>]` | JSON pack for the standup skill: active deals with state, last three interactions each, stage gaps, weakest elements, suggested next questions from the framework file (`focus`: up to three applicable elements below the top level, lowest first) |
| `retro-data --rep <id> [--week <YYYY-Www>]` | JSON pack for the retro skill: this week vs last week vs benchmark, deals moved, wins and losses with element post-mortem inputs. Without `--week`: the current ISO week, or the previous one when run on a Monday or Tuesday |
| `status` | counts of everything in the store, `lastRun` (newest successful timestamp per command from runs.jsonl, including skills that log with `fs.py log --command`) and `latestReport` |
| `eval-golden build [--parts n]` | write the golden set (`evals/golden/snippets.json`) as batch files `work/batches/demo_golden-<n>.json` into the store at `--home` (a scratch store), with `work/plan.json`; prints the files to hand to the deal-assessor agent |
| `eval-golden compare [--model m] [--note t] [--strict]` | validate `assessments/demo_golden-*.json` in that store, compare with the labels (section 13), print metrics, secondary checks and the confusion table, append to `evals/golden/runs.jsonl`, write detail to `evals/golden/results/`. `--strict` exits 1 when a target is missed or a snippet was not judged |

## 11. Framework file (`frameworks/meddpicc.json`)

```json
{ "slug": "meddpicc", "name": "MEDDPICC", "version": "0.1.0", "maxLevel": 3,
  "elements": [
    { "code": "M", "name": "Metrics", "definition": "...", "questions": ["..."], "evidenceSignals": ["..."],
      "anchors": { "0": "...", "1": "...", "2": "...", "3": "..." },
      "exampleQuotes": { "1": "...", "2": "...", "3": "..." },
      "nextQuestionAt1": "...", "behaviourTags": ["asked-metrics", "quantified-impact"],
      "failureModes": ["..."],
      "stageExpectations": { "discovery": 2, "evaluation": 2, "proposal": 2, "commit": 2 },
      "applicableFrom": "discovery" } ],
  "generalBehaviourTags": ["secured-next-step", "multi-threaded", "summarised-and-confirmed"],
  "scoring": { "quoteRequiredAbove": 1, "decayDays": 45, "commitGate": { "all": 2, "E": 3, "CH": 3, "PP": 2 }, "qualifyOut": { "maxTotal": 9, "minInteractions": 4 } },
  "sources": ["..."] }
```

The rubric hash is the sha256 of the file's canonical JSON (sorted keys, no whitespace). `meddic.json` is the same structure with six elements.

## 12. Runs log

`runs.jsonl` is the kill-switch companion: it shows what every command read and wrote. Skills append their own lines through `fs.py log --command <name> --note "..."`.

## 13. Golden-set evaluation (`evals/golden/`)

`snippets.json` holds labelled interactions (`id`, `type`, `phase`, `kind`, `speakerRoles`, `body`, `expected`, `notApplicable`, `expectedBehaviourTags`, optional `reversal` and `hygiene`) and `targets`. `fs.py eval-golden build` turns them into batches shaped exactly like section 7 under deal ids `demo:golden-<n>`; the judge is run on them unchanged. `fs.py eval-golden compare` validates the output first (section 8.2, so unverified quotes are capped as in production) and computes:

- `exactAgreement`: share of (snippet, expected element) pairs where judged `evidence` equals the label.
- `withinOneLevel`: share of pairs with absolute difference at most 1.
- `behaviourTagAgreement`: mean over snippets of the Jaccard overlap between the union of judged `behaviourTags` and `expectedBehaviourTags` (empty against empty counts 1.0).
- Secondary checks: applicability mismatches, quote failures, rep-assertion snippets scored above 1, reversal snippets that used the earlier quote, pitch-monologue snippets with any tag or without `pitchBeforePain`, missing snippets.

Each run appends `{at, rubricHash, framework, frameworkVersion, goldenVersion, model, note, metrics, passed, checks, store}` to `evals/golden/runs.jsonl` and writes the per-snippet detail and confusion tables to `evals/golden/results/<timestamp>-<model>.json`. A change to a framework file, the judge prompt or the model ships only if no target regresses against the last recorded run.
