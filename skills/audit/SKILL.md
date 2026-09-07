---
name: audit
description: Score every call, email, meeting and note on every deal in the window against the framework with quoted evidence, roll the scores up to deals, reps, elements and the team, and build the interactive report. The historical benchmark and the recurring audit are the same command.
disable-model-invocation: true
argument-hint: "[--sample N] [--force] [--deal <id>]"
---

You are running a FlowSales audit. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse). Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

## 1. Preflight

Run `fs.py status --json`. If there is no store, tell the user to run `/flow-sales:setup` and stop. If `interactionsUnlinked` is above zero, say so and offer to run the link skill first (recommended when the number is material); if `linksPending` is above zero, run `/flow-sales:link` before continuing. If a live source is enabled (HubSpot), ask whether to refresh it now (`fs.py pull hubspot`) or audit what is already stored.

## 2. Plan and gate on volume

Run `fs.py plan-assessment --json` (pass through `--sample N`, `--force` and `--deal <id>` from `$ARGUMENTS`). Read the totals: deals, interactions, characters and the token estimate. Present them in one short table and ask with AskUserQuestion: run the full plan, run a sample of 10 deals first (recommended above 40 deals), or narrow the window (then set `window` with `fs.py config set` and re-plan). Note the rough cost in plain terms: each interaction costs about one model call of a few thousand tokens on the user's own Claude plan; nothing is sent anywhere else.

## 3. Judge, in parallel

Read `.flow-sales/work/plan.json`. For every batch file listed, launch the plugin agent `flow-sales:deal-assessor` with the Agent tool, prompt: `Assess the batch file <absolute path>. Write the assessment to the outputFile named inside it and validate it.` Run up to the number in config `judge.parallel` (default 5) at the same time, keep launching as agents finish, and pass `model` from config `judge.model` when the Agent tool accepts it. Do not read batch bodies or assessments into your own context. Track completion by the agent replies and by the presence of the assessment files. If an agent fails, relaunch its batch once; if it fails twice, record the deal id and move on.

## 4. Roll up and report

Run `fs.py rollup --json`, then `fs.py impact --quarter <current quarter, YYYY-Qn>`, then `fs.py report --json`. Summarise in under 200 words: deals and interactions scored, team adoption rate, win rate by adoption tertile, the three weakest elements, before-and-after adoption when a training date is set, the number of influenced deals in the quarter with the rule stated, and the data coverage caveats (unlinked interactions, deals without interactions, transcripts present or not). Every number you quote must come from the analytics JSON.

## 5. Finish (gate)

Ask: open the report in the browser (`fs.py report --open`), show the path only, or run a stand-up for a rep now (`/flow-sales:standup`). Log a note with `fs.py log --command audit --note "<one line>"`.

Never write to the CRM, never send anything, never quote a score without the evidence behind it. Plain language, no em dashes.
