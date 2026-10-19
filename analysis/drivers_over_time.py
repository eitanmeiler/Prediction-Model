#!/usr/bin/env python3
"""Headline chart: how much each traditional driver mattered, year by year (descriptive, not causal).

Per year, OLS of log opening on standardized drivers (z-scored within the year so each coefficient reads as
"change in log opening per 1 SD of that driver that year"), plus a franchise flag. Live-action films with
star & director history. 2013-2024, excluding 2020-21; 2025 stays sealed.
Theater count is a consequence of the other drivers (studios book more screens for bigger bets), so the chart
shows the model WITHOUT it; a second figure adds it.
Outputs: docs/figures/drivers_over_time.png, docs/figures/drivers_over_time_with_theaters.png, docs/drivers_over_time.csv
"""
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "model_table.csv"
FIG = ROOT / "docs" / "figures"
YEARS = [y for y in range(2013, 2025) if y not in (2020, 2021)]
# validated reference palette (dataviz skill, light mode): series slot 1 + text/grid tokens
BLUE, INK, INK2, GRID, SURFACE = "#2a78d6", "#1f1f1e", "#5f5e5a", "#e6e5e0", "#fcfcfb"
DRIVERS = {"z_star": "Star track record (per 1 SD)", "z_director": "Director track record (per 1 SD)",
           "franchise": "Franchise film (vs. not)", "z_dist": "Distributor recent record (per 1 SD)",
           "z_theaters": "Opening theater count (per 1 SD)"}


def yearly(df, with_theaters):
    rows = []
    for y in YEARS:
        g = df[df.year == y].copy()
        for src, z in (("star_mean", "z_star"), ("director_mean", "z_director"), ("dist_recent_mean", "z_dist"),
                       ("log_theaters", "z_theaters")):
            g["no_" + z] = g[src].isna().astype(float)  # no track record: separate intercept, z set to 0
            g[z] = ((g[src] - g[src].mean()) / g[src].std()).fillna(0)
        f = ("log_opening ~ z_star + no_z_star + z_director + no_z_director + z_dist + no_z_dist + franchise"
             + (" + z_theaters" if with_theaters else ""))
        m = smf.ols(f, data=g).fit(cov_type="HC3")
        for k in DRIVERS:
            if k in m.params:
                lo, hi = m.conf_int().loc[k]
                rows.append({"year": y, "driver": k, "coef": m.params[k], "lo": lo, "hi": hi, "n": int(m.nobs),
                             "with_theaters": with_theaters})
    return pd.DataFrame(rows)


def plot(res, path, title):
    drivers = [d for d in DRIVERS if d in res.driver.unique()]
    fig, axes = plt.subplots(1, len(drivers), figsize=(3.3 * len(drivers), 3.4), sharey=True, facecolor=SURFACE)
    for ax, d in zip(axes, drivers):
        r = res[res.driver == d].set_index("year").reindex(range(2013, 2025))
        ax.set_facecolor(SURFACE)
        ax.axhline(0, color=INK2, lw=1)
        ax.axvspan(2019.5, 2021.5, color=GRID, lw=0)  # excluded pandemic years
        for seg in (r.loc[2013:2019], r.loc[2022:2024]):  # no line drawn across the gap
            ax.fill_between(seg.index, seg.lo, seg.hi, color=BLUE, alpha=0.15, lw=0)
            ax.plot(seg.index, seg.coef, color=BLUE, lw=2, marker="o", ms=5, mec=SURFACE, mew=1.5)
        ax.set_title(DRIVERS[d], fontsize=9.5, color=INK, loc="left")
        ax.grid(axis="y", color=GRID, lw=0.8)
        ax.tick_params(colors=INK2, labelsize=8, length=0)
        ax.set_xticks([2013, 2016, 2019, 2022, 2024])
        for s in ax.spines.values():
            s.set_visible(False)
        ax.text(2020.5, 0.98, "2020–21\nexcluded", transform=ax.get_xaxis_transform(),
                ha="center", va="top", fontsize=7, color=INK2)
    axes[0].set_ylabel("Effect on log opening", color=INK2, fontsize=9)
    fig.suptitle(title, x=0.01, ha="left", fontsize=12, color=INK, fontweight="bold")
    fig.text(0.01, -0.02, "Each point: one year's regression; band = 95% CI. Descriptive only — associations, not causes. "
             "All live-action wide releases (films without a track record get their own baseline); 2025 sealed.", fontsize=7.5, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=SURFACE)
    plt.close(fig)


def main():
    df = pd.read_csv(TABLE)
    df = df[df.in_model & ~df.g_animation].copy()
    df["franchise"] = (df.franchise_prev_films > 0).astype(float)
    df["log_theaters"] = np.log(df.open_theaters)
    FIG.mkdir(parents=True, exist_ok=True)
    a, b = yearly(df, False), yearly(df, True)
    pd.concat([a, b]).to_csv(ROOT / "docs" / "drivers_over_time.csv", index=False)
    plot(a, FIG / "drivers_over_time.png", "What moved opening weekends, year by year (before theater counts)")
    plot(b, FIG / "drivers_over_time_with_theaters.png", "Same, once the opening theater count is known")
    print(a.pivot(index="year", columns="driver", values="coef").round(2).to_string())
    print("n per year:", a.groupby("year").n.first().to_dict())


if __name__ == "__main__":
    main()
