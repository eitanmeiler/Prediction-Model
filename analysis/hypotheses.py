#!/usr/bin/env python3
"""Confirmatory tests for H1 (star effect smaller after 2020) and H2 (openings less predictable after 2020).

DEVELOPMENT RUN: 2025 stays sealed, so the post period here is 2022-2024. The confirmatory run adds 2025
(HYPOTHESES.md) and is the one reported as the result. Output: docs/hypothesis_results_dev.md
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "model_table.csv"
BACKTEST = ROOT / "data" / "processed" / "backtest_predictions.csv"
OUT = ROOT / "docs" / "hypothesis_results_dev.md"
POST_YEARS = [2022, 2023, 2024]  # + 2025 in the confirmatory run


def h1(df):
    """OLS of log opening on star power x period, with controls and year fixed effects (absorb market level)."""
    d = df[df.in_model & df.year.between(2013, 2024) & ~df.year.isin([2020, 2021])
           & ~df.g_animation & df.star_mean.notna()].copy()
    d["post"] = d.year.isin(POST_YEARS).astype(int)
    d["star_c"] = d.star_mean - d.star_mean.mean()
    d["budget_tier"] = pd.qcut(d.log_budget, 4, labels=["b1", "b2", "b3", "b4"]).astype(str).replace("nan", "unknown")
    d["log_theaters"] = np.log(d.open_theaters)
    genres = " + ".join(c for c in d.columns if c.startswith("g_") and c not in ("g_animation", "g_western", "g_war", "g_history"))
    base = (f"log_opening ~ star_c * post + sequel_like + C(mpaa) + C(month) + C(budget_tier) + C(year) + {genres}")
    out = {}
    for label, formula in [("without theater count", base), ("with theater count", base + " + log_theaters")]:
        m = smf.ols(formula, data=d.astype({c: float for c in d.columns if d[c].dtype == bool})).fit(cov_type="HC3")
        out[label] = {
            "n": int(m.nobs),
            "star effect pre (per +1 log-opening of cast history)": m.params["star_c"],
            "change after 2020 (interaction)": m.params["star_c:post"],
            "interaction 95% CI": tuple(m.conf_int().loc["star_c:post"]),
            "interaction p (one-sided, H1: negative)": m.pvalues["star_c:post"] / 2 if m.params["star_c:post"] < 0
            else 1 - m.pvalues["star_c:post"] / 2,
        }
    # year-by-year star coefficient (descriptive, for the headline chart)
    yearly = {}
    for y, g in d.groupby("year"):
        if len(g) < 60:
            continue
        m = smf.ols("log_opening ~ star_c + sequel_like + C(mpaa) + C(budget_tier)", data=g.astype(
            {c: float for c in g.columns if g[c].dtype == bool})).fit(cov_type="HC3")
        yearly[y] = (m.params["star_c"], *m.conf_int().loc["star_c"])
    return out, yearly


def h2(pred, model, seed=0, n=4000):
    """Median absolute log error at T-7: 2022-2024 minus 2016-2019 (pre-registered windows), bootstrap CI."""
    p = pred[(pred.checkpoint == "T-7") & (pred.model == model)]
    pre = np.abs(p[p.year.between(2016, 2019)].err.to_numpy())
    post = np.abs(p[p.year.isin(POST_YEARS)].err.to_numpy())
    post_ex22 = np.abs(p[p.year.isin([2023, 2024])].err.to_numpy())
    rng = np.random.default_rng(seed)

    def boot(a, b):
        diffs = [np.median(rng.choice(b, len(b))) - np.median(rng.choice(a, len(a))) for _ in range(n)]
        return np.median(b) - np.median(a), np.percentile(diffs, 2.5), np.percentile(diffs, 97.5), np.mean(np.array(diffs) <= 0)

    return {"pre_median_abs_log_err": np.median(pre), "post_median_abs_log_err": np.median(post),
            "diff (post - pre)": boot(pre, post), "diff excluding 2022 reopening year": boot(pre, post_ex22),
            "n_pre": len(pre), "n_post": len(post)}


def main():
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    pred = pd.read_csv(BACKTEST)
    h1_res, yearly = h1(df)
    lines = ["# Hypothesis results — DEVELOPMENT RUN (2025 sealed; post = 2022-2024)", "",
             "Not the confirmatory result: that run adds 2025 once the model is frozen. Holm correction across "
             "H1-H5 is applied in the confirmatory run.", "", "## H1 — star-power effect after 2020", ""]
    for label, r in h1_res.items():
        lo, hi = r["interaction 95% CI"]
        lines += [f"**{label}** (n = {r['n']})", "",
                  f"- star effect, 2013-2019: {r['star effect pre (per +1 log-opening of cast history)']:.3f}",
                  f"- change after 2020: {r['change after 2020 (interaction)']:.3f} (95% CI {lo:.3f} to {hi:.3f}), "
                  f"one-sided p = {r['interaction p (one-sided, H1: negative)']:.3f}", ""]
    lines += ["Year-by-year star coefficient (descriptive):", "", "| year | coef | 95% CI |", "|---|---|---|"]
    lines += [f"| {y} | {c:.3f} | {l:.3f} to {h:.3f} |" for y, (c, l, h) in yearly.items()]
    lines += ["", "## H2 — predictability at T-7 (median absolute log error)", ""]
    for model in ("ridge", "catboost"):
        r = h2(pred, model)
        d, lo, hi, p = r["diff (post - pre)"]
        d2, lo2, hi2, p2 = r["diff excluding 2022 reopening year"]
        lines += [f"**{model}**: 2016-2019 = {r['pre_median_abs_log_err']:.3f} (n={r['n_pre']}), "
                  f"2022-2024 = {r['post_median_abs_log_err']:.3f} (n={r['n_post']})", "",
                  f"- difference {d:+.3f} (95% CI {lo:+.3f} to {hi:+.3f}); bootstrap share ≤ 0: {p:.3f}",
                  f"- excluding 2022: {d2:+.3f} (95% CI {lo2:+.3f} to {hi2:+.3f}); share ≤ 0: {p2:.3f}", ""]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
