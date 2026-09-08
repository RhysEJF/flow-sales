# FlowSales handoff (2026-09-08, 00:10 Europe/Amsterdam)

This file lets a fresh Claude Code session, on a different plan, continue the FlowSales build without the previous conversation. Read it top to bottom before touching anything. Then follow "Resume here" (section 3) exactly.

## 1. What FlowSales is, in three lines

A source-available Claude Code plugin (this repo) that reads a sales team's own CRM and meeting transcripts, scores every call, email, meeting and note against MEDDPICC with verbatim buyer quotes, measures how much each rep applies the framework over time, links adoption to won and lost deals, and briefs each rep every morning. Local-first, read-only, HubSpot and Granola first. Owner: Rhys Fisher (RhysEJF). Private repo: https://github.com/RhysEJF/flow-sales.

## 2. Where things are

| What | Path |
|---|---|
| Plugin repo (this) | `~/flow-sales` (git, main, pushed; commit `567ffd6` at handoff) |
| Contracts every module follows | `~/flow-sales/docs/CONTRACTS.md` (read this before writing code) |
| Design, decisions, research summary, 17-task plan | `~/flow-os-rhys/experiences/plans/flow-sales-plugin-plan.md` (sections 14b and 15 hold the latest decisions) |
| Research docs (HubSpot API, Granola, MEDDPICC canon, landscape, licence) | `~/flow-sales/docs/research/` (copies in `~/flow-os-rhys/experiences/flow-sales/research/`) |
| Demo project directory with a live store | `~/flow-sales-demo/.flow-sales/` (32 deals, 167 linked interactions, 9 of 32 deals already judged and validated) |
| Rhys's second brain (session notes live in `brain-health/progress.md`) | `~/flow-os-rhys` |
| Logo candidates (A chosen, now `assets/hero.png`) | `~/flow-os-rhys/experiences/flow-sales/logo-candidates/` |

## 3. Resume here

The previous session was judging the demo dataset when the plan's weekly limit cut it off. The pipeline is resumable by design: `plan-assessment` only plans deals that have no validated assessment.

Preferred route (it is also the end-to-end test of the product):

```bash
cd ~/flow-sales-demo
claude --plugin-dir ~/flow-sales
```

Inside that session:

1. `/flow-sales:audit` and answer the gates: audit what is stored (no refresh), run the full plan (23 deals, about 100k input tokens of batches). The skill launches the plugin agent `flow-sales:deal-assessor` per batch, up to `judge.parallel` (5) at a time. Keep it at 5 to 8 parallel; 16 in flight is what tripped the old plan's limits.
2. When it finishes, the skill runs `rollup`, `impact` and `report`. If the skill misbehaves, fall back to the manual route below and fix the skill text (`~/flow-sales/skills/audit/SKILL.md`).
3. Open the report and check every tab on real numbers. Screenshot it (Playwright MCP blocks `file://`; serve it with `python3 -m http.server 8765 --bind 127.0.0.1` from the reports folder and screenshot `http://127.0.0.1:8765/<file>`; screenshots must be saved under the project directory). Replace `~/flow-sales/docs/screenshots/*.png` with the real-data versions.

Manual route (what the previous session did, works without the plugin being loaded):

```bash
cd ~/flow-sales-demo
python3 ~/flow-sales/scripts/fs.py plan-assessment --json     # lists the remaining batch files
```

Then, for each batch file, launch a general-purpose subagent on Sonnet with this prompt (change the batch file name):

> You are the FlowSales deal-assessor. Read /Users/rhysfishernewairblack/flow-sales/agents/deal-assessor.md and /Users/rhysfishernewairblack/flow-sales/skills/methodology/SKILL.md once, then follow that procedure exactly for the batch file /Users/rhysfishernewairblack/flow-sales-demo/.flow-sales/work/batches/<dealIdSafe>.json. The plugin root is /Users/rhysfishernewairblack/flow-sales (validator: python3 /Users/rhysfishernewairblack/flow-sales/scripts/fs.py validate-assessment <outputFile>). Write the assessment to the outputFile named in the batch, validate, fix until ok is true, and reply with the three summary lines only.

Each batch costs roughly 150k to 200k tokens on Sonnet across its turns (quality so far: 0 unverified quotes across 9 deals). After all batches: `bash ~/flow-sales/scripts/dev/finish_demo.sh ~/flow-sales-demo/.flow-sales` (validates, rolls up, computes the quarter's impact, builds the report).

## 4. What is done (all tests green: `cd ~/flow-sales && python3 -m unittest discover -s tests`, 232 tests)

- Plugin manifest, marketplace manifest, `.mcp.json` (HubSpot remote at `https://mcp.hubspot.com/anthropic`, unverified path; Granola remote at `https://mcp.granola.ai/mcp`, verified).
- Licence set: `LICENSE.md` (ELv2-derived "FlowSales Source-Available License 1.0"), `LICENSE-FAQ.md`, `COMMERCIAL.md`. README, INSTALL, `docs/privacy.md`, `docs/hubspot.md`, `docs/granola.md`, `docs/other-crms.md`.
- Core CLI `scripts/fs.py` with every command in CONTRACTS section 10: init, config, status, log, doctor, pull hubspot, import demo/csv/granola/transcripts, link (run/pending/confirm/reject), plan-assessment, validate-assessment (quote verification), rollup, impact, report, briefing-data, retro-data.
- Adapters: HubSpot REST client and pull (mock-tested only, never run against a live portal), HubSpot seeder for test accounts, Granola (export dir, public API, legacy cache with the encrypted-cache message), CSV, transcripts folder, demo dataset (Northwind Analytics, 4 reps, training date 4 months before window end).
- Methodology: `frameworks/meddpicc.json`, `frameworks/meddic.json`, `skills/methodology/SKILL.md`, golden set `evals/golden/` (40 labelled snippets; no harness runs them yet).
- Skills: setup, link, audit, standup, retro, impact, coaching-voice, methodology. Agent: `agents/deal-assessor.md`. `claude --plugin-dir ~/flow-sales plugin details flow-sales` shows 8 skills, 1 agent, 2 MCP servers, about 740 always-on tokens.
- Report builder (`scripts/flowsales/report/`): six tabs, inline SVG charts from the dataviz palette, light and dark, table views, licence footer. Screenshots from fixture data in `docs/screenshots/`.
- Analytics (`scripts/flowsales/analytics/`): deal states, rep and team metrics, timeseries, impact, briefing and retro packs.

## 5. What remains (in order)

1. Finish the demo judge run (23 deals) and rebuild the report on real numbers; fix anything the real data breaks in rollup, packs or the report; replace the screenshots; commit and push.
2. Run `/flow-sales:standup Tom Ellis` and `/flow-sales:retro Tom Ellis` in the demo project; fix the skills where the flow is clumsy (they have never been exercised end to end). Tom Ellis is the rep whose adoption rises after the training date.
3. Run `/flow-sales:impact` for the current quarter and read the markdown it produces.
4. `claude plugin validate ~/flow-sales`; install test from the marketplace in a clean directory (`/plugin marketplace add RhysEJF/flow-sales`, `/plugin install flow-sales@flow-sales`); note that `userConfig` for the HubSpot token is not in `plugin.json` yet (the token is read from the env var, the plugin option env var, or `secrets.json`; add `userConfig` if `claude plugin validate` and the docs confirm the field).
5. Evals: a small harness that runs the judge on `evals/golden/snippets.json` and reports agreement (targets in `evals/golden/README.md`); `claude plugin eval` cases if the CLI has it enabled.
6. HubSpot live test: needs a token from Rhys (`/setkey HUBSPOT_ACCESS_TOKEN` in the brain, or an env var). Private-app creation leaves the HubSpot UI on 2026-09-28 (new accounts) and 2026-10-26 (existing); after that it is a Service Key. Then `doctor`, `pull hubspot`, and `seed_hubspot.py` into a developer test account. Verify the remote MCP sign-in path.
7. Granola live test: sign in with `/mcp` in a session where the plugin is loaded, export a few meetings following `docs/granola.md`, `import granola`, `link`.
8. Before any public release: `~/flow-os-rhys/experiences/solutions/public-repo-security-audit-checklist.md`, tag `v0.1.0`.
9. In the brain: update `brain-health/progress.md` and run `/learn` at the end of the session.

Decisions still with Rhys: HubSpot token (item 6) and whether Tom Parker becomes a rubric reviewer and pilot user or is only informed at release (nothing goes to Tom from this build without Rhys saying so).

## 6. Conventions and gotchas

- Python 3.10+ standard library only. No em dashes anywhere in shipped text (Rhys reads them as AI slop). Plain English, short sentences.
- CONTRACTS.md is the source of truth; change it first, then the code. Every command logs to `.flow-sales/runs.jsonl`.
- `fs.py` accepts `--home` and `--json` before or after the subcommand.
- Quote verification: scores above 1 without a verifiable quote are capped to 1 and flagged; the judge copies exact spans from `body`.
- Playwright MCP: no `file://`; serve over localhost; screenshot paths must be inside the project directory.
- `validate-assessment` now logs into the store the assessment file belongs to even when run from another directory (fixed at handoff; earlier judge runs left a stray `.flow-sales/runs.jsonl` in whatever directory they ran from).
- Quota: the old plan hit a 5-hour session limit with 7 parallel build agents and then the weekly limit with 16 parallel Sonnet judges. Run judges in waves of at most 8 and check for 429s in agent results.
- Models used previously: orchestrator Claude Fable 5.1 (`claude-fable-5-1`, effort max); research and build subagents on the same model; judge subagents on Claude Sonnet 5 (`claude-sonnet-5`), which the deal-assessor agent pins with `model: sonnet`. Any capable model works for orchestration; keep Sonnet or better for judging.
- Time zone: Rhys is in Europe/Amsterdam.

## 7. If something looks wrong

Check `~/flow-sales-demo/.flow-sales/runs.jsonl` for what ran, `work/plan.json` for what is planned, and `assessments/` for what is judged. `git log` in `~/flow-sales` shows the build order. The previous session's plan file has a section per subsystem with the reasoning behind each choice.
