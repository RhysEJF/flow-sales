<p align="center">
  <img src="./assets/hero.png" alt="FlowSales: a pixel-art sales rep walking a glowing pipeline of checked deal cards" width="900">
</p>

# FlowSales

> Sales methodology as a system of record, not a training you attended.

FlowSales is a Claude Code plugin that reads your own CRM and meeting transcripts, scores every call, email, meeting and note against MEDDPICC with the buyer's exact words as evidence, measures how much each rep actually applies the framework week by week, ties adoption to won and lost deals, and briefs every rep each morning. It runs inside your Claude Code, on your machine, read-only. Nothing leaves except the model calls your session already makes.

Six commands. One loop. Source-available. Installed and running on the demo in about twenty minutes by whoever runs your CRM.

## The loop

```
  /flow-sales:setup     connect HubSpot, Granola, a folder of Gong or Fireflies or Fathom
        |               transcripts, or a CSV export from Salesforce or any other CRM;
        |               agree who sees the report and what may be read; pick the framework,
        |               the window, the reps, the training date
        |
  /flow-sales:audit     link every call and meeting to its deal (asks you only about the
        |               ambiguous ones), score every interaction with quoted evidence, roll
        |               up to deals, reps, elements and team, build the report
        |
  /flow-sales:standup   one rep, one morning: say where each live deal stands, then see the
        |               evidence, the next framework move per deal, one thing to practise
        |
  /flow-sales:retro     one rep, one week: adoption vs last week and the team, deals moved,
        |               wins and losses explained by element, the focus for next week
        |
  /flow-sales:impact    one quarter: adoption before and after training, win rate by adoption,
        |               the won deals that followed framework actions, the rule beside each number
        |
  /flow-sales:status    is it working: token, data, what is ambiguous, when each step last ran,
                        what the next audit would judge and cost. Reads, never writes.
```

Run `audit` once for the historical benchmark, then `standup` daily and `retro` weekly. `impact` is the slide. `status` is the thing to run when in doubt. A rerun of `audit` only judges deals whose interactions changed.

## Why

Sales teams buy methodology training and measure it by who joined the sessions. Three months later nobody can say whether reps ask for the Economic Buyer more often, whether the deals with a tested Champion close faster, or whether the training moved anything at all. Every vendor tool that scores calls does it inside a black box that uses its own idea of the methodology, and the rep sees a number instead of their own words.

FlowSales does the boring part properly. The rubric is a file you can read and edit. Every score above "mentioned" carries a verbatim quote, and a validator checks the quote exists before the score counts. Adoption is measured on what the rep did (asked the question, tested the champion), separately from what the deal shows. The rep self-assesses before seeing the evidence, because conscious use of a competency is what training is for. And the numbers that matter for a leader (adoption over time, win rate by adoption, deals influenced) come out of your own pipeline with the rule printed next to them.

## Install

This page is for whoever runs your CRM or sales operations. It takes about twenty minutes, most of it watching the demo audit run. Reps install nothing; they get the report and their morning briefings.

### 1. Check your machine (one paste)

Open a terminal (Terminal on a Mac, any shell on Linux) and paste the whole block. Three lines come back, each saying ok or what to do next.

```bash
claude --version >/dev/null 2>&1 && echo "Claude Code: ok" || echo "Claude Code: not found. Install it first: https://docs.claude.com/en/docs/claude-code/quickstart"
python3 -c 'import sys; v=sys.version_info; print("Python: ok" if v>=(3,10) else "Python: %d.%d found, need 3.10 or newer: https://www.python.org/downloads/" % v[:2])' 2>/dev/null || echo "Python: not found. Install 3.10 or newer: https://www.python.org/downloads/"
git ls-remote -q https://github.com/RhysEJF/flow-sales.git HEAD >/dev/null 2>&1 && echo "GitHub access: ok" || echo "GitHub access: no. The repo is private: ask Rhys to add your GitHub account, then sign in in this terminal (gh auth login) and paste again"
```

Nothing else is needed. FlowSales is standard-library Python; there are no packages to install. macOS and Linux are tested. Windows is not tested yet: the same commands should work in PowerShell with `python` in place of `python3`, and if they do not, say so and it will be fixed.

### 2. Install the plugin (inside Claude Code)

Start Claude Code by typing `claude` in the terminal, then paste these two lines one at a time:

```
/plugin marketplace add RhysEJF/flow-sales
/plugin install flow-sales@flow-sales
```

Each one answers in a second or two. Then type `/flow-sales:` and the six commands appear in the list. That is the sign you are in.

### 3. See it work on fictional data (about eight minutes)

Make an empty folder for FlowSales to keep its files in and open Claude Code there:

```bash
mkdir -p ~/flowsales-demo && cd ~/flowsales-demo && claude
```

Then run, one after the other:

```
/flow-sales:setup --demo
/flow-sales:audit
```

`setup --demo` takes a few seconds: it creates a `.flow-sales` folder in that directory and loads 32 fictional deals, 4 reps and a training date halfway through the window. It asks nothing.

`audit` links the calls to the deals, tells you how many interactions it is about to score and roughly what that costs, and asks you once to confirm. Then five judges score about 160 interactions in parallel, printing a progress line as each deal finishes (about six to eight minutes on the demo), and it ends with `Report is ready at <path>` and offers to open it in your browser.

After that: `/flow-sales:standup Tom Ellis` for one rep's morning, `/flow-sales:impact` for the quarter, `/flow-sales:status` to see the state of everything.

### 4. Connect your own data

Make a new folder for the real thing and run `/flow-sales:setup` without `--demo`. Before it connects anything it asks whether the reps have been told and who will see the report, then which sources to use. Have these to hand:

- **HubSpot**: a private app with six read scopes, created by your HubSpot admin in about five minutes; [docs/hubspot.md](docs/hubspot.md) has the exact page and scopes. HubSpot does not hand over call transcripts, so pair it with one of the next two.
- **Granola**: sign in from Claude Code with `/mcp` when setup asks; [docs/granola.md](docs/granola.md).
- **A folder of call transcripts** exported from Gong, Fireflies, Fathom or Google Meet.
- **Salesforce, Pipedrive or any other CRM**: a two-file CSV export; [docs/other-crms.md](docs/other-crms.md). The report is the same.

Developers who want to work on the plugin itself: [INSTALL.md](INSTALL.md) covers the local checkout.

## What the report looks like

The overview opens with the verdict: the sentences a sales leader repeats, built from your own pipeline with the n beside each number. Under it: adoption over time with the training date marked, win rate by adoption tertile, before and after training per rep, and the data coverage the numbers rest on.

<p align="center"><img src="./docs/screenshots/report-overview.png" alt="FlowSales report overview: the verdict, four figures and adoption over time" width="900"></p>

Every deal is a row with its eight element levels, its gate and the adoption behind it, and every deal has a page: the element levels, stage gaps, and the interaction timeline with the evidence level and the behaviour mark per element, expandable to the quotes, the "why not higher" and the next question.

<p align="center"><img src="./docs/screenshots/report-deals.png" alt="FlowSales deals table with the element strip per deal" width="900"></p>
<p align="center"><img src="./docs/screenshots/report-deal-page.png" alt="FlowSales deal page with the interaction timeline" width="900"></p>

The impact tab is the slide: one quarter, four numbers, the before and after chart and the rule beside them. Filters on the overview (reps, one element, interaction type, deal outcome) and a period control in the header recompute the charts from the interaction-level data in the file. The Export menu saves the report as PDF or Markdown, and has two exports that can leave the sales team: the Impact slide with rep names hidden, and one rep's own page on its own. The whole report works on a phone, with charts rendered at phone width and the tabs as a bottom bar.

<p align="center"><img src="./docs/screenshots/report-impact.png" alt="FlowSales impact slide" width="900"></p>
<p align="center"><img src="./docs/screenshots/report-phone.png" alt="FlowSales report on a phone" width="300"></p>

## Your data

- **HubSpot**: a private app with six read scopes; see [docs/hubspot.md](docs/hubspot.md). Deals, stage history, contacts, companies, calls, emails, meetings and notes come through the REST API. HubSpot does not expose call transcripts reliably through its API, so pair it with Granola or a transcripts folder for the calls themselves.
- **Granola**: the official Granola MCP server (all plans, sign in from Claude Code) or the public API (Business and Enterprise); see [docs/granola.md](docs/granola.md).
- **Transcripts folder**: Gong, Fireflies, Fathom and Google Meet exports as `.md`, `.txt`, `.vtt` or `.json`.
- **Any other CRM**: a two-file CSV export; see [docs/other-crms.md](docs/other-crms.md), which also explains how to write an adapter.

## The commands

| Command | Reads | Writes |
|---|---|---|
| `/flow-sales:setup` | your answers, the sources you connect | `.flow-sales/config.json`, cached source data, canonical deals and interactions |
| `/flow-sales:audit` | every interaction in the window, the framework file; links new ones to deals first and asks about the ambiguous ones | `.flow-sales/data/links.json`, one assessment file per deal, the analytics files, `reports/flowsales-<date>.html` |
| `/flow-sales:standup` | the rep's active deals, their assessments, the rep's answers | `briefings/<rep>/<date>.md` |
| `/flow-sales:retro` | the rep's week, their assessments | `retros/<rep>/<week>.md` and, if the rep chooses, a manager summary |
| `/flow-sales:impact` | the analytics, the training date, the influence rule | `analytics/impact-<quarter>.json` and `.md` |
| `/flow-sales:status` | everything above | nothing but a line in the runs log |

`/flow-sales:link` still exists for fixing or re-checking which calls belong to which deal without scoring anything; audit runs the same step itself.

Everything lives under `.flow-sales/` in the directory you run Claude Code in. Delete the folder and FlowSales forgets everything, so back it up like any other folder if the history matters. Every command appends a line to `.flow-sales/runs.jsonl` saying what it read and wrote.

Cost: audit prints the token count and a dollar range at list price before it starts (the demo is about $3 to $5 on Sonnet), and a rerun only judges deals whose interactions changed. On a Claude subscription the tokens come out of the plan's usage rather than a bill.

## How scoring works

The framework lives in [frameworks/meddpicc.json](frameworks/meddpicc.json) (MEDDIC in `meddic.json`). For each interaction the judge scores every element that is fair to score at that stage on a 0 to 3 evidence ladder:

| Level | Meaning |
|---|---|
| 0 | nothing in the text |
| 1 | the rep asserts or infers it; a title or an org chart; the buyer said nothing specific |
| 2 | the buyer stated it, specifically enough to act on, one source |
| 3 | confirmed by a second buyer-side person, a buyer artefact, or a buyer action |

Above level 1 the judge must quote the exact words and name the speaker. A validator checks the quote against the source text; if it cannot find it, the score drops to 1 and the element is flagged. Separately, each element gets a behaviour flag: did the rep visibly apply the framework here (asked a metrics question, tested the champion, mapped the paper process). Adoption is measured on behaviour. Deal health is measured on evidence. They are different things and the report keeps them apart.

Deal level: each element takes its best verified level, decaying one step when the last supporting evidence is older than the decay window (45 days unless setup was told your sales cycle is longer). Coverage is the count of elements at level 2 or more. Gates (commit-eligible, upside, pipeline, qualify-out) follow published MEDDPICC practice and are stated in the report's "How this is scored" tab.

The judge is the `deal-assessor` agent in [agents/deal-assessor.md](agents/deal-assessor.md); the rules it follows are in [skills/methodology/SKILL.md](skills/methodology/SKILL.md). Change the file, change the judge.

## What "attributable" means here

FlowSales never says the framework caused a deal. It says:

- **Adoption over time** per rep and per element, weekly, with the training date marked.
- **Win rate by adoption tertile**, cycle length and deal size by tertile, over closed deals, with n.
- **Before and after training**: adoption lift per rep, win rate for deals closed before and after, same reps, with the caveat that the after-period is younger.
- **Deals influenced this quarter**: a won deal counts when at least 3 framework behaviours happened across at least 2 interactions after the training date and at least one element moved from 0 or 1 to 2 or 3 in one of them. The threshold is yours to change and is printed next to the number.
- **Coverage at a fixed stage** (end of discovery, end of evaluation) against eventual outcome, because coverage rises with stage and the honest comparison holds stage constant.

Correlation, stated as such, from your own data, reproducible from open code.

## Privacy and control

Read-only scopes. Local state. No server. The interactions FlowSales scores go to the model through your own Claude Code session and nowhere else. Transcripts stay in `.flow-sales/` on your disk. Optional anonymisation replaces contact and company names before judging. The runs log shows every read and write. The kill switch is `/plugin disable flow-sales` or deleting `.flow-sales/`. Nothing runs unless you type a command: the plugin ships no hooks.

## Licence

FlowSales is **source-available**: the code is public and free to use, modify and share, including in production inside companies and by their sales teams, under the FlowSales Source-Available License 1.0 (based on the Elastic License 2.0). It is not open source under the OSI definition: you cannot sell it, embed it in a paid product, offer it as a hosted service, or remove the FlowSales branding without a commercial licence. See [LICENSE.md](LICENSE.md), the [licence FAQ](LICENSE-FAQ.md) and [COMMERCIAL.md](COMMERCIAL.md).

| What you want to do | Free under FlowSales-SAL-1.0 | Commercial licence |
|---|---|---|
| Run it in production for your own company, including your sales team | Yes | Yes |
| Modify the code and keep your changes private | Yes | Yes |
| Share copies or your fork with anyone, free of charge | Yes, keep the licence and the branding | Yes |
| Have contractors or agencies run it on your behalf | Yes | Yes |
| Share or sell what you create with it (reports, briefings, data) | Yes, output is yours | Yes |
| Paid consulting, setup, training or support on a customer's own instance | Yes | Yes |
| Bundle or embed it in a product or service you charge for | No | Yes |
| Offer it to others as a hosted or managed service | No | Yes |
| Remove or hide the FlowSales logo, name or "Powered by" notice | No | Yes, on request |
| Use the FlowSales name or logo as your own brand | No | Separate trademark licence |

Built by [Rhys Fisher](https://github.com/RhysEJF). FlowScout, the research sibling of this plugin, lives at [github.com/RhysEJF/flowscout](https://github.com/RhysEJF/flowscout).
