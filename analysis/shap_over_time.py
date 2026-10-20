#!/usr/bin/env python3
"""What the forecasting model actually leans on, year by year (SHAP).

For each year Y in 2017-2025 (excl. 2020-21): train CatBoost + attention (T-7 features) on 2016..Y-1 films, compute
SHAP values for year Y's films, and report each feature group's share of total |SHAP| (how much of the forecast's
movement away from the average film that group explains). Descriptive.
Outputs: docs/shap_over_time.csv, docs/figures/shap_over_time.png
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor, Pool

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "models"))
from feature_sets import ATTENTION, CATEGORICAL, checkpoint_features  # noqa: E402

GROUPS = {
    "Theater count & competition": ["open_theaters", "comp_same_wkend_n", "comp_same_wkend_theaters", "comp_recent_open_sum", "comp_recent_max"],
    "Franchise & source": ["in_collection", "sequel_like", "franchise_prev_films", "franchise_prev_mean", "franchise_prev_last",
                           "src_novel", "src_comic", "src_game", "src_true_story", "src_toy_tv", "remake"],
    "Talent (stars, director)": ["star_mean", "star_best", "star_films", "star_n_with_history", "director_mean", "director_films"],
    "Distributor & studio": ["dist_recent_mean", "dist_recent_n", "studio"],
    "Audience attention": ATTENTION,
    "Market level & timing": ["mkt_recent_median", "month", "weekofyear", "opens_weekday", "hol_memorial", "hol_july4", "hol_labor",
                              "hol_thanksgiving", "hol_christmas", "hol_presidents_mlk"],
}
BLUE, INK, INK2, GRID, SURFACE = "#2a78d6", "#1f1f1e", "#5f5e5a", "#e6e5e0", "#fcfcfb"


def main():
    df = pd.read_csv(ROOT / "data/processed/model_table.csv", parse_dates=["release_date"])
    df = df[df.in_model & ~df.year.isin([2020, 2021]) & df.year.between(2016, 2025)].copy()
    df["primary_genre"] = df.genres.fillna("Unknown").str.split("|").str[0]
    feats = checkpoint_features("T-7") + ATTENTION
    cat = [f for f in feats if f in CATEGORICAL]
    X = lambda d: d[feats].assign(**{c: d[c].astype(str) for c in cat})
    group_of = {f: g for g, fs in GROUPS.items() for f in fs}
    rows = []
    for y in [y for y in range(2017, 2026) if y not in (2020, 2021)]:
        tr, te = df[df.year < y], df[df.year == y]
        m = CatBoostRegressor(iterations=700, depth=6, learning_rate=0.05, random_seed=7, verbose=False, cat_features=cat)
        m.fit(X(tr), tr.log_opening)
        sv = m.get_feature_importance(Pool(X(te), cat_features=cat), type="ShapValues")[:, :-1]
        imp = pd.Series(np.abs(sv).mean(axis=0), index=feats)
        share = imp.groupby(lambda f: group_of.get(f, "Genre, rating & other")).sum()
        share = share / share.sum()
        rows += [{"year": y, "group": g, "share": v} for g, v in share.items()]
        print(f"  {y}: trained on {len(tr)}, explained {len(te)}", flush=True)
    res = pd.DataFrame(rows)
    res.to_csv(ROOT / "docs/shap_over_time.csv", index=False)
    piv = res.pivot(index="year", columns="group", values="share")
    print((piv * 100).round(1).to_string())

    order = list(GROUPS) + ["Genre, rating & other"]
    fig, axes = plt.subplots(2, 4, figsize=(13, 5.6), sharey=True, facecolor=SURFACE)
    for ax, g in zip(axes.ravel(), order):
        s = piv[g] * 100
        ax.set_facecolor(SURFACE)
        ax.axvspan(2019.5, 2021.5, color=GRID, lw=0)
        for seg in (s.loc[:2019], s.loc[2022:]):
            ax.plot(seg.index, seg.values, color=BLUE, lw=2, marker="o", ms=5, mec=SURFACE, mew=1.5)
        ax.set_title(g, fontsize=9.5, color=INK, loc="left")
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.tick_params(colors=INK2, labelsize=8, length=0)
        ax.set_xticks([2017, 2019, 2022, 2025])
        for sp in ax.spines.values():
            sp.set_visible(False)
    axes.ravel()[-1].axis("off")
    for ax in axes[:, 0]:
        ax.set_ylabel("Share of the forecast (%)", color=INK2, fontsize=9)
    fig.suptitle("What the forecasting model leans on, year by year", x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.text(0.01, -0.01, "Share of mean |SHAP| by feature group, CatBoost + attention, one week before release; each year explained by a model "
             "trained only on earlier years (2016+). 2020-21 excluded.", fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(ROOT / "docs/figures/shap_over_time.png", dpi=180, bbox_inches="tight", facecolor=SURFACE)


if __name__ == "__main__":
    main()
