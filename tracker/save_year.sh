#!/bin/bash
# Usage: tracker/save_year.sh 2010
# Saves the Box Office Mojo yearly table you just copied (clipboard) to data/raw/boxoffice/<year>.tsv and checks it.
set -e
Y="$1"; [[ "$Y" =~ ^20(1[0-9]|2[0-5])$ ]] || { echo "Give a year 2010-2025"; exit 1; }
OUT="$(cd "$(dirname "$0")/.." && pwd)/data/raw/boxoffice/$Y.tsv"
pbpaste > "$OUT"
rows=$(grep -cE $'^[0-9]+\t' "$OUT" || true)
grep -q "Release Date" "$OUT" || echo "WARNING: header row not found - did you copy the whole table, starting at 'Rank'?"
grep -q "$Y" "$OUT" || echo "WARNING: no dates from $Y in the paste - wrong year page?"
echo "saved $Y: $rows film rows -> data/raw/boxoffice/$Y.tsv"
[ "$rows" -ge 150 ] || echo "WARNING: fewer than 150 rows - the page shows up to 200; copy all of it."
