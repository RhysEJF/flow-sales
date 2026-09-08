---
name: retro
description: A rep's weekly retro: adoption this week against last week, the four-week average and the team, deals that moved, wins and losses explained by element with the quotes, progress on last week's focus, and one focus for next week. Writes a note the rep can keep or share.
disable-model-invocation: true
argument-hint: "[rep name or email] [YYYY-Www] [--no-refresh]"
---

You are running a FlowSales weekly retro for one rep. Load the `flow-sales:coaching-voice` skill first. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse).

## 1. Who and when

Run `fs.py status --json`; without a store, point to `/flow-sales:setup` and stop. Resolve the rep from `$ARGUMENTS` or ask (AskUserQuestion, up to four options per question). The week is the ISO week in `$ARGUMENTS`; otherwise leave `--week` off and `retro-data` picks the current ISO week, or the week just finished when today is Monday or Tuesday. Tell the user which week you are writing about.

## 2. Refresh (gate, skipped with --no-refresh)

Same as the stand-up: offer to pull and import the week's activity, link (automatic, asking only about ambiguous ones), plan, judge new batches with `flow-sales:deal-assessor` agents, and `fs.py rollup`. One line of progress.

## 3. Pack

Run `fs.py retro-data --rep <rep id> --week <YYYY-Www>` and read the JSON: adoption this week, last week, four-week average, team; interactions by type; behaviour tags; deals moved; wins and losses with element levels; silent deals; last retro's focus if any.

## 4. Write the retro

Follow the retro template in the coaching-voice skill. The week in numbers (four lines, counts not decimals). Deals that moved, each with the evidence that moved it or the element still missing. Wins and losses: for each, the strong elements and the one never established, with the quote or the silence (pull the quotes from the assessment file for that deal: `.flow-sales/assessments/<dealIdSafe>.json`, read only the element entries you cite). Last week's focus: what this week's evidence shows. Next focus: one element, on which deals, with one example phrasing. End with the line `Focus: <element>` so the next retro can read it. Under 450 words.

## 5. Deliver (gate)

Show the retro. Ask: keep, edit, or discard. Save to `.flow-sales/retros/<repIdSafe>/<YYYY-Www>.md`. Then ask whether the rep wants a five-line manager summary (see the coaching-voice skill); if yes, write it to `.flow-sales/retros/<repIdSafe>/<YYYY-Www>-manager.md` and offer the clipboard. Log with `fs.py log --command retro --note "<rep> <week>"`.

The retro belongs to the rep. Nothing is sent, nothing is shown to anyone else by this skill. No em dashes.
