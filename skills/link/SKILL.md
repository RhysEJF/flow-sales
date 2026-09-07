---
name: link
description: Build and maintain the record of which calls, meetings, emails and transcripts belong to which deal. Applies the automatic links (CRM associations, attendee emails, company domains, times, titles) and walks you through the ambiguous ones. Run after importing Granola meetings or transcripts, or whenever audit reports unlinked interactions.
disable-model-invocation: true
argument-hint: "[--auto-only]"
---

You are maintaining the FlowSales link record (`.flow-sales/data/links.json`). Use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"`.

## 1. Apply the automatic links

Run `fs.py link --json`. Report the counts by method (crm-association, time-match, email-match, domain-match, title-match) and how many interactions are now pending or still unlinked. If `$ARGUMENTS` contains `--auto-only`, stop here with the summary.

## 2. Resolve pending candidates (gate)

Run `fs.py link pending --json`. For each pending interaction, in batches of up to four per AskUserQuestion call, ask: "Which deal does this belong to?" and show the interaction's date, title, participants (names and emails) and a one-line body preview, with one option per candidate deal (deal name, company, stage, confidence as a percentage and the evidence behind it) plus "None of these, leave unlinked". Apply each answer immediately: `fs.py link confirm <interactionId> <dealId>` or `fs.py link reject <interactionId>`. Continue until nothing is pending or the user asks to stop.

## 3. Manual links

If the user names a deal for an interaction that had no candidates, run `fs.py link confirm <interactionId> <dealId>`. If they want to move an interaction to a different deal, reject the old link first, then confirm the new one.

## 4. Finish

Run `fs.py status --json` and report: interactions linked, unlinked, pending. Remind the user that unlinked interactions are never scored and appear in the report's data coverage panel, and that the link record is theirs to edit at `.flow-sales/data/links.json`.

Plain language, no em dashes, never write to the CRM.
