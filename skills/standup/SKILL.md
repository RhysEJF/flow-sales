---
name: standup
description: A rep's daily stand-up: refresh the latest calls and emails on their deals, score anything new, ask the rep where each live deal stands before showing the evidence, then write a two-minute briefing with the next framework move per deal and one thing to practise today.
disable-model-invocation: true
argument-hint: "[rep name or email] [--no-refresh]"
---

You are running a FlowSales stand-up for one rep. Load the `flow-sales:coaching-voice` skill before writing anything rep-facing. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse). Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## 1. Who

Run `fs.py status --json`; if there is no store, point to `/flow-sales:setup` and stop. Read `.flow-sales/data/reps.json`. If `$ARGUMENTS` names a rep (name or email, case-insensitive), use them; otherwise ask which rep with AskUserQuestion (up to four per question, more questions if needed).

## 2. Refresh (gate, skipped with --no-refresh)

Ask whether to pull the latest activity first. If yes and HubSpot is enabled, run `fs.py pull hubspot --since <yesterday>`; if Granola is enabled with the MCP route, export the last 7 days as described in the setup skill and run `fs.py import granola --export-dir .flow-sales/cache/granola`; then `fs.py link --json` and, if anything is pending for this rep's deals, resolve it the way the audit skill's link step does. Then `fs.py plan-assessment --json`: if it planned batches, judge them exactly as the audit skill does (parallel `flow-sales:deal-assessor` agents, one per batch, up to config `judge.parallel`), then `fs.py rollup --json`. Keep this quiet: one line of progress.

## 3. Pack

Run `fs.py briefing-data --rep <rep id> --date <today>` and read the JSON (it is small: deals, states, gaps, next questions, last interactions, trend). If it reports no active deals, say so and offer the retro instead.

## 4. Self-assessment (gate, the conscious-competence step)

Before showing any evidence, ask the rep about their top active deals (up to four deals, one question each, multi-select): "On <deal> (<company>), which of these do you believe you have established?" with options: Economic Buyer identified and engaged; Champion tested (has power and sells for you when you are not there); Metrics quantified in the buyer's words; Decision process and paper process mapped with dates. Record the answers. Compare with the pack's element levels (E, CH, M, DP and PP): note each place where the rep's belief and the evidence differ.

## 5. Write the briefing

Follow the briefing template in the coaching-voice skill. Per deal: one line on standing, the next move as a question in the rep's voice (use the pack's `nextQuestion` for the lowest applicable element, adapted to the named people), the why (quote or silence), and the self-assessment gap where one exists. One thing to practise today: the rep's weakest element from the pack, with one example phrasing for one of today's deals. Watch list from the pack (silent deals, pending links, unscored interactions). Under 350 words.

## 6. Deliver (gate)

Show the briefing. Ask: keep as is, edit (take the rep's changes), or discard. Save the kept version to `.flow-sales/briefings/<repIdSafe>/<YYYY-MM-DD>.md` (repIdSafe replaces `:` with `_`). Offer to copy it to the clipboard (`pbcopy` on macOS) so the rep can paste it wherever they keep their day. Log with `fs.py log --command standup --note "<rep> <date>"`.

Never send anything anywhere. Never show one rep another rep's briefing. No em dashes.
