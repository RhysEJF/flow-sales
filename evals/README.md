# Evals

- `golden/`: the labelled snippet set and the judge comparison run by `fs.py eval-golden` (see `golden/README.md`).
- `cases/`: `claude plugin eval` cases (`prompt.md` plus `graders/*.md`). Run from the repo root with
  `claude plugin eval . --runs 1 --allow-tools Bash --no-publish`; results land in `evals/results/` (gitignored).
  As of 2026-09-08 (Claude Code 2.1.263) `plugin eval` is early access and prints `plugin eval is currently in early access` on this account, so the cases are written but unrun.
