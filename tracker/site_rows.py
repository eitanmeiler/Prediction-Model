#!/usr/bin/env python3
"""Rows for the research page's live tracker and Amendment 8 scorecard, one per film.
Built from site/export_results.py (same grading as the public site), so both pages always agree.
Writes forecasts/site_rows.json: {doc_id: row}. Claude then writes them to the page's `forecasts` collection
(ArtifactData batch) — the page itself never has write access for viewers.
Page: the living research page (site/opening_night.html)
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory() as d:
    out = Path(d) / "results.json"
    subprocess.run([sys.executable, str(ROOT / "site/export_results.py"), "--out", str(out)],
                   check=True, stdout=subprocess.DEVNULL)
    res = json.loads(out.read_text())

rows = {}
for f in res["films"]:
    if f["status"] == "upcoming":  # drafts not yet locked are not shown
        continue
    o, h, a, g = f["ours"], f.get("hollywood") or {}, f.get("actual") or {}, f.get("grade") or {}
    m = o.get("matched") or {}
    doc = re.sub(r"[^a-z0-9]+", "_", f"{f['release_date']}_{f['title']}".lower()).strip("_")
    rows[doc] = {
        "title": f["title"], "release_date": f["release_date"], "checkpoint": f["checkpoint"], "kind": f["kind"],
        "model": o.get("model"), "frozen_at_utc": f.get("locked_at_utc"), "git_commit": f.get("git_commit"),
        "forecast_m": o["forecast_m"], "lo80_m": o["low_m"], "hi80_m": o["high_m"],
        "matched_lo_m": m.get("low_m"), "matched_hi_m": m.get("high_m"),
        "hw_lo_m": h.get("low_m"), "hw_hi_m": h.get("high_m"), "hw_mid_m": h.get("mid_m"), "hw_source": h.get("source"),
        "combined_m": (f.get("combined") or {}).get("forecast_m"),
        "actual_m": a.get("m"), "actual_status": a.get("status"),
        "provisional": g.get("provisional"), "side_case": bool(f.get("side_case")),
    }
(ROOT / "forecasts" / "site_rows.json").write_text(json.dumps(rows, indent=1))
print(f"{len(rows)} rows -> forecasts/site_rows.json ({sum(v['actual_m'] is not None for v in rows.values())} graded)")
