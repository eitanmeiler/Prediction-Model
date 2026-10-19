#!/usr/bin/env python3
"""Rolling-origin backtest: every quarter from 2014 to 2024, train only on films released before the quarter,
then predict the quarter's films. 2020-2021 are excluded from training and scoring (HYPOTHESES.md);
2025 is the sealed holdout and is never touched here.

Two forecast checkpoints:
  T-7  : a week out. Opening theater count and same-weekend competition are known.
  T-28 : four weeks out. No theater count, no recent-competitor openings.
Models: comps baseline (median of similar past films), ridge regression, CatBoost.
80% intervals come from the empirical 10th/90th percentile of earlier quarters' out-of-sample errors.
Outputs: data/processed/backtest_predictions.csv, docs/backtest_summary.md
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import RidgeCV
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from feature_sets import ATTENTION, CATEGORICAL, checkpoint_features  # noqa: E402

TABLE = ROOT / "data" / "processed" / "model_table.csv"
PRED_OUT = ROOT / "data" / "processed" / "backtest_predictions.csv"
SUMMARY = ROOT / "docs" / "backtest_summary.md"
EXCLUDED_YEARS = {2020, 2021}
FIRST_TEST, LAST_TEST = "2014Q1", "2024Q4"


def load():
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    df = df[df["in_model"] & ~df["year"].isin(EXCLUDED_YEARS) & (df["year"] <= 2024)].copy()  # 2025 sealed, 2026 = live
    df["primary_genre"] = df["genres"].fillna("Unknown").str.split("|").str[0]
    df["quarter"] = df["release_date"].dt.to_period("Q")
    return df


def comps_baseline(train, test):
    """Median log opening of the last 3 years' films with the same primary genre and sequel status."""
    recent = train[train.release_date >= train.release_date.max() - pd.DateOffset(years=3)]
    table = recent.groupby(["primary_genre", "sequel_like"]).log_opening.median()
    fallback = recent.log_opening.median()
    return np.array([table.get((g, s), fallback) for g, s in zip(test.primary_genre, test.sequel_like)])


def ridge_model(train, test, feats):
    num = [f for f in feats if f not in CATEGORICAL]
    cat = [f for f in feats if f in CATEGORICAL]
    pre = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    m = make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 20)))
    m.fit(train[feats].astype({c: float for c in num}), train.log_opening)
    return m.predict(test[feats].astype({c: float for c in num}))


def catboost_model(train, test, feats):
    cat = [f for f in feats if f in CATEGORICAL]
    m = CatBoostRegressor(iterations=700, depth=6, learning_rate=0.05, loss_function="RMSE",
                          random_seed=7, verbose=False, cat_features=cat)
    X = lambda d: d[feats].assign(**{c: d[c].astype(str) for c in cat})
    m.fit(X(train), train.log_opening)
    return m.predict(X(test))


def run():
    df = load()
    quarters = pd.period_range(FIRST_TEST, LAST_TEST, freq="Q")
    rows = []
    for q in quarters:
        if q.year in EXCLUDED_YEARS:
            continue
        test = df[df.quarter == q]
        train = df[df.release_date < q.start_time]
        if test.empty:
            continue
        for cp in ("T-7", "T-28"):
            feats = checkpoint_features(cp)
            preds = {"comps": comps_baseline(train, test),
                     "ridge": ridge_model(train, test, feats),
                     "catboost": catboost_model(train, test, feats)}
            if q.year >= 2017:  # attention exists from mid-2015: train on 2016+ films only
                preds["catboost_att"] = catboost_model(train[train.year >= 2016], test, feats + ATTENTION)
            for model, p in preds.items():
                rows.append(pd.DataFrame({"film_id": test.film_id.values, "title": test.title.values,
                                          "year": test.year.values, "quarter": str(q), "checkpoint": cp,
                                          "model": model, "pred": p, "actual": test.log_opening.values}))
        print(f"  {q}: trained on {len(train)}, predicted {len(test)}", flush=True)
    pred = pd.concat(rows, ignore_index=True)
    pred["err"] = pred.actual - pred.pred

    # 80% interval from earlier quarters' errors only (same model & checkpoint)
    lo, hi = [], []
    for (m, cp), g in pred.groupby(["model", "checkpoint"], sort=False):
        for q, gq in g.groupby("quarter", sort=True):
            # errors from the previous 8 quarters only, so ranges widen when the market shifts
            prior_q = sorted(x for x in g.quarter.unique() if x < q)[-8:]
            past = g[g.quarter.isin(prior_q)].err
            ok = len(past) >= 150
            lo.append(pd.Series(gq.pred + (past.quantile(0.10) if ok else np.nan), index=gq.index))
            hi.append(pd.Series(gq.pred + (past.quantile(0.90) if ok else np.nan), index=gq.index))
    pred["lo80"], pred["hi80"] = pd.concat(lo), pd.concat(hi)
    pred.to_csv(PRED_OUT, index=False)
    return pred


def metrics(g):
    ratio = np.exp(g.pred - g.actual)
    covered = g.dropna(subset=["lo80"])
    return pd.Series({
        "films": len(g),
        "median_abs_pct_err": np.median(np.abs(ratio - 1)) * 100,
        "within_25pct": np.mean(np.abs(ratio - 1) <= 0.25) * 100,
        "mae_log": np.mean(np.abs(g.err)),
        "interval80_coverage": ((covered.actual >= covered.lo80) & (covered.actual <= covered.hi80)).mean() * 100,
    })


def bootstrap_gain(pred, cp, a="catboost", b="ridge", n=2000, seed=0):
    """Paired bootstrap of MAE(log) difference b - a, resampling films. Positive = a is better."""
    x = pred[(pred.checkpoint == cp)].pivot_table(index="film_id", columns="model", values="err")
    d = (x[b].abs() - x[a].abs()).to_numpy()
    rng = np.random.default_rng(seed)
    boots = [rng.choice(d, len(d)).mean() for _ in range(n)]
    return d.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def summarize(pred):
    overall = pred.groupby(["checkpoint", "model"]).apply(metrics).round(1)
    common = pred[pred.year >= 2017]
    overall_17 = common.groupby(["checkpoint", "model"]).apply(metrics).round(1)
    by_period = pred.assign(period=np.where(pred.year <= 2019, "2014-2019", "2022-2024")) \
        .groupby(["checkpoint", "model", "period"]).apply(metrics).round(1)
    lines = ["# Backtest summary", "",
             "Rolling quarterly retrain, 2014-2024 (2020-2021 excluded, 2025 sealed). Errors are on opening-weekend "
             "gross; *median abs % error* is the typical miss, *within 25%* the share of films forecast within ±25%.",
             "", "## Overall (2014-2024; catboost_att only scored from 2017)", "", overall.to_markdown(), "",
             "## Same films for every model (2017-2024)", "", overall_17.to_markdown(), "", "## By period (H2)", "", by_period.to_markdown(), "",
             "## Bias by year (mean of actual − predicted, log scale; negative = over-forecast)", "", pred[pred.checkpoint == "T-7"].pivot_table(index="year", columns="model", values="err", aggfunc="mean").round(3).to_markdown(), "",
             "## Is CatBoost better than ridge? (paired bootstrap on MAE of log opening)", ""]
    for cp in ("T-7", "T-28"):
        m, l, h = bootstrap_gain(pred, cp)
        lines.append(f"- {cp}: ridge MAE − CatBoost MAE = {m:.3f} (95% CI {l:.3f} to {h:.3f})")
    SUMMARY.parent.mkdir(exist_ok=True)
    SUMMARY.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    summarize(run())
