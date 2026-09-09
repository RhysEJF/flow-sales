---
name: audit
description: Score every call, email, meeting and note on every deal in the window against the framework with quoted evidence, roll the scores up to deals, reps, elements and the team, and build the interactive report. Links new calls and meetings to their deals first and asks you only about the ambiguous ones. The historical benchmark and the recurring audit are the same command; a rerun only judges deals whose interactions changed.
disable-model-invocation: true
argument-hint: "[--sample N] [--force] [--deal <id>] [--no-link]"
---

You are running a FlowSales audit. CLI: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fs.py"` (add `--json` to parse). Plugin root: `${CLAUDE_PLUGIN_ROOT}`.

Say what is about to happen before each step, in one line, and how long it takes. Nobody should be watching a silent terminal wondering whether it is stuck.

## 1. Preflight

Run `fs.py status --json`. If there is no store, tell the user to run `/flow-sales:setup` and stop. If HubSpot is enabled, ask whether to refresh it now or audit what is already stored. Refresh on the connector route (`sources.hubspot.route` is `connector`) means the tool walk described in the setup skill, deals modified since the last pull or import in `lastRun`, saved verbatim into `.flow-sales/cache/hubspot-mcp/` and then `fs.py import hubspot-cache`; on the private-app route it is `fs.py pull hubspot --since <last pull>` (under a minute for a few hundred deals). If `me.role` is rep, offer `--owner me` (or the owner filter on the connector search) so the audit covers their own deals only.

## 2. Link (automatic, then a gate only if needed)

Run `fs.py link --json`. This attaches calls, meetings, emails and notes to deals using the CRM's own associations, attendee emails, company domains, meeting times and titles, and remembers every answer. Report one line: how many linked automatically, how many are still unlinked, how many are ambiguous (`pending`).

If anything is pending and `$ARGUMENTS` does not contain `--no-link`: run `fs.py link pending --json` and resolve the ambiguous ones now, in batches of up to four per AskUserQuestion call. For each, show the interaction's date, title, participants (names and emails) and a one-line body preview, with one option per candidate deal (deal name, company, stage, confidence as a percentage and the evidence behind it), plus "None of these, leave unlinked" and, on the last question of each batch, "Skip the rest for now". Apply each answer immediately with `fs.py link confirm <interactionId> <dealId>` or `fs.py link reject <interactionId>`. Say once that unlinked interactions are never scored and appear in the report's data coverage panel, and that `/flow-sales:link` can revisit them any time.

## 3. Plan and gate on volume

If a team folder is set (`team.folder` in the status payload), run `fs.py team sync --pull-only --json` first and say how many judged deals came in from teammates. Run `fs.py plan-assessment --json` (pass through `--sample N`, `--force` and `--deal <id>` from `$ARGUMENTS`). Read the totals: deals, interactions, characters, the token estimate, `estCostUsd` and `skipped.reusedFromTeam` (deals the team had already judged on exactly these interactions, reused for free). Present them in one short table and say plainly what the run costs: the token figure, the dollar range at list price for the judge model, and that on a Claude subscription it comes out of the plan's usage rather than a bill. Say that a rerun only judges deals whose interactions changed, so the second audit is much smaller than the first. If nothing was planned, say every deal is unchanged and skip to step 5.

Ask with AskUserQuestion: run the full plan, run a sample of 10 deals first (recommended above 40 deals), or narrow the window (then set `window` with `fs.py config set` and re-plan).

## 4. Judge, in parallel

Read `.flow-sales/work/plan.json`. Say how many batches there are, how many run at once, and the expected duration (about one minute per batch divided by the parallelism, so 32 batches at 5 in parallel is about six to eight minutes).

For every batch file listed, launch the plugin agent `flow-sales:deal-assessor` with the Agent tool, prompt: `Assess the batch file <absolute path>. Write the assessment to the outputFile named inside it and validate it.` Run up to the number in config `judge.parallel` (default 5) at the same time, keep launching as agents finish, and pass `model` from config `judge.model` when the Agent tool accepts it. Do not read batch bodies or assessments into your own context. Track completion by the agent replies and by the presence of the assessment files. After each completion print one progress line: `Judged 7 of 32 (Brightwater Logistics), about 5 minutes left`. If an agent fails, relaunch its batch once; if it fails twice, record the deal id and move on.

## 5. Roll up and report

If a team folder is set, run `fs.py team sync --push-only --json` so the deals judged here are not judged again by a teammate. Run `fs.py rollup --json`, then `fs.py impact --quarter <current quarter, YYYY-Qn>`, then `fs.py report --json`. Summarise in under 200 words: deals and interactions scored, team adoption rate, win rate by adoption tertile, the three weakest elements, before-and-after adoption when a training date is set, the number of influenced deals in the quarter with the rule stated, and the data coverage caveats (unlinked interactions, deals without interactions, transcripts present or not). Every number you quote must come from the analytics JSON.

## 6. Finish (gate)

End with the line `Report is ready at <absolute path>` and ask: open it in the browser (`fs.py report --open`), leave it there, or run a stand-up for a rep now (`/flow-sales:daily-sync`). Mention once that the Export menu in the report has a names-hidden Impact export for anyone outside the sales team. Log a note with `fs.py log --command audit --note "<one line>"`.

Never write to the CRM, never send anything, never quote a score without the evidence behind it. Plain language, no em dashes.
