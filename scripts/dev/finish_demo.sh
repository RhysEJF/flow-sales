#!/usr/bin/env bash
# Second half of the demo loop, after the judge wrote the assessments: validate, roll up, impact, report.
set -euo pipefail
HOME_DIR="${1:-/tmp/fs-demo}"
QUARTER="${2:-$(python3 -c 'import datetime as d; t=d.date.today(); print(f"{t.year}-Q{(t.month-1)//3+1}")')}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FS="python3 $HERE/../fs.py --home $HOME_DIR"
fails=0
for f in "$HOME_DIR"/assessments/*.json; do
  [ -e "$f" ] || continue
  if ! $FS validate-assessment "$f" --json > /tmp/fs-validate.out 2>&1; then
    fails=$((fails+1)); echo "validation failed: $f"; head -c 600 /tmp/fs-validate.out; echo
  fi
done
echo "validation failures: $fails"
$FS rollup
$FS impact --quarter "$QUARTER"
$FS report
$FS status
