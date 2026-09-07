# Privacy and control

FlowSales was designed for teams whose sales data is the most sensitive thing they own, and for sales trainers who refuse to touch client CRMs. The model is simple: the customer runs FlowSales on their own machine against their own data, and nobody else runs anything.

## What goes where

| Data | Where it lives | Who sees it |
|---|---|---|
| CRM records (deals, contacts, companies, calls, emails, meetings, notes) | `.flow-sales/cache/` and `.flow-sales/data/` on your disk | you |
| Granola meetings and transcripts | `.flow-sales/cache/granola/` and `.flow-sales/data/` | you |
| Interaction text sent for scoring | your own Claude Code session, one interaction batch at a time | the model provider your Claude Code session already uses; FlowSales adds no other recipient |
| Assessments, analytics, reports, briefings, retros | `.flow-sales/` | you, and whoever you send the files to |
| Tokens and keys | environment variables, the plugin's user config, or `.flow-sales/secrets.json` with permissions 600 | you; FlowSales never prints them and never writes them anywhere else |

FlowSales has no server, no telemetry and no update check. The plugin ships no hooks, so nothing runs unless you type a command.

## Read-only

The HubSpot private app needs read scopes only. FlowSales never creates, updates or deletes CRM records, never sends email, never posts to Slack. The link record, the assessments and the coaching notes are local files.

## Anonymisation

Setting `anonymize` to true in `.flow-sales/config.json` replaces contact names, email addresses and company names with role labels (Buyer 1, Company A) in the text sent for scoring and in the reports. Quotes keep their wording otherwise. Use it when the people on the calls did not consent to downstream processing, or when the report will leave the team.

## The audit log

`.flow-sales/runs.jsonl` records every command: when it ran, what it read, what it wrote, whether it succeeded. Skills add a line each time they finish. It is the answer to "what did this thing do".

## Kill switch

`/plugin disable flow-sales` stops the commands. Deleting `.flow-sales/` removes every cached record, assessment and report. Revoking the HubSpot private app or the Granola API key cuts the sources.

## What the rep sees

Briefings and retros are written to the rep and saved under the rep's own folder. Managers see a summary only when the rep chooses to produce one. Per-interaction scores are coaching inputs and adoption telemetry, not a performance-review feed; the coaching-voice rules in the plugin forbid rankings of named colleagues in rep-facing text.
