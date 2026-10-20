#!/usr/bin/env python3
"""H9 (HYPOTHESES.md Amendment 6): does post-release attention momentum (days +3..+9 vs T-7..T-1) improve the legs
model beyond the opening weekend and traditional features? Rolling quarterly 2017-2025, 2016+ training,
paired bootstrap MAE gain; ridge and CatBoost; conservative p = the larger. Output: docs/nowcast_results.md
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from backtest import EXCLUDED_YEARS, catboost_model, ridge_model  # noqa: E402
from feature_sets import checkpoint_features  # noqa: E402

RNG = np.random.default_rng(0)
df = pd.read_csv(ROOT / "data/processed/model_table.csv", parse_dates=["release_date"])
post = pd.read_csv(ROOT / "data/interim/wiki_post.csv")
df = df.merge(post[["film_id", "post_momentum"]], on="film_id", how="inner")
df = df[df.in_model & ~df.year.isin(EXCLUDED_YEARS) & (df.year <= 2025) & np.isfinite(df.log_total_over_opening)].copy()
df["primary_genre"] = df.genres.fillna("Unknown").str.split("|").str[0]
df["quarter"] = df.release_date.dt.to_period("Q")
df["log_opening_known"] = df.log_opening
base = checkpoint_features("T-7") + ["log_opening_known"]
rows = []
for q in pd.period_range("2017Q1", "2025Q4", freq="Q"):
    if q.year in EXCLUDED_YEARS:
        continue
    te, tr = df[df.quarter == q], df[(df.release_date < q.start_time) & (df.year >= 2016)]
    if te.empty:
        continue
    tr2, te2 = tr.assign(log_opening=tr.log_total_over_opening), te.assign(log_opening=te.log_total_over_opening)
    for setname, feats in (("base", base), ("momentum", base + ["post_momentum"])):
        for m, fn in (("ridge", ridge_model), ("catboost", catboost_model)):
            p = fn(tr2, te2, feats)
            rows.append(pd.DataFrame({"film_id": te.film_id.values, "title": te.title.values, "year": te.year.values,
                                      "model": m, "set": setname, "pred": p, "actual": te.log_total_over_opening.values}))
r = pd.concat(rows)
r.to_csv(ROOT / "data/processed/nowcast_predictions.csv", index=False)
r["abs_err"] = (r.actual - r.pred).abs()
L = ["# H9 — catching word of mouth early (nowcast of the final total, 9 days after release)", "",
     "Legs = log(domestic total ÷ opening weekend). Gain = MAE(base) − MAE(+ post-release momentum).", "",
     "| Model | MAE base | MAE + momentum | Gain (95% CI) | share ≤ 0 | typical total-gross miss base → + momentum |", "|---|---|---|---|---|---|"]
ps = []
for m in ("ridge", "catboost"):
    w = r[r.model == m].pivot_table(index="film_id", columns="set", values="abs_err")
    g = (w.base - w.momentum).to_numpy()
    b = np.array([RNG.choice(g, len(g)).mean() for _ in range(4000)])
    s = float(np.mean(b <= 0))
    ps.append(s)
    pct = lambda e: np.median(np.abs(np.exp(e) - 1)) * 100
    L.append(f"| {m} | {w.base.mean():.3f} | {w.momentum.mean():.3f} | {g.mean():+.3f} ({np.percentile(b, 2.5):+.3f} to "
             f"{np.percentile(b, 97.5):+.3f}) | {s:.3f} | {pct(w.base):.0f}% → {pct(w.momentum):.0f}% |")
L += ["", f"Conservative p = **{max(ps):.3f}** → H9 **{'supported' if max(ps) <= 0.05 else 'not supported'}** at α = 0.05.", ""]
cb = r[(r.model == "catboost")].pivot_table(index=["film_id", "title", "year", "actual"], columns="set", values="pred").reset_index()
cb["base_x"], cb["mom_x"], cb["actual_x"] = np.exp(cb.base), np.exp(cb.momentum), np.exp(cb.actual)
cb["fixed"] = (cb.actual - cb.base).abs() - (cb.actual - cb.momentum).abs()
L += ["Where momentum helped most (CatBoost; × = total ÷ opening):", "", "| Film | Year | Actual × | Base forecast × | With momentum × |", "|---|---|---|---|---|"]
L += [f"| {x.title} | {x.year} | {x.actual_x:.1f} | {x.base_x:.1f} | {x.mom_x:.1f} |" for x in cb.sort_values("fixed", ascending=False).head(10).itertuples()]
(ROOT / "docs/nowcast_results.md").write_text("\n".join(L) + "\n")
print("\n".join(L))
