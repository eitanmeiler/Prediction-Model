#!/usr/bin/env python3
"""Amendment 9 candidate fixes, backtested before any decision (exploratory; nothing here changes the live model).

Problem (Hunger Games: Sunrise on the Reaping, Nov 20, 2026): forecast $43.6M, actual ~$120M. Two causes found:
  A. Split franchises: TMDB files the original Hunger Games films and the prequels as two collections, so the
     franchise inputs saw only The Ballad of Songbirds & Snakes ($44.6M).
  B. Top-end compression: the T-7 model under-forecast 40 of 42 openings above $100M (2017-2025), median x1.76.

Variants, all CatBoost + attention at T-7, rolling quarterly 2017-2025 (2020-21 excluded), trained on 2016+ films
before each quarter (the frozen procedure):
  base  current features
  A     + franchise family (collections linked by a shared title prefix): best, mean and last prior opening, count
  B     base + top-end correction: residual ~ hinge(pred - log $25M), fitted only on earlier quarters' errors
  AB    A + the same correction
Output: docs/amendment9_backtest.md
"""
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from backtest import EXCLUDED_YEARS, catboost_model  # noqa: E402
from feature_sets import ATTENTION, checkpoint_features  # noqa: E402

KNOWN_LAG = pd.Timedelta(days=7)
HINGE = np.log(25e6)
FAM = ["fam_prev_films", "fam_prev_best", "fam_prev_mean", "fam_prev_last"]


def prefix(title):
    t = re.split(r":| - ", str(title).lower())[0]
    t = re.sub(r"[^a-z0-9 ]", "", t).strip()
    t = re.sub(r"^the ", "", t)
    return t if (len(t.split()) >= 2 or len(t) >= 8) else None


def franchise_family(df):
    """Union TMDB collections whose films share a title prefix; then prior openings within the family."""
    parent = {}
    find = lambda x: x if parent.get(x, x) == x else find(parent[x])
    by_prefix = {}
    for r in df[df.collection_id.notna()].itertuples():
        p = prefix(r.title)
        if p:
            by_prefix.setdefault(p, set()).add(r.collection_id)
    for cids in by_prefix.values():
        cids = sorted(cids)
        for c in cids[1:]:
            parent[find(c)] = find(cids[0])
    fam = df.collection_id.map(lambda c: find(c) if pd.notna(c) else np.nan)
    hist, rows = {}, []
    for r, f in zip(df.sort_values("release_date").itertuples(), fam[df.sort_values("release_date").index]):
        past = [lo for dt, lo in hist.get(f, []) if dt <= r.release_date - KNOWN_LAG] if pd.notna(f) else []
        rows.append({"film_id": r.film_id, "fam_prev_films": len(past),
                     "fam_prev_best": max(past) if past else np.nan,
                     "fam_prev_mean": np.mean(past) if past else np.nan,
                     "fam_prev_last": past[-1] if past else np.nan})
        if pd.notna(f) and pd.notna(r.log_opening):
            hist.setdefault(f, []).append((r.release_date, r.log_opening))
    merged = {p: c for p, c in by_prefix.items() if len(c) > 1}
    return pd.DataFrame(rows), merged


def correct(pred, past):
    """Top-end correction fitted on earlier quarters only: err = b * max(0, pred - HINGE)."""
    if len(past) < 200:
        return pred, 0.0
    h = np.maximum(0, past.pred - HINGE)
    b = float((h * past.err).sum() / max((h * h).sum(), 1e-9))
    b = max(b, 0.0)  # only ever stretch upward, never pull big forecasts down
    return pred + b * np.maximum(0, pred - HINGE), b


def main():
    df = pd.read_csv(ROOT / "data/processed/model_table.csv", parse_dates=["release_date"])
    df["primary_genre"] = df["genres"].fillna("Unknown").str.split("|").str[0]
    fam, merged = franchise_family(df)
    df = df.merge(fam, on="film_id", how="left")
    d = df[df.in_model & ~df.year.isin(EXCLUDED_YEARS) & (df.year <= 2025)].copy()
    d["quarter"] = d.release_date.dt.to_period("Q")
    base_f = checkpoint_features("T-7") + ATTENTION
    out = []
    for q in pd.period_range("2017Q1", "2025Q4", freq="Q"):
        if q.year in EXCLUDED_YEARS:
            continue
        test, train = d[d.quarter == q], d[(d.release_date < q.start_time) & (d.year >= 2016)]
        if test.empty:
            continue
        for name, feats in (("base", base_f), ("A", base_f + FAM)):
            p = catboost_model(train, test, feats)
            out.append(pd.DataFrame({"film_id": test.film_id.values, "title": test.title.values, "year": test.year.values,
                                     "quarter": str(q), "variant": name, "pred": p, "actual": test.log_opening.values}))
        print(f"  {q}: {len(test)} films", flush=True)
    r = pd.concat(out, ignore_index=True)
    r["err"] = r.actual - r.pred
    # corrections: for each quarter, fit on that variant's earlier out-of-sample errors only
    extra = []
    for src, name in (("base", "B"), ("A", "AB")):
        s = r[r.variant == src].sort_values("quarter")
        for q, g in s.groupby("quarter", sort=True):
            past = s[s.quarter < q]
            p2, b = correct(g.pred.to_numpy(), past)
            extra.append(g.assign(variant=name, pred=p2, err=g.actual - p2, b=b))
    r = pd.concat([r] + extra, ignore_index=True)
    r.to_csv(ROOT / "data/processed/amendment9_predictions.csv", index=False)

    mape = lambda e: float(np.median(np.abs(np.exp(e) - 1)) * 100)
    L = ["# Amendment 9 candidates: backtest (exploratory)", "",
         "CatBoost + attention at T-7, rolling quarterly 2017-2025 (2020-21 excluded), trained on 2016+ films before each "
         "quarter. Miss = |actual / forecast - 1|. Corrections are fitted only on earlier quarters.", "",
         f"Franchise families linked by title prefix ({len(merged)}): " +
         "; ".join(f"{p} ({len(c)} collections)" for p, c in sorted(merged.items())), "",
         "| Variant | Typical miss, all | 2022-2025 | 2025 | $100M+ openings: median actual/forecast | under-forecast |",
         "|---|---|---|---|---|---|"]
    big = set(r[(r.variant == "base") & (np.exp(r.actual) >= 100e6)].film_id)
    for v in ("base", "A", "B", "AB"):
        s = r[r.variant == v]
        b = s[s.film_id.isin(big)]
        L.append(f"| {v} | {mape(s.err):.1f}% | {mape(s[s.year >= 2022].err):.1f}% | {mape(s[s.year == 2025].err):.1f}% | "
                 f"x{np.exp(b.err.median()):.2f} | {int((b.err > 0).sum())}/{len(b)} |")
    L += ["", "By year (typical miss):", "", "| Year | base | A | B | AB |", "|---|---|---|---|---|"]
    for y in sorted(r.year.unique()):
        L.append(f"| {y} | " + " | ".join(f"{mape(r[(r.variant == v) & (r.year == y)].err):.1f}%" for v in ("base", "A", "B", "AB")) + " |")
    (ROOT / "docs/amendment9_backtest.md").write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
