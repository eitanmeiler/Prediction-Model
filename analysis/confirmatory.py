#!/usr/bin/env python3
"""CONFIRMATORY RUN — unseals 2025, exactly as specified in docs/frozen_spec.md (commit e21bcc8).

Reuses the frozen model/metric functions unchanged; only the year range is extended through 2025.
Outputs: data/processed/confirmatory_predictions.csv, docs/confirmatory_results.md
Run once. Re-running reproduces the same numbers (fixed seeds), it does not "retry".
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
sys.path.insert(0, str(ROOT / "analysis"))
from backtest import EXCLUDED_YEARS, catboost_model, comps_baseline, metrics, ridge_model  # noqa: E402
from feature_sets import ATTENTION, checkpoint_features  # noqa: E402

TABLE = ROOT / "data" / "processed" / "model_table.csv"
ATT = ROOT / "data" / "interim" / "wiki_attention.csv"
PRED = ROOT / "data" / "processed" / "confirmatory_predictions.csv"
OUT = ROOT / "docs" / "confirmatory_results.md"
POST = [2022, 2023, 2024, 2025]
RNG = np.random.default_rng(0)


def load():
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    df = df[df["in_model"] & ~df["year"].isin(EXCLUDED_YEARS) & (df["year"] <= 2025)].copy()
    df["primary_genre"] = df["genres"].fillna("Unknown").str.split("|").str[0]
    df["quarter"] = df["release_date"].dt.to_period("Q")
    # same rename rule as the development attention tests
    df.loc[df["att_level"].notna() & df["film_id"].isin(
        pd.read_csv(ATT).query("att_suspect_rename").film_id), ["att_level", "att_accel", "att_t60"]] = np.nan
    return df


def backtest(df):
    rows = []
    for q in pd.period_range("2014Q1", "2025Q4", freq="Q"):
        if q.year in EXCLUDED_YEARS:
            continue
        test, train = df[df.quarter == q], df[df.release_date < q.start_time]
        if test.empty:
            continue
        for cp in ("T-7", "T-28"):
            feats = checkpoint_features(cp)
            preds = {"comps": comps_baseline(train, test), "ridge": ridge_model(train, test, feats),
                     "catboost": catboost_model(train, test, feats)}
            if q.year >= 2017:
                preds["catboost_att"] = catboost_model(train[train.year >= 2016], test, feats + ATTENTION)
                preds["ridge_att"] = ridge_model(train[train.year >= 2016], test, feats + ATTENTION)
                # H3 compares like with like (as in development): traditional features, same 2016+ training films
                preds["ridge_t16"] = ridge_model(train[train.year >= 2016], test, feats)
                preds["catboost_t16"] = catboost_model(train[train.year >= 2016], test, feats)
            for m, p in preds.items():
                rows.append(pd.DataFrame({"film_id": test.film_id.values, "title": test.title.values,
                                          "year": test.year.values, "quarter": str(q), "checkpoint": cp,
                                          "model": m, "pred": p, "actual": test.log_opening.values}))
        print(f"  {q}", flush=True)
    pred = pd.concat(rows, ignore_index=True)
    pred["err"] = pred.actual - pred.pred
    lo, hi = [], []
    for (m, cp), g in pred.groupby(["model", "checkpoint"], sort=False):
        for q, gq in g.groupby("quarter", sort=True):
            prior = sorted(x for x in g.quarter.unique() if x < q)[-8:]
            past = g[g.quarter.isin(prior)].err
            ok = len(past) >= 150
            lo.append(pd.Series(gq.pred + (past.quantile(0.10) if ok else np.nan), index=gq.index))
            hi.append(pd.Series(gq.pred + (past.quantile(0.90) if ok else np.nan), index=gq.index))
    pred["lo80"], pred["hi80"] = pd.concat(lo), pd.concat(hi)
    pred.to_csv(PRED, index=False)
    return pred


def boot_share_le0(x, n=4000):
    b = np.array([RNG.choice(x, len(x)).mean() for _ in range(n)])
    return x.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5), np.mean(b <= 0)


def h1(df):
    d = df[df.year.between(2013, 2025) & ~df.g_animation & df.star_mean.notna()].copy()
    d["post"] = d.year.isin(POST).astype(int)
    d["star_c"] = d.star_mean - d.star_mean.mean()
    d["log_theaters"] = np.log(d.open_theaters)
    d["budget_tier"] = pd.qcut(d.log_budget, 4, labels=["b1", "b2", "b3", "b4"]).astype(str).replace("nan", "unknown")
    genres = " + ".join(c for c in d.columns if c.startswith("g_") and c not in ("g_animation", "g_western", "g_war", "g_history"))
    base = f"log_opening ~ star_c * post + sequel_like + C(mpaa) + C(month) + C(budget_tier) + C(year) + {genres}"
    out = {}
    for label, f in (("without theater count", base), ("with theater count", base + " + log_theaters")):
        m = smf.ols(f, data=d.astype({c: float for c in d.columns if d[c].dtype == bool})).fit(cov_type="HC3")
        b, p2 = m.params["star_c:post"], m.pvalues["star_c:post"]
        out[label] = (int(m.nobs), m.params["star_c"], b, *m.conf_int().loc["star_c:post"], p2 / 2 if b < 0 else 1 - p2 / 2)
    return out


def h2(pred, model):
    p = pred[(pred.checkpoint == "T-7") & (pred.model == model)]
    pre, post = np.abs(p[p.year.between(2016, 2019)].err.to_numpy()), np.abs(p[p.year.isin(POST)].err.to_numpy())
    diffs = np.array([np.median(RNG.choice(post, len(post))) - np.median(RNG.choice(pre, len(pre))) for _ in range(4000)])
    return np.median(pre), np.median(post), np.median(post) - np.median(pre), np.percentile(diffs, 2.5), \
        np.percentile(diffs, 97.5), np.mean(diffs <= 0)


def h3(pred, base, att):
    p = pred[(pred.checkpoint == "T-7") & pred.model.isin([base, att])]
    w = p.pivot_table(index=["film_id", "year"], columns="model", values="err").dropna().reset_index()
    gain = (w[base].abs() - w[att].abs())
    pre, post = gain[w.year <= 2019].to_numpy(), gain[w.year >= 2022].to_numpy()
    diff = np.array([RNG.choice(post, len(post)).mean() - RNG.choice(pre, len(pre)).mean() for _ in range(4000)])
    return len(w), boot_share_le0(gain.to_numpy()), (post.mean() - pre.mean(), np.percentile(diff, 2.5),
                                                    np.percentile(diff, 97.5), np.mean(diff <= 0))


def resid_tests(df, pred):
    res = pred[(pred.checkpoint == "T-7") & (pred.model == "ridge")][["film_id", "err"]]
    att = pd.read_csv(ATT)[["film_id", "wiki_sources"]]
    d = df.merge(res, on="film_id").merge(att, on="film_id", how="left")
    one = lambda m, k: m.pvalues[k] / 2 if m.params[k] > 0 else 1 - m.pvalues[k] / 2
    a = d[d.wiki_sources.notna() & d.src_att.notna()]
    m4 = smf.ols("err ~ src_att", data=a).fit(cov_type="HC3")
    m5 = smf.ols("err ~ att_accel + att_level", data=d.dropna(subset=["att_accel", "att_level"])).fit(cov_type="HC3")
    return ((int(m4.nobs), m4.params["src_att"], *m4.conf_int().loc["src_att"], one(m4, "src_att")),
            (int(m5.nobs), m5.params["att_accel"], *m5.conf_int().loc["att_accel"], one(m5, "att_accel")))


def holm(pvals, alpha=0.05):
    order = sorted(pvals, key=pvals.get)
    out, stop = {}, False
    for i, k in enumerate(order):
        thr = alpha / (len(order) - i)
        ok = (not stop) and pvals[k] <= thr
        stop = stop or not ok
        out[k] = (pvals[k], thr, ok)
    return out


def main():
    df = load()
    pred = backtest(df)
    hold = pred[pred.year == 2025]
    card = hold.groupby(["checkpoint", "model"]).apply(metrics).round(1)
    r1 = h1(df)
    r2 = {m: h2(pred, m) for m in ("ridge", "catboost")}
    r3 = {"ridge": h3(pred, "ridge_t16", "ridge_att"), "catboost": h3(pred, "catboost_t16", "catboost_att")}
    r4, r5 = resid_tests(df, pred)
    p = {"H1": max(v[-1] for v in r1.values()), "H2": max(v[-1] for v in r2.values()),
         "H3": max(v[1][3] for v in r3.values()), "H4": r4[-1], "H5": r5[-1]}
    hm = holm(p)

    L = ["# Confirmatory results (sealed 2025 unsealed once; spec frozen at commit e21bcc8)", "",
         "## 2025 holdout scorecard (models trained only on earlier films, retrained quarterly)", "",
         card.to_markdown(), "", "## Hypothesis tests (post period = 2022-2025)", "", "### H1 — star effect after 2020", ""]
    for k, (n, pre, b, lo, hi, pv) in r1.items():
        L.append(f"- {k} (n={n}): pre-2020 star effect {pre:.3f}; change after 2020 {b:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}); one-sided p = {pv:.3f}")
    L += ["", "### H2 — predictability at T-7 (median |log error|)", ""]
    for m, (a, b, d, lo, hi, s) in r2.items():
        L.append(f"- {m}: 2016-19 {a:.3f} → 2022-25 {b:.3f}; diff {d:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}); share ≤ 0 = {s:.3f}")
    L += ["", "### H3 — attention gain at T-7 (MAE of log opening, 2017-2025; >0 = attention helps)", ""]
    for m, (n, g, b) in r3.items():
        L.append(f"- {m} (n={n}): gain {g[0]:+.3f} (95% CI {g[1]:+.3f} to {g[2]:+.3f}); share ≤ 0 = {g[3]:.3f}; "
                 f"H3b post−pre {b[0]:+.3f} (95% CI {b[1]:+.3f} to {b[2]:+.3f}; share ≤ 0 = {b[3]:.3f})")
    L += ["", "### H4 / H5 — attention vs. the traditional model's misses", "",
          f"- H4 (n={r4[0]}): source-work attention {r4[1]:+.3f} (95% CI {r4[2]:+.3f} to {r4[3]:+.3f}); one-sided p = {r4[4]:.3f}",
          f"- H5 (n={r5[0]}): acceleration {r5[1]:+.3f} (95% CI {r5[2]:+.3f} to {r5[3]:+.3f}); one-sided p = {r5[4]:.3f}",
          "", "## Holm correction (α = 0.05; p = the conservative value defined in the frozen spec)", "",
          "| H | p | Holm threshold | supported |", "|---|---|---|---|"]
    L += [f"| {k} | {v[0]:.4f} | {v[1]:.4f} | {'**yes**' if v[2] else 'no'} |" for k, v in sorted(hm.items())]
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L))


if __name__ == "__main__":
    main()
