#!/usr/bin/env python3
"""Watches the clipboard while you click the 'Copy BOM table' bookmark on each year page, and saves every year it sees
to data/raw/boxoffice/<year>.tsv. Stops when 2010-2025 are all saved (or Ctrl-C)."""
import re, subprocess, time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "boxoffice"
YEARS = range(2009, 2026)  # 2009 only to remove its holdovers from 2010
OUT.mkdir(parents=True, exist_ok=True)

def missing():
    return [y for y in YEARS if not (OUT / f"{y}.tsv").exists()]

print(f"Waiting for copied tables. Still needed: {missing() or 'none'}  (Ctrl-C to stop)", flush=True)
last = ""
while missing():
    clip = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    if clip != last and clip.startswith("#BOM_YEAR "):
        last = clip
        year = int(clip.split()[1])
        rows = sum(1 for line in clip.splitlines() if re.match(r"^\d+\t", line))
        if year in YEARS and rows >= 50:
            (OUT / f"{year}.tsv").write_text(clip)
            print(f"saved {year} ({rows} films). Still needed: {missing() or 'none - all done!'}", flush=True)
        else:
            print(f"ignored clipboard for {year}: {rows} rows (need a 2009-2025 page with the full table)", flush=True)
    time.sleep(1)
