#!/usr/bin/env python3
"""The breakout chapter (HYPOTHESES.md Amendment 5): community audiences, legs (H8), breakout probability.

A. Residuals of the traditional T-7 forecasts by community class (exploratory; H7 exploratory part).
B. H8: legs model — log(domestic total / opening) — traditional vs + attention + community, rolling quarterly
   backtest 2017-2025, paired bootstrap; ridge and CatBoost both reported (conservative p = the larger).
C. Breakout model: P(opening >= 2x the traditional ridge T-7 forecast), rolling quarterly, Brier/AUC/calibration.
Output: docs/breakout_results.md, data/processed/legs_predictions.csv, data/processed/breakout_predictions.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.metrics import brier_score_loss, roc_auc_score

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from backtest import EXCLUDED_YEARS, catboost_model, ridge_model  # noqa: E402
from feature_sets import ATTENTION, CATEGORICAL, COMMUNITY, checkpoint_features  # noqa: E402

TABLE = ROOT / "data/processed/model_table.csv"
CONF = ROOT / "data/processed/confirmatory_predictions.csv"
OUT = ROOT / "docs/breakout_results.md"
RNG = np.random.default_rng(0)
CLASSES = {"c1_creator_native": "C1 creator-native", "c2_game_ip": "C2 game IP", "c3_anime": "C3 anime",
           "c4_faith": "C4 faith audience", "c5_spanish": "C5 Spanish-language"}


def boot_mean(x, n=4000):
    b = np.array([RNG.choice(x, len(x)).mean() for _ in range(n)])
    return x.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5), np.mean(b <= 0)


def load():
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    df = df[df.in_model & ~df.year.isin(EXCLUDED_YEARS) & (df.year <= 2025)].copy()
    df["primary_genre"] = df.genres.fillna("Unknown").str.split("|").str[0]
    df["quarter"] = df.release_date.dt.to_period("Q")
    for c in COMMUNITY:
        df[c] = df[c].astype(bool)
    return df


def class_residuals(df, conf):
    lines = ["## A. Who does the traditional forecast miss? (exploratory)", "",
             "Mean residual of the traditional T-7 forecast, log scale (positive = opened above forecast); "
             "×≈ = exp(mean). 2014-2025 rolling backtest.", "",
             "| Class | Films | Ridge mean (95% CI) | ×≈ | CatBoost mean (95% CI) | ×≈ |", "|---|---|---|---|---|---|"]
    for col, name in CLASSES.items():
        row = [name]
        ids = set(df[df[col]].film_id)
        for m in ("ridge", "catboost"):
            e = conf[(conf.checkpoint == "T-7") & (conf.model == m) & conf.film_id.isin(ids)].err.to_numpy()
            if len(e) < 3:
                row += ["—", "—"]
                continue
            mu, lo, hi, _ = boot_mean(e)
            row += [f"{mu:+.2f} ({lo:+.2f} to {hi:+.2f})", f"{np.exp(mu):.2f}"]
        n = conf[(conf.checkpoint == "T-7") & (conf.model == "ridge") & conf.film_id.isin(ids)].shape[0]
        lines.append(f"| {row[0]} | {n} | " + " | ".join(row[1:]) + " |")
    base = conf[(conf.checkpoint == "T-7") & (conf.model == "ridge")].err
    lines += [f"| All other films (reference) | {len(base)} | {base.mean():+.2f} | {np.exp(base.mean()):.2f} | | |", ""]
    c1 = conf[(conf.checkpoint == "T-7") & (conf.model == "ridge") & conf.film_id.isin(set(df[df.c1_creator_native].film_id))]
    lines += ["C1 films individually (ridge, T-7; ×  = actual ÷ forecast):", "",
              "| Film | Year | × |", "|---|---|---|"]
    lines += [f"| {r.title} | {r.year} | {np.exp(r.err):.2f} |" for r in c1.sort_values("year").itertuples()]
    return lines + [""]


def legs(df):
    d = df[df.log_total_over_opening.notna() & np.isfinite(df.log_total_over_opening)].copy()
    d["log_opening_known"] = d.log_opening  # legs model is used after opening weekend: the opening is known
    base = checkpoint_features("T-7") + ["log_opening_known"]
    rows = []
    for q in pd.period_range("2017Q1", "2025Q4", freq="Q"):
        if q.year in EXCLUDED_YEARS:
            continue
        test, train = d[d.quarter == q], d[(d.release_date < q.start_time) & (d.year >= 2016)]
        if test.empty:
            continue
        tr, te = train.assign(log_opening=train.log_total_over_opening), test.assign(log_opening=test.log_total_over_opening)
        for name, feats in (("traditional", base), ("plus", base + ATTENTION + COMMUNITY)):
            for mname, fn in (("ridge", ridge_model), ("catboost", catboost_model)):
                p = fn(tr, te, feats)
                rows.append(pd.DataFrame({"film_id": test.film_id.values, "title": test.title.values, "year": test.year.values,
                                          "model": mname, "set": name, "pred": p, "actual": test.log_total_over_opening.values}))
    r = pd.concat(rows)
    r.to_csv(ROOT / "data/processed/legs_predictions.csv", index=False)
    r["abs_err"] = (r.actual - r.pred).abs()
    lines = ["## B. H8 — legs: does attention + community class predict how long a film runs?", "",
             "Target: log(domestic total ÷ opening weekend). Rolling quarterly backtest 2017-2025, trained on 2016+ films; "
             "the opening weekend itself is a feature (forecast made after opening). Gain = MAE(traditional) − MAE(plus).", "",
             "| Model | MAE traditional | MAE + attention & community | Gain (95% CI) | share ≤ 0 |", "|---|---|---|---|---|"]
    ps = []
    for m in ("ridge", "catboost"):
        w = r[r.model == m].pivot_table(index="film_id", columns="set", values="abs_err")
        g = (w.traditional - w.plus).to_numpy()
        mu, lo, hi, s = boot_mean(g)
        ps.append(s)
        lines.append(f"| {m} | {w.traditional.mean():.3f} | {w.plus.mean():.3f} | {mu:+.3f} ({lo:+.3f} to {hi:+.3f}) | {s:.3f} |")
    lines += ["", f"Conservative p (larger of the two) = **{max(ps):.3f}**; H8 {'supported' if max(ps) <= 0.05 else 'not supported'} at α = 0.05 "
              "(single pre-registered test, no further correction).", ""]
    best = r[(r.model == "catboost") & (r.set == "plus")].copy()
    best["actual_x"], best["pred_x"] = np.exp(best.actual), np.exp(best.pred)
    lines += ["Longest runs vs. the legs forecast (CatBoost + attention & community; × = total ÷ opening):", "",
              "| Film | Year | Actual × | Forecast × |", "|---|---|---|---|"]
    for x in best.assign(gap=best.actual - best.pred).sort_values("gap", ascending=False).head(10).itertuples():
        lines.append(f"| {x.title} | {x.year} | {x.actual_x:.1f} | {x.pred_x:.1f} |")
    return lines + [""]


def breakout(df, conf):
    ref = conf[(conf.checkpoint == "T-7") & (conf.model == "ridge")][["film_id", "err", "pred"]]
    d = df.merge(ref, on="film_id")
    d["breakout"] = (d.err >= np.log(2)).astype(int)
    d["trad_forecast"] = d.pred
    feats = checkpoint_features("T-7") + ATTENTION + COMMUNITY + ["trad_forecast"]
    cat = [f for f in feats if f in CATEGORICAL]
    rows = []
    for q in pd.period_range("2017Q1", "2025Q4", freq="Q"):
        if q.year in EXCLUDED_YEARS:
            continue
        test, train = d[d.quarter == q], d[(d.release_date < q.start_time) & (d.year >= 2016)]
        if test.empty or train.breakout.sum() < 10:
            continue
        X = lambda x: x[feats].assign(**{c: x[c].astype(str) for c in cat})
        m = CatBoostClassifier(iterations=500, depth=4, learning_rate=0.05, random_seed=7, verbose=False,
                               cat_features=cat, auto_class_weights=None)
        m.fit(X(train), train.breakout)
        rows.append(pd.DataFrame({"film_id": test.film_id.values, "title": test.title.values, "year": test.year.values,
                                  "p_breakout": m.predict_proba(X(test))[:, 1], "breakout": test.breakout.values}))
    r = pd.concat(rows)
    r.to_csv(ROOT / "data/processed/breakout_predictions.csv", index=False)
    base_rate = r.breakout.mean()
    brier, brier0 = brier_score_loss(r.breakout, r.p_breakout), brier_score_loss(r.breakout, np.full(len(r), base_rate))
    auc = roc_auc_score(r.breakout, r.p_breakout)
    r["bin"] = pd.cut(r.p_breakout, [0, .05, .1, .2, .3, 1.0], include_lowest=True)
    cal = r.groupby("bin", observed=True).agg(films=("breakout", "size"), predicted=("p_breakout", "mean"), actual=("breakout", "mean"))
    lines = ["## C. Breakout probability: can a model flag a 2× surprise before opening?", "",
             f"Breakout = opened at ≥ 2× the traditional ridge T-7 forecast. Rolling quarterly 2017-2025, n = {len(r)}, "
             f"base rate {base_rate:.1%}.", "",
             f"- ROC-AUC **{auc:.2f}** (0.5 = no better than chance)",
             f"- Brier score {brier:.4f} vs {brier0:.4f} for always predicting the base rate "
             f"(skill = {1 - brier / brier0:+.1%})", "", "Calibration:", "", cal.round(3).to_markdown(), "",
             "Highest predicted breakout probabilities (and what happened):", "",
             "| Film | Year | P(breakout) | Broke out? |", "|---|---|---|---|"]
    for x in r.sort_values("p_breakout", ascending=False).head(15).itertuples():
        lines.append(f"| {x.title} | {x.year} | {x.p_breakout:.2f} | {'yes' if x.breakout else 'no'} |")
    return lines + [""]


def main():
    df, conf = load(), pd.read_csv(CONF)
    L = ["# The breakout chapter — results", "", "Pre-registered in HYPOTHESES.md Amendment 5 (commit 250c058; C1 list b5de31a). "
         "Section A is exploratory; B is the H8 test; C is descriptive.", ""]
    L += class_residuals(df, conf) + legs(df) + breakout(df, conf)
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
