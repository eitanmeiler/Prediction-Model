#!/usr/bin/env python3
"""Builds rows for upcoming releases so the live forecaster can score them with the same features.

Reads tracker/upcoming.json (title, US release date, distributor, optional opening theater count once announced),
matches each to TMDB with the same matcher as the historical films, and writes data/interim/upcoming.csv in the
films.csv + tmdb.csv layout (opening left empty).
"""
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import tmdb_enrich as tm  # noqa: E402

SRC = ROOT / "tracker" / "upcoming.json"
OUT = ROOT / "data" / "interim" / "upcoming.csv"


def main():
    tm.CACHE.mkdir(parents=True, exist_ok=True)
    items = json.loads(SRC.read_text())["films"]
    rows = []
    for it in items:
        rd = pd.Timestamp(it["release_date"])
        fid = f"{rd:%Y%m%d}_{re.sub(r'[^a-z0-9]+', '_', it['title'].lower()).strip('_')[:40]}"
        film = {"film_id": fid, "year": rd.year, "title": it["title"], "distributor": it["distributor"],
                "domestic_total": None, "max_theaters": it.get("open_theaters"), "opening": None,
                "open_theaters": it.get("open_theaters"), "release_date": rd, "bom_estimated": False,
                "rerelease": False, "event": bool(it.get("event", False)), "upcoming": True}
        if it.get("tmdb_id"):
            tm.FORCE_ID[fid] = it["tmdb_id"]
        res = tm.best_match(SimpleNamespace(film_id=fid, title=it.get("tmdb_title", it["title"]), year=rd.year,
                                            release_date=rd))
        if res and res[-1]:
            film.update(tm.flatten(fid, *res[:-1]))
        else:
            print(f"  no TMDB match for {it['title']} — add its tmdb_id to {SRC.name}")
        rows.append(film)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print(f"{len(rows)} upcoming films -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
