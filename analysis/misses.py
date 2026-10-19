#!/usr/bin/env python3
"""The films the traditional model missed most (T-7 ridge backtest, 2014-2024): starting list for case studies.
Output: docs/biggest_misses.md
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
bt = pd.read_csv(ROOT / "data/processed/backtest_predictions.csv")
t = pd.read_csv(ROOT / "data/processed/model_table.csv")
b = bt[(bt.checkpoint == "T-7") & (bt.model == "ridge")].merge(
    t[["film_id", "genres", "distributor", "open_theaters", "sequel_like", "src_novel", "src_comic", "src_game",
       "src_true_story", "g_horror", "g_animation"]], on="film_id")
b["actual_m"], b["pred_m"] = np.exp(b.actual) / 1e6, np.exp(b.pred) / 1e6
b["times"] = np.exp(b.err)


def table(d):
    return d[["title", "year", "distributor", "pred_m", "actual_m", "times", "genres"]].round(
        {"pred_m": 1, "actual_m": 1, "times": 2}).to_markdown(index=False)


over = b.sort_values("err", ascending=False).head(15)
under = b.sort_values("err").head(15)
share = lambda col: (b.assign(o=b.err > np.log(1.5), u=b.err < -np.log(1.5))
                     .groupby(col)[["o", "u"]].mean().mul(100).round(0))
lines = ["# Biggest misses (T-7, ridge backtest 2014-2024)", "",
         "`times` = actual ÷ forecast. These are the starting list for case studies — patterns here are hypotheses, "
         "not findings.", "", "## Outperformed the forecast most", "", table(over), "",
         "## Underperformed the forecast most", "", table(under), "",
         "## Who beats / misses the forecast by 50%+ (share of films, %)", ""]
for col, label in (("g_horror", "Horror"), ("g_animation", "Animation"), ("sequel_like", "Sequel/franchise"),
                   ("src_game", "Video-game adaptation"), ("src_comic", "Comic adaptation"),
                   ("src_true_story", "True story")):
    s = share(col)
    if True in s.index:
        lines.append(f"- {label}: beat by 50%+ {s.loc[True, 'o']:.0f}% vs {s.loc[False, 'o']:.0f}% of other films; "
                     f"missed by 50%+ {s.loc[True, 'u']:.0f}% vs {s.loc[False, 'u']:.0f}%")
(ROOT / "docs/biggest_misses.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
