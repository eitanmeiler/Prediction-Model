#!/usr/bin/env python3
"""H3-H5 (pre-release Wikipedia attention). DEVELOPMENT RUN: 2025 sealed, post period = 2022-2024.

H3  : does adding attention features cut T-7 backtest error vs traditional features only? (2017-2024 test quarters,
      training restricted to 2016+ films because pageviews start mid-2015). H3b: is the gain bigger after 2020?
H4  : among adaptations, is source-work attention (365 days ending T-180) positively related to the traditional
      model's out-of-sample residuals?
H5  : is attention acceleration (T-14..T-8 vs T-28..T-22) positively related to those residuals, beyond level?
Output: docs/attention_results_dev.md
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from backtest import EXCLUDED_YEARS, catboost_model, ridge_model  # noqa: E402
from feature_sets import checkpoint_features  # noqa: E402

TABLE = ROOT / "data" / "processed" / "model_table.csv"
ATT = ROOT / "data" / "interim" / "wiki_attention.csv"
BACKTEST = ROOT / "data" / "processed" / "backtest_predictions.csv"
OUT = ROOT / "docs" / "attention_results_dev.md"
ATT_FEATS = ["att_level", "att_accel", "att_t60", "src_att"]


def load():
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    att = pd.read_csv(ATT)
    df = df.merge(att, on="film_id", how="inner")
    df = df[df.in_model & ~df.year.isin(EXCLUDED_YEARS) & (df.year <= 2024)].copy()
    # renamed/late-created articles have near-zero recorded views: treat their attention as missing, not as "no buzz"
    df.loc[df.att_suspect_rename, ["att_level", "att_accel", "att_t60"]] = np.nan
    df["primary_genre"] = df["genres"].fillna("Unknown").str.split("|").str[0]
    df["quarter"] = df.release_date.dt.to_period("Q")
    return df


def h3(df, model_fn):
    base = checkpoint_features("T-7")
    rows = []
    for q in pd.period_range("2017Q1", "2024Q4", freq="Q"):
        if q.year in EXCLUDED_YEARS:
            continue
        test, train = df[df.quarter == q], df[df.release_date < q.start_time]
        if test.empty:
            continue
        for name, feats in (("traditional", base), ("with_attention", base + ATT_FEATS)):
            p = model_fn(train, test, feats)
            rows.append(pd.DataFrame({"film_id": test.film_id.values, "year": test.year.values, "set": name,
                                      "abs_err": np.abs(test.log_opening.values - p)}))
    r = pd.concat(rows).pivot_table(index=["film_id", "year"], columns="set", values="abs_err").reset_index()
    r["gain"] = r.traditional - r.with_attention  # positive = attention helps
    rng = np.random.default_rng(0)

    def ci(x):
        b = [rng.choice(x, len(x)).mean() for _ in range(4000)]
        return x.mean(), np.percentile(b, 2.5), np.percentile(b, 97.5), np.mean(np.array(b) <= 0)

    pre, post = r[r.year <= 2019].gain.to_numpy(), r[r.year >= 2022].gain.to_numpy()
    diff = [rng.choice(post, len(post)).mean() - rng.choice(pre, len(pre)).mean() for _ in range(4000)]
    return {"n": len(r), "mae_traditional": r.traditional.mean(), "mae_with_attention": r.with_attention.mean(),
            "gain_all": ci(r.gain.to_numpy()), "gain_pre": ci(pre), "gain_post": ci(post),
            "h3b_post_minus_pre": (post.mean() - pre.mean(), np.percentile(diff, 2.5), np.percentile(diff, 97.5),
                                   np.mean(np.array(diff) <= 0))}


def residual_tests(df):
    pred = pd.read_csv(BACKTEST)
    res = pred[(pred.checkpoint == "T-7") & (pred.model == "ridge")][["film_id", "err"]]
    d = df.merge(res, on="film_id")
    adapt = d[d.wiki_sources.notna() & d.src_att.notna()]
    h4 = smf.ols("err ~ src_att", data=adapt).fit(cov_type="HC3")
    d5 = d.dropna(subset=["att_accel", "att_level"])
    h5 = smf.ols("err ~ att_accel + att_level", data=d5).fit(cov_type="HC3")
    one_sided = lambda m, k: m.pvalues[k] / 2 if m.params[k] > 0 else 1 - m.pvalues[k] / 2
    return ({"n": int(h4.nobs), "coef": h4.params["src_att"], "ci": tuple(h4.conf_int().loc["src_att"]),
             "p": one_sided(h4, "src_att")},
            {"n": int(h5.nobs), "coef": h5.params["att_accel"], "ci": tuple(h5.conf_int().loc["att_accel"]),
             "p": one_sided(h5, "att_accel"), "level_coef": h5.params["att_level"]})


def main():
    df = load()
    lines = ["# Attention hypotheses — DEVELOPMENT RUN (2025 sealed; post = 2022-2024)", "",
             f"Films with attention data: {df.att_level.notna().sum()} of {len(df)} (2016-2024, excl. 2020-21); "
             f"source-work attention for {df.src_att.notna().sum()} adaptations.", "",
             "## H3 — does attention reduce T-7 error? (MAE of log opening; gain > 0 means attention helps)", ""]
    for name, fn in (("ridge", ridge_model), ("catboost", catboost_model)):
        r = h3(df, fn)
        fmt = lambda t: f"{t[0]:+.3f} (95% CI {t[1]:+.3f} to {t[2]:+.3f}; bootstrap share ≤ 0: {t[3]:.3f})"
        lines += [f"**{name}** (n = {r['n']}): MAE traditional {r['mae_traditional']:.3f} → with attention "
                  f"{r['mae_with_attention']:.3f}", "",
                  f"- gain, all years: {fmt(r['gain_all'])}", f"- gain 2017-2019: {fmt(r['gain_pre'])}",
                  f"- gain 2022-2024: {fmt(r['gain_post'])}", f"- H3b (post − pre): {fmt(r['h3b_post_minus_pre'])}", ""]
    h4, h5 = residual_tests(df)
    lines += ["## H4 — source-work attention vs. the traditional model's misses (adaptations)", "",
              f"- n = {h4['n']}; coefficient {h4['coef']:+.3f} (95% CI {h4['ci'][0]:+.3f} to {h4['ci'][1]:+.3f}); "
              f"one-sided p = {h4['p']:.3f}", "",
              "## H5 — attention acceleration vs. the traditional model's misses (controlling for level)", "",
              f"- n = {h5['n']}; acceleration coefficient {h5['coef']:+.3f} (95% CI {h5['ci'][0]:+.3f} to "
              f"{h5['ci'][1]:+.3f}); one-sided p = {h5['p']:.3f}; level coefficient {h5['level_coef']:+.3f}", ""]
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
