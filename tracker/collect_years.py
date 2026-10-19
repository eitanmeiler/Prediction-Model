#!/usr/bin/env python3
"""Watches the clipboard while you click the 'Copy BOM table' bookmark on each year page
(https://www.boxofficemojo.com/year/YYYY/?grossesOption=totalGrosses&sort=maxNumTheaters) and saves each
year to data/raw/boxoffice/<year>.tsv. Only the In-year releases view (has 'Max Th' and 'Opening' columns)
is accepted; older calendar-view copies are replaced. Stops when 2010-2025 are all saved in that view."""
import re, subprocess, time
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "boxoffice"
YEARS = range(2010, 2026)
OUT.mkdir(parents=True, exist_ok=True)

def done(y):
    f = OUT / f"{y}.tsv"
    return f.exists() and "Max Th" in f.read_text()

def missing():
    return [y for y in YEARS if not done(y)]

def link(y):
    return f"https://www.boxofficemojo.com/year/{y}/?grossesOption=totalGrosses&sort=maxNumTheaters"

print(f"Waiting for copied tables. Still needed: {missing() or 'none'}  (Ctrl-C to stop)", flush=True)
last = ""
while missing():
    clip = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
    if clip != last and clip.startswith("#BOM_YEAR "):
        last = clip
        year = int(clip.split()[1])
        lines = [l.split("\t") for l in clip.splitlines()]
        hdr = next((l for l in lines if "Rank" in l), [])
        rows = [l for l in lines if l and l[0].strip().isdigit()]
        if "Max Th" not in hdr or "Opening" not in hdr:
            print(f"REJECTED {year}: wrong view (no Opening column). Open {link(year)}", flush=True)
        elif year not in YEARS or len(rows) < 50:
            print(f"ignored {year}: {len(rows)} rows (need a 2010-2025 page with the full table)", flush=True)
        else:
            ti = hdr.index("Max Th")
            th = [int(r[ti].replace(",", "")) for r in rows if len(r) > ti and r[ti].replace(",", "").isdigit()]
            (OUT / f"{year}.tsv").write_text(clip)
            note = f"  NOTE: smallest Max Th is {min(th)}; films between 600 and {min(th) - 1} theaters are not on the page." if th and min(th) >= 600 else ""
            print(f"saved {year} ({len(rows)} films).{note} Still needed: {missing() or 'none - all done!'}", flush=True)
    time.sleep(1)
