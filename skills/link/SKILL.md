---
name: link
description: Fix or re-check which calls, meetings, emails and transcripts belong to which deal, without scoring anything. Audit already does this for you and asks about the ambiguous ones; run link on its own after importing Granola meetings or transcripts, to move an interaction to a different deal, or to revisit the ones you skipped.
disable-model-invocation: true
argument-hint: "[--auto-only]"
---

You are maintaining the FlowSales link record (`.flow-sales/data/links.json`). Use `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"`. This is the same linking step `/flow-sales:audit` runs before it scores; here it runs alone.

## 1. Apply the automatic links

Run `fs.py link --json`. Report the counts by method (crm-association, time-match, email-match, domain-match, title-match) and how many interactions are now pending or still unlinked. If `$ARGUMENTS` contains `--auto-only`, stop here with the summary.

## 2. Resolve pending candidates (gate)

Run `fs.py link pending --json`. For each pending interaction, in batches of up to four per AskUserQuestion call, ask: "Which deal does this belong to?" and show the interaction's date, title, participants (names and emails) and a one-line body preview, with one option per candidate deal (deal name, company, stage, confidence as a percentage and the evidence behind it) plus "None of these, leave unlinked". Apply each answer immediately: `fs.py link confirm <interactionId> <dealId>` or `fs.py link reject <interactionId>`. Continue until nothing is pending or the user asks to stop.

## 3. Manual links

If the user names a deal for an interaction that had no candidates, run `fs.py link confirm <interactionId> <dealId>`. If they want to move an interaction to a different deal, reject the old link first, then confirm the new one.

## 4. Finish

Run `fs.py status --json` and report: interactions linked, unlinked, pending. Remind the user that unlinked interactions are never scored and appear in the report's data coverage panel, that the link record is theirs to edit at `.flow-sales/data/links.json`, and that the next `/flow-sales:audit` will score anything newly linked.

Plain language, no em dashes, never write to the CRM.
