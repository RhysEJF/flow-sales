# Design notes: the report redesign (branch `design-sprint`, 2026-09-08)

What changed in the HTML report, why, and how to check it. Scope was the report only: `template.html`, `charts.py` and `build_report.py` under `scripts/flowsales/report/`, plus the README screenshots. Scoring, analytics, adapters, the CLI and the briefings are untouched.

## The brief

Make the report look and read like something a sales leader would pay for, on a laptop and on a phone, without leaving the product's rules: one self-contained HTML file, no network requests, no web fonts, Python 3.10 standard library, inline SVG charts that each keep a table view, light and dark, printable, no em dashes.

## What the old report was

A competent default: identical rounded cards with the same border on everything, uppercase tracked labels above every fact, middle dots joining the meta line, a near-black ink, and the "Overview" heading over a row of number tiles. On a phone the 760px line chart shrank to a third of its size and its labels became unreadable.

## The plan

- **Verdict first.** The overview opens with the sentences the sales leader will repeat, built in the page from the analytics (before and after adoption, win rate on deals closed after the training, the rep who moved most, win rate by adoption tertile, the influenced deals in the quarter), with the n kept close and an honest note that these are correlations. Each sentence has a fallback for missing data (no training date, no impact file, no tertiles) and is dropped rather than faked when its inputs are absent.
- **Type carries the identity.** Charter for the verdict, section titles, the impact slide title and every buyer quote. Charter ships with macOS and iOS; the stack falls to Sitka Text on Windows, then Cambria and Georgia. The system UI face carries everything else with tabular figures. No web fonts, so the file stays offline.
- **The element strip is the product's grammar.** The eight MEDDPICC cells in framework order, filled by the validated level ramp with the number always printed. It now appears as a mini strip in the deals table (sortable by count), as the large row on every deal page with the code key beneath it, and per interaction in the timeline. Same order, same colours, everywhere.
- **Cards only where a surface is needed.** Charts, the deals table, rep cards, element cards and the impact slide sit on white panels. Number tiles lost their boxes and gained a single top rule in the display navy. Facts are a ruled grid, not a card. Timeline items are cards on a rail.
- **One moment of motion.** The adoption lines draw themselves once when the overview first renders (`pathLength="1"` on the solid paths, a dash-offset animation in CSS; the dashed team line and the points fade in after). Tab switches cross-fade. Nothing else moves unprompted, and `prefers-reduced-motion` disables all of it.
- **The pixel signature.** The existing pixel wordmark stays the only playful thing, joined by six 8x8 pixel icons for the tabs (drawn as crisp-edged paths) that only show on phones, where the tabs become a bottom bar. The favicon is the pixel F on navy.
- **Phone charts are rendered at phone width.** `build_report.py` renders every chart twice: once at its desktop width and once at `NARROW_W` (330px, the widest chart that fits a 390px phone inside the page and figure padding). The page picks the narrow SVG under 720px and swaps on resize. Small multiples go two-up, the line chart drops its end labels (the legend still names every series), the deal heatmap uses smaller cells.
- **Phone layout.** Bottom tab bar with safe-area padding, two-up tiles, the deals table becomes a stack of cards (owner, amount, stage and rates inline; the strip and the gate chip on their own rows), key/value tables stack, quote rows stack. The header shows only the org name and the window.
- **The impact tab is the slide.** One panel with the quarter title, the four numbers, the before and after chart, the rule and the influenced deals side by side, and a footer with the window and the mark. Print it and it is the slide.
- **Three-state theme.** Light is the default palette on `:root`; the dark tokens apply under `prefers-color-scheme: dark` unless the root is stamped light, and always when stamped dark. The toggle stamps and remembers; `?theme=dark` or `?theme=light` in the URL forces one (useful for screenshots). Print always uses the light tokens.

## Filters, period, rep switcher and export (added the same day)

- **Filters on the overview.** Reps, one element ("was the framework applied for Champion"), interaction type and deal outcome. The page rebuilds the same rows the rollup used (one per judged interaction, from the assessments and interaction metadata already embedded in the file) and recomputes the tiles, adoption over time (trailing four ISO weeks), win rate by adoption tertile, before and after by rep, and interactions by type from that subset, using the rollup's own rules (applied means at least one behaviour tag; tertiles cut closed deals at n/3 and 2n/3; before and after split on the training date). With no filter set the numbers reproduce the analytics files exactly; this was checked by dumping the rendered DOM and comparing every tile, tertile label, before and after row and all 41 weeks of every adoption line against `team_metrics.json`, `rep_metrics.json` and the Python rolling window. Legend names on the adoption chart toggle reps too. The verdict is deliberately not filtered: it states the whole-window truth.
- **Period in the header.** Whole window, before training, after training, last 12 weeks, last 26 weeks, or custom dates with from and to pickers (bounded to the window). Honoured by the Overview and Reps tabs, which recompute; the other tabs show the whole window and say so in a note. The analytics files are computed by `rollup` for the configured window, so re-slicing happens in the page from the interaction rows; a shorter window changes n, not the rules.
- **Reps tab.** A sticky switcher (previous, a dropdown you can type into, next; `[` and `]` on the keyboard) replaces the chip row, and with more than six reps the tab shows one rep at a time. Every number on the card is recomputed for the period from the same rows (adoption, weekly sparkline, adoption by element, weakest and strongest three with the rollup's 3-decimal tie-break, before and after, win rate and at-close averages over deals closed in the period, evidence quality from verified level-2+ scores). Recommendations stay whole-window because they cite specific judge notes.
- **Export.** The Print button became an Export menu: Save as PDF (the print dialog, always light tokens), Download Markdown and Copy Markdown. The Markdown is generated from the rendered page, so it carries the current filters and period, every chart as its table twin, every tile, the deals table, the rep cards, the element quotes, the impact slide and the method rules. `window.flowsalesExportMarkdown()` returns the same text for scripts.
- **Percentages round half to even** in the page now, as Python's formatting does, so 62.5% reads 62% in the verdict and in the impact tile alike.

## What was checked

- Palette: the categorical, level-ramp and before/after palettes were re-run through the dataviz validator against the new surfaces (`#ffffff` light, `#161a21` dark). All checks pass; the three light hues below 3:1 keep their relief through the legend, direct labels and the table view. Results are in the comment at the top of `template.html`.
- Tests: `python3 -m unittest discover -s tests` (244 green at the time of writing). The report test still asserts a self-contained file under 1 MB for the fixture store, no network `src` or `href`, no em dash, the footer credit, and well-formed chart SVG.
- Rendering: every tab in light and dark at 1440px and 390px with the Playwright headless shell on the real demo data (32 deals, 4 reps, training 7 May 2026), plus print to PDF for the overview and the impact tab. The filters, period, rep switcher and export were exercised in a real browser through the Playwright MCP.

## Things a reviewer might ask

- **Why is the verdict computed in the page and not in Python?** It is presentation, not analytics. It reads `teamMetrics`, `repMetrics` and `impact` as they are and never recomputes a number, which keeps the builder's rule ("nothing is recomputed here") intact.
- **Why not embed a font?** The report test forbids network loads and the product promise is a file that works anywhere offline. Charter and Sitka cover macOS, iOS and Windows; Georgia is the last fallback and still reads as intended.
- **Why two SVGs per chart instead of a responsive one?** SVG text does not reflow. Rendering at two widths costs about 50 KB on the demo report and keeps every label legible on a phone; the alternative was horizontal scrolling inside every figure.
- **Size.** The demo report went from 1.28 MB to 1.48 MB, almost all of it the narrow chart variants and the deal heatmaps. The fixture report is 415 KB against the 1 MB test limit.

## Not done

- The standup and retro briefings (markdown) and the README hero image are unchanged. The README's report screenshots were regenerated from the new report and a phone and impact screenshot were added.

## Usability round one: what changed (branch `usability-fixes`)

Ten synthetic personas (AskRally GenPop, sales roles) tested the report on 2026-09-08; the analysis is in the flow-os-rhys brain under `experiences/flow-sales/usability-2026-09-08/analysis.md`. Changes made in response, in the order of the findings:

1. Point deltas (the "+25 pts" beside 62% and 38%) are now taken between the rounded figures the page prints, in the Impact tiles, the before-and-after tables and the rep cards. Same rule in Python (`_pct_points`) and in the page (`pctPts`).
2. When any filter or period is active the verdict dims and carries a "Whole window" badge; the adoption tile is named after the slice ("Adoption: Tom Ellis, after training").
3. Decayed elements get a sentence with dates under the element strip ("CO decayed from 2 to 1: last evidence 6 Apr 2026, 57 days before close, window 45 days") and the key line names the corner marker.
4. "What to fix on this deal": for every element below level 2 or behind its stage, the judge's latest "why not higher" and "ask next", above the timeline.
5. The Deals tab carries a key under the toolbar: the four gate rules with their chips, the eight element names, and what the strip shows. Column headers explain themselves on hover.
6. Evidence quality: when it is the same on every deal the column folds into one line in the key that says what it measures; otherwise it stays, with a tooltip.
7. The verdict names the divergence behind a flat average ("Behind the flat average, Tom Ellis rose 34 points while Amira Khan fell 19 points"); the Impact slide lists every rep's before-to-after change.
8. The Elements tab calls out any element that scores higher on lost deals than won, with a one-line reading.
9. Clicking a rep chip while all are selected now shows only that rep (click again for everyone); the period presets sit in the filter bar as chips, sharing the header control; the Reps switcher has an element select, so "Tom, Champion, after training" is one row on one page.
10. On phones the adoption chart starts with the team line only; legend names now hide or show a line and no longer change the numbers (the Reps filter does that).
11. The timeline strip fits on one row on a phone; the keyboard hint is hidden on phones.
12. The Impact blurb and the Export button say what the export produces; the Total fact explains itself on hover.
