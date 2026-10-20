#!/usr/bin/env python3
"""Turns forecasts/forecast_log.csv (+ actual openings once known) into rows for the research page's live tracker.
Writes forecasts/site_rows.json: {doc_id: row}. Claude then writes them to the page's `forecasts` collection
(ArtifactData batch) — the page itself never has write access for viewers.
Page: https://claude.ai/artifact/NRT8g5q5HFdsYzPocSpkHV
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
log = pd.read_csv(ROOT / "forecasts" / "forecast_log.csv")
t = pd.read_csv(ROOT / "data" / "processed" / "model_table.csv")[["title", "release_date", "opening"]]
log = log.merge(t.dropna(subset=["opening"]).drop(columns="release_date"), on="title", how="left")
rows = {}
for r in log.itertuples():
    doc = f"{r.film_id}_{r.checkpoint}_{str(r.frozen_at_utc)[:10]}".replace(":", "")
    rows[doc] = {"title": r.title, "release_date": str(r.release_date), "checkpoint": r.checkpoint,
                 "model": r.primary_model if hasattr(r, "primary_model") else r.model,
                 "forecast_m": float(r.forecast_m), "lo80_m": float(r.lo80_m), "hi80_m": float(r.hi80_m),
                 "frozen_at_utc": r.frozen_at_utc, "git_commit": r.git_commit,
                 "actual_m": round(r.opening / 1e6, 2) if pd.notna(r.opening) else None}
(ROOT / "forecasts" / "site_rows.json").write_text(json.dumps(rows, indent=1))
print(f"{len(rows)} rows -> forecasts/site_rows.json ({sum(v['actual_m'] is not None for v in rows.values())} graded)")
