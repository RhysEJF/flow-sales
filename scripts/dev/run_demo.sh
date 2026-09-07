#!/usr/bin/env bash
# Deterministic half of the demo loop: store, demo data, links, batches.
# The judge step is done by Claude (audit skill or deal-assessor agents); then run finish_demo.sh.
set -euo pipefail
HOME_DIR="${1:-/tmp/fs-demo}"
HERE="$(cd "$(dirname "$0")" && pwd)"
FS="python3 $HERE/../fs.py --home $HOME_DIR"
$FS init
$FS import demo
$FS link
$FS status
$FS plan-assessment --json | python3 -c 'import json,sys; d=json.load(sys.stdin); t=d.get("totals",{}); print("batches:", t.get("batches"), "deals:", t.get("deals"), "interactions:", t.get("interactions"), "estTokens:", t.get("estTokens"))'
echo "batch files: $HOME_DIR/work/batches/"
