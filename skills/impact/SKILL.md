---
name: impact
description: One quarter of attributable impact: adoption before and after the training date, win rate by adoption, and how many won deals followed framework actions, with the rule printed next to every number. The proof-point a sales leader or a training provider can put in front of a board.
disable-model-invocation: true
argument-hint: "[YYYY-Qn]"
---

You are producing the FlowSales impact view. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse).

## 1. Inputs

Run `fs.py status --json`. Without assessments, tell the user to run `/flow-sales:audit` first and stop. If `analytics/deal_states.json` is older than the newest assessment, run `fs.py rollup --json`. The quarter is `$ARGUMENTS` (YYYY-Qn) or the current quarter.

## 2. Confirm the rule (gate)

Read `trainingDate` and `attribution` from `fs.py config show --json`. Ask the user to confirm, in one AskUserQuestion call with two questions: the training date (keep, change, or none: without a date the before-and-after view is skipped and "influenced" counts framework actions inside the window) and the influence threshold (keep the default of 3 behaviours across 2 interactions, or stricter: 5 across 3, or looser: 2 across 2). Apply changes with `fs.py config set` and re-run `fs.py rollup --json` if anything changed.

## 3. Compute

Run `fs.py impact --quarter <quarter> --json`, then read `.flow-sales/analytics/impact-<quarter>.md`.

## 4. Present

Show the markdown summary as written (it carries the headline numbers, the rule in words, the influenced deals table, adoption and win rate before and after with n, and the caveats). Add two sentences of your own only if they help: what the strongest evidence in it is, and what would make it stronger (more transcripts, a longer after-period, more closed deals). Never soften or inflate a number, and never drop a caveat.

## 5. Finish (gate)

Ask: open the report's Impact tab in the browser (`fs.py report --open`), copy the markdown to the clipboard (`pbcopy` on macOS), or done. Log with `fs.py log --command impact --note "<quarter>"`.

Correlation language only ("associated with", "followed"), never "caused". No em dashes.
