#!/bin/bash
# Export results.json and push it to the public data repo (github.com/eitanmeiler/opening-night-data),
# which the Opening Night page on eitanmeiler.com reads live. No-op if nothing changed.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PUB="${OPENING_NIGHT_DATA:-$HOME/Desktop/Claude Projects/Opening Night Data}"
[ -d "$PUB/.git" ] || git clone -q https://github.com/eitanmeiler/opening-night-data.git "$PUB"
git -C "$PUB" pull -q --rebase
"$ROOT/.venv/bin/python" "$ROOT/site/export_results.py" --out "$PUB/results.json" > /dev/null
# updated_utc changes every run: only publish when something other than the timestamp changed
if git -C "$PUB" diff --quiet -I '"updated_utc"' -- results.json; then
  git -C "$PUB" checkout -q -- results.json
  echo "results.json unchanged: nothing published"
  exit 0
fi
git -C "$PUB" add results.json
git -C "$PUB" commit -q -m "${1:-Update live results}"
git -C "$PUB" push -q
echo "published: $(git -C "$PUB" log -1 --format='%h %s')"
