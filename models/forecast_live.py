#!/usr/bin/env python3
"""Live opening-weekend forecasts for upcoming releases (rows with upcoming=True in the model table).

Primary model: CatBoost + attention (docs/frozen_spec.md), used once a film's attention window (T-28..T-8) is
complete; before that the ridge forecast is shown and labelled as such.
Checkpoint per film: T-7 if its opening theater count is known (tracker/upcoming.json), else T-28.
80% range: 10th/90th percentile of the ridge backtest's errors over its last 8 quarters at that checkpoint.

  python models/forecast_live.py           # print forecasts (draft)
  python models/forecast_live.py --freeze  # also append them to forecasts/forecast_log.csv (never edited)
  python models/forecast_live.py --freeze --films 20261106_the_cat_in_the_hat  # freeze only the films that are due

Training data: films through 2024 until the sealed 2025 evaluation has been run; pass --train-through 2026
afterwards. Freezing is refused while the current-market feature is missing (no 2026 box office loaded).
"""
import argparse
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from backtest import EXCLUDED_YEARS, catboost_model  # noqa: E402
from feature_sets import ATTENTION, CATEGORICAL, checkpoint_features  # noqa: E402

TABLE = ROOT / "data" / "processed" / "model_table.csv"
BACKTEST = ROOT / "data" / "processed" / "backtest_predictions.csv"
LOG = ROOT / "forecasts" / "forecast_log.csv"


def fit_ridge(train, feats):
    from sklearn.compose import ColumnTransformer
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import RidgeCV
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    num = [f for f in feats if f not in CATEGORICAL]
    cat = [f for f in feats if f in CATEGORICAL]
    pre = ColumnTransformer([
        ("num", make_pipeline(SimpleImputer(strategy="median", add_indicator=True), StandardScaler()), num),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat)])
    model = make_pipeline(pre, RidgeCV(alphas=np.logspace(-2, 3, 20)))
    X = lambda d: d[feats].astype({c: float for c in num})
    model.fit(X(train), train.log_opening)
    return model, X


def drivers(model, X, row, train, k=5):
    """Biggest pushes up/down vs. an average film: coefficient x (this film's value - training mean), transformed."""
    pre, ridge = model[0], model[-1]
    names = pre.get_feature_names_out()
    z_row = pre.transform(X(row)).toarray()[0] if hasattr(pre.transform(X(row)), "toarray") else pre.transform(X(row))[0]
    z_mean = np.asarray(pre.transform(X(train)).mean(axis=0)).ravel()
    contrib = ridge.coef_ * (z_row - z_mean)
    order = np.argsort(-np.abs(contrib))[:k]
    clean = lambda n: n.replace("num__", "").replace("cat__", "").replace("missingindicator_", "missing: ")
    return "; ".join(f"{clean(names[i])} {'+' if contrib[i] > 0 else '−'}{abs(contrib[i]):.2f}" for i in order)


def comparables(model, X, row, train, k=5):
    pre = model[0]
    zt = pre.transform(X(train))
    zt = zt.toarray() if hasattr(zt, "toarray") else zt
    zr = pre.transform(X(row))
    zr = (zr.toarray() if hasattr(zr, "toarray") else zr)[0]
    w = np.abs(model[-1].coef_)  # weight dimensions by how much the model cares about them
    dist = np.sqrt((((zt - zr) * w) ** 2).sum(axis=1))
    near = train.iloc[np.argsort(dist)[:k]]
    return "; ".join(f"{t} ({y}) ${np.exp(o) / 1e6:.0f}M" for t, y, o in zip(near.title, near.year, near.log_opening))


def interval(checkpoint, model="ridge"):
    bt = pd.read_csv(BACKTEST)
    g = bt[(bt.model == model) & (bt.checkpoint == checkpoint)]
    recent = sorted(g.quarter.unique())[-8:]
    e = g[g.quarter.isin(recent)].err
    return e.quantile(0.10), e.quantile(0.90)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--films", default="", help="comma-separated film_ids: only these are forecast (and frozen)")
    ap.add_argument("--train-through", type=int, default=2025)  # 2025 unsealed by the confirmatory run (2026-10-19)
    args = ap.parse_args()

    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    df["primary_genre"] = df["genres"].fillna("Unknown").str.split("|").str[0]
    train = df[df.in_model & ~df.year.isin(EXCLUDED_YEARS) & (df.year <= args.train_through)]
    up = df[df.upcoming.astype(bool)].sort_values("release_date")
    if args.films:
        want = {f.strip() for f in args.films.split(",") if f.strip()}
        unknown = want - set(up.film_id)
        if unknown:
            sys.exit(f"Unknown or not-upcoming film_id(s): {sorted(unknown)}")
        up = up[up.film_id.isin(want)]
    missing_market = up.mkt_recent_median.isna().any()
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    out = []
    for cp in ("T-7", "T-28"):
        rows = up[up.open_theaters.notna()] if cp == "T-7" else up[up.open_theaters.isna()]
        if rows.empty:
            continue
        feats = checkpoint_features(cp)
        model, X = fit_ridge(train, feats)
        cb = catboost_model(train, rows, feats)
        att = catboost_model(train[train.year >= 2016], rows, feats + ATTENTION)
        lo, hi = interval(cp)
        alo, ahi = interval(cp, "catboost_att")
        for (_, r), cbp, ap in zip(rows.iterrows(), cb, att):
            one = rows.loc[[r.name]]
            p = model.predict(X(one))[0]
            out.append({"frozen_at_utc": now, "git_commit": commit, "film_id": r.film_id, "title": r.title,
                        "release_date": r.release_date.date(), "checkpoint": cp, "model": "ridge",
                        "train_through": args.train_through,
                        "forecast_m": round(np.exp(p) / 1e6, 1), "lo80_m": round(np.exp(p + lo) / 1e6, 1),
                        "hi80_m": round(np.exp(p + hi) / 1e6, 1), "catboost_m": round(np.exp(cbp) / 1e6, 1),
                        "att_m": round(np.exp(ap) / 1e6, 1), "att_lo80_m": round(np.exp(ap + alo) / 1e6, 1),
                        "att_hi80_m": round(np.exp(ap + ahi) / 1e6, 1),
                        "att_inputs_complete": bool(r[["att_level", "att_accel"]].notna().all()),
                        "drivers": drivers(model, X, one, train), "comparables": comparables(model, X, one, train)})
    res = pd.DataFrame(out)
    # missing attention reads as "obscure film" to the model: only report it once the T-28..T-8 window is complete
    incomplete = ~res.att_inputs_complete
    res.loc[incomplete, ["att_m", "att_lo80_m", "att_hi80_m"]] = np.nan
    # primary (frozen spec, 2026-10-19): CatBoost + attention once its inputs are complete; ridge before that
    res["ridge_m"], res["ridge_lo80_m"], res["ridge_hi80_m"] = res.forecast_m, res.lo80_m, res.hi80_m
    res["primary_model"] = np.where(incomplete, "ridge (attention window incomplete)", "catboost_att")
    use = ~incomplete
    res.loc[use, "forecast_m"], res.loc[use, "lo80_m"], res.loc[use, "hi80_m"] = \
        res.loc[use, "att_m"], res.loc[use, "att_lo80_m"], res.loc[use, "att_hi80_m"]
    res["status"] = "draft (no 2026 market data)" if missing_market else "draft"
    (ROOT / "forecasts").mkdir(exist_ok=True)
    res.to_csv(ROOT / "forecasts" / "latest_draft.csv", index=False)  # read by the dashboard; overwritten each run
    pd.set_option("display.width", 220, "display.max_colwidth", 90)
    print(res[["title", "release_date", "checkpoint", "forecast_m", "lo80_m", "hi80_m", "primary_model", "ridge_m"]].to_string(index=False))
    for r in res.itertuples():
        print(f"\n{r.title}: drivers [{r.drivers}]\n  comparables: {r.comparables}")
    if missing_market:
        print("\nDRAFT ONLY: current-market feature is missing (load the 2026 Box Office Mojo page). Not frozen.")
    elif args.freeze:
        LOG.parent.mkdir(exist_ok=True)
        res.to_csv(LOG, mode="a", header=not LOG.exists(), index=False)
        print(f"\nFrozen: appended {len(res)} forecasts to {LOG} — commit it now so git timestamps it.")


if __name__ == "__main__":
    main()
