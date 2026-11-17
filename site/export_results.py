#!/usr/bin/env python3
"""Build results.json for the public live-season page (Opening Night vs. Hollywood vs. actual).

Inputs (all in this repo):
  forecasts/forecast_log.csv          frozen forecasts (never edited); latest pre-release T-7 row per film wins
  live_season/drafts_2026-10-23.csv   the Oct 23 films, which were only ever drafts (T-7 freeze missed)
  live_season/industry.csv            Hollywood's last pre-release forecast per film (source, date, URL)
  live_season/actuals.csv             opening weekends (status: saturday_projection | sunday_estimate | bom_actual)
  forecasts/latest_draft.csv          drafts for films opening in the next 14 days (shown as "upcoming")

Miss = |actual / forecast - 1| (the paper's "typical miss"). Hollywood's forecast = the midpoint of its range.
Usage: .venv/bin/python site/export_results.py --out <path/to/results.json>
"""
import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FINAL = {"sunday_estimate", "bom_actual"}
V2_FACTOR = 1.37  # must match models/forecast_live.py (Amendment 7)
A7_START = "2026-11-11"  # Amendment 7: v2 and Combined are locked and scored from these openings on
A8_START = "2026-11-18"  # Amendment 8: equal-width range test; clean set starts with these openings
SIDE_CASES = {"Wild Horse Nine"}  # limited releases, outside the model's population (HYPOTHESES.md): shown, not scored


def num(x, nd=1):
    return None if pd.isna(x) else round(float(x), nd)


def load_ours():
    rows = []
    log = ROOT / "forecasts/forecast_log.csv"
    if log.exists():
        f = pd.read_csv(log)
        f["rank"] = f.checkpoint.map({"T-7": 0, "T-28": 1})
        f = f.sort_values(["rank", "frozen_at_utc"], ascending=[True, False]).drop_duplicates(["title", "release_date"])
        f["kind"] = "locked"
        rows.append(f)
    d = pd.read_csv(ROOT / "live_season/drafts_2026-10-23.csv")
    d["kind"] = "draft"
    rows.append(d)
    out = pd.concat(rows, ignore_index=True)
    return out.drop_duplicates(["title", "release_date"], keep="first")


def days_before(stamp, release):
    """Days between a forecast's date and release; None if the date is only a month (e.g. '2026-10')."""
    s = str(stamp)[:10]
    try:
        return (date.fromisoformat(str(release)[:10]) - date.fromisoformat(s)).days
    except ValueError:
        return None


def matched_range(forecast, h_low, h_high):
    """Amendment 8: a range with Hollywood's relative width (high/low), centred on our forecast on the log scale."""
    if not forecast or not h_low or not h_high or h_low <= 0:
        return None
    half = (h_high / h_low) ** 0.5
    return {"low_m": num(forecast / half), "high_m": num(forecast * half), "width_ratio": num(h_high / h_low, 2)}


def miss(actual, forecast):
    return None if actual is None or forecast in (None, 0) else round(abs(actual / forecast - 1) * 100, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ours = load_ours()
    ind = pd.read_csv(ROOT / "live_season/industry.csv")
    act = pd.read_csv(ROOT / "live_season/actuals.csv")
    key = lambda r: (r["title"], str(r["release_date"]))
    ind_by = {key(r): r for _, r in ind.iterrows()}
    act_by = {key(r): r for _, r in act.iterrows()}

    v2_by = {}
    dr_all = ROOT / "forecasts/latest_draft.csv"
    if dr_all.exists() and "v2_forecast_m" in pd.read_csv(dr_all, nrows=0).columns:
        for _, r in pd.read_csv(dr_all).iterrows():
            v2_by[(r.title, str(r.release_date)[:10])] = (r, "retro")
    lv2 = ROOT / "forecasts/forecast_log_v2.csv"
    if lv2.exists():
        l = pd.read_csv(lv2)
        l["rank"] = l.checkpoint.map({"T-7": 0, "T-28": 1})
        for _, r in l.sort_values(["rank", "frozen_at_utc"], ascending=[False, True]).iterrows():
            v2_by[(r.title, str(r.release_date)[:10])] = (r, "locked")  # later rows win: the T-7 row, newest
    films = []
    for _, r in ours.iterrows():
        k = key(r)
        f = {"title": r.title, "release_date": str(r.release_date), "checkpoint": r.checkpoint,
             "locked_at_utc": r.frozen_at_utc, "kind": r.kind,
             "ours": {"forecast_m": num(r.forecast_m), "low_m": num(r.lo80_m), "high_m": num(r.hi80_m),
                      "model": r.primary_model if "primary_model" in r and pd.notna(r.get("primary_model")) else r.model}}
        h = ind_by.get(k)
        if h is not None:
            f["hollywood"] = {"source": h.source, "published": str(h.published), "low_m": num(h.low_m),
                              "high_m": num(h.high_m), "mid_m": num((h.low_m + h.high_m) / 2), "url": h.url,
                              "note": None if pd.isna(h.notes) else h.notes,
                              "days_before": days_before(h.published, r.release_date)}
            f["ours"]["matched"] = matched_range(f["ours"]["forecast_m"], h.low_m, h.high_m)
        f["ours"]["days_before"] = days_before(r.frozen_at_utc, r.release_date)
        vk = v2_by.get(k)
        if vk is not None:
            v, how = vk
            if how == "locked":
                f["v2"] = {"forecast_m": num(v.v2_forecast_m), "low_m": num(v.v2_lo80_m), "high_m": num(v.v2_hi80_m),
                           "adjusted": bool(v.v2_adjusted), "basis": "locked"}
            else:  # retro: apply the Amendment 7 rule to the forecast that was actually locked (or drafted) for this film
                fx = V2_FACTOR if bool(v.v2_adjusted) else 1.0
                o = f["ours"]
                f["v2"] = {"forecast_m": num(o["forecast_m"] * fx), "low_m": num(o["low_m"] * fx),
                           "high_m": num(o["high_m"] * fx), "adjusted": bool(v.v2_adjusted), "basis": "retro"}
        if "hollywood" in f and f["ours"]["forecast_m"]:
            f["combined"] = {"forecast_m": num((f["ours"]["forecast_m"] * f["hollywood"]["mid_m"]) ** 0.5),
                             "basis": "locked" if str(r.release_date) >= A7_START else "retro"}
        a = act_by.get(k)
        if a is not None:
            av = float(a.actual_m)
            f["actual"] = {"m": num(av, 2), "theaters": None if pd.isna(a.theaters) else int(a.theaters),
                           "status": a.status, "source": a.source, "url": a.url, "as_of": str(a.as_of)}
            hm = f.get("hollywood", {}).get("mid_m")
            om, hi_err = miss(av, f["ours"]["forecast_m"]), miss(av, hm)
            f["grade"] = {"our_miss_pct": om, "hollywood_miss_pct": hi_err,
                          "in_our_range": f["ours"]["low_m"] <= av <= f["ours"]["high_m"],
                          "in_hollywood_range": None if hm is None else f["hollywood"]["low_m"] <= av <= f["hollywood"]["high_m"],
                          "in_our_matched_range": None if not f["ours"].get("matched") else
                              f["ours"]["matched"]["low_m"] <= av <= f["ours"]["matched"]["high_m"],
                          "closer": None if hi_err is None else ("ours" if om < hi_err else "hollywood" if hi_err < om else "tie"),
                          "provisional": a.status not in FINAL,
                          "v2_miss_pct": miss(av, f.get("v2", {}).get("forecast_m")),
                          "combined_miss_pct": miss(av, f.get("combined", {}).get("forecast_m"))}
            f["status"] = "graded"
        else:
            f["status"] = "awaiting_results"
        f["side_case"] = r.title in SIDE_CASES
        films.append(f)

    # drafts for films opening in the next 14 days that are not locked yet
    today = date.today()
    dr = ROOT / "forecasts/latest_draft.csv"
    have = {(f["title"], f["release_date"]) for f in films}
    if dr.exists():
        for _, r in pd.read_csv(dr).iterrows():
            rd = date.fromisoformat(str(r.release_date)[:10])
            if today < rd <= today + timedelta(days=14) and (r.title, str(r.release_date)[:10]) not in have:
                films.append({"title": r.title, "release_date": str(r.release_date)[:10], "checkpoint": r.checkpoint,
                              "kind": "draft", "status": "upcoming",
                              "ours": {"forecast_m": num(r.forecast_m), "low_m": num(r.lo80_m), "high_m": num(r.hi80_m),
                                       "model": r.primary_model}})

    films.sort(key=lambda f: (f["release_date"], f["title"]))
    g = [f for f in films if f["status"] == "graded" and not f.get("side_case")]
    gh = [f for f in g if f["grade"]["hollywood_miss_pct"] is not None]
    med = lambda xs: None if not xs else round(float(pd.Series(xs).median()), 1)
    summary = {
        "films_graded": len(g),
        "films_graded_final": sum(not f["grade"]["provisional"] for f in g),
        "our_median_miss_pct": med([f["grade"]["our_miss_pct"] for f in g]),
        "hollywood_median_miss_pct": med([f["grade"]["hollywood_miss_pct"] for f in gh]),
        "in_our_80pct_range": sum(f["grade"]["in_our_range"] for f in g),
        "head_to_head": {"ours": sum(f["grade"]["closer"] == "ours" for f in gh),
                         "hollywood": sum(f["grade"]["closer"] == "hollywood" for f in gh),
                         "tie": sum(f["grade"]["closer"] == "tie" for f in gh)},
    }
    a7 = [f for f in g if f["release_date"] >= A7_START and f.get("combined", {}).get("basis") == "locked"]
    summary["amendment7"] = {
        "since": A7_START, "films": len(a7),
        "median_miss_pct": {"v1": med([f["grade"]["our_miss_pct"] for f in a7]),
                            "v2": med([f["grade"]["v2_miss_pct"] for f in a7 if f["grade"]["v2_miss_pct"] is not None]),
                            "combined": med([f["grade"]["combined_miss_pct"] for f in a7]),
                            "hollywood": med([f["grade"]["hollywood_miss_pct"] for f in a7])},
        "note": "Pre-registered 2026-11-08 (HYPOTHESES.md Amendment 7). Films before this date show v2/Combined as 'retro' only.",
    }
    def fair(fs):
        fs = [f for f in fs if f["grade"]["hollywood_miss_pct"] is not None]
        om, hm = med([f["grade"]["our_miss_pct"] for f in fs]), med([f["grade"]["hollywood_miss_pct"] for f in fs])
        cm = [f["grade"]["combined_miss_pct"] for f in fs if f["grade"]["combined_miss_pct"] is not None]
        return {"films": len(fs),
                "equal_width_hits": {"ours": sum(bool(f["grade"]["in_our_matched_range"]) for f in fs),
                                     "hollywood": sum(bool(f["grade"]["in_hollywood_range"]) for f in fs)},
                "closer": {"ours": sum(f["grade"]["closer"] == "ours" for f in fs),
                           "hollywood": sum(f["grade"]["closer"] == "hollywood" for f in fs)},
                "median_miss_pct": {"ours": om, "hollywood": hm, "combined": med(cm)},
                "gap_ratio": None if not om or not hm else round(om / hm, 2),
                "combined_beats_hollywood": None if not cm or hm is None else med(cm) < hm}
    summary["amendment8"] = {
        "since": A8_START,
        "clean": fair([f for f in g if f["release_date"] >= A8_START]),
        "retro": fair([f for f in g if f["release_date"] < A8_START]),
        "note": "Pre-registered 2026-11-17 (HYPOTHESES.md Amendment 8). Equal-width test: our forecast given "
                "Hollywood's range width. Films before Nov 18 are retro, outside the clean totals.",
    }
    out = {
        "project": "Opening Night: what predicts a box office opening now?",
        "author": "Eitan Meiler",
        "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "how_to_read": {
            "ours": "Model forecast of the US opening weekend (Fri-Sun incl. previews), locked in before release. "
                    "The 80% range should contain about 8 of every 10 actual openings.",
            "hollywood": "Boxoffice Pro's last published pre-release forecast range; its midpoint is used for scoring.",
            "miss": "|actual / forecast - 1|, in percent.",
            "draft": "The Oct 23 films were scored on drafts committed Oct 20 (the one-week lock-in did not run).",
            "provisional": "Graded on a Saturday projection; updated when Sunday estimates or final numbers arrive.",
            "v2": "v1 x 1.37 for non-English films opening in 2,000+ theaters (a blind spot found in the backtest); otherwise equal to v1.",
            "combined": "Geometric mean of our v1 forecast and Hollywood's midpoint; tests whether the two carry different information.",
            "matched": "Our forecast given Hollywood's range width (same high/low ratio), so 'inside the range' compares aim, not width.",
            "gap_ratio": "Our median miss divided by Hollywood's: how far free public data is from paid tracking (1.0 = level).",
            "retro": "Computed after release for illustration; not part of the Amendment 7 test, which starts with the Nov 11 openings.",
        },
        "summary": summary,
        "films": films,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
