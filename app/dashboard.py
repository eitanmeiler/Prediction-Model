"""Prediction Model dashboard.  Run:  .venv/bin/streamlit run app/dashboard.py

Pages: upcoming forecasts · forecast vs. actual tracker · backtest accuracy · what drives openings.
Reads only files the pipeline writes; it never retrains anything.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
BLUE, ORANGE, INK2, GRID = "#2a78d6", "#eb6834", "#5f5e5a", "#e6e5e0"  # validated reference palette slots 1-2

st.set_page_config(page_title="Opening Night — box office forecasts", layout="wide")


@st.cache_data
def load(path, **kw):
    p = ROOT / path
    return pd.read_csv(p, **kw) if p.exists() else None


def money(m):
    return f"${m:,.1f}M" if pd.notna(m) else "—"


page = st.sidebar.radio("Page", ["Upcoming forecasts", "Forecast vs. actual", "Backtest accuracy",
                                 "What drives openings"])
st.sidebar.caption("Opening-weekend forecasts for US wide releases (opened in 800+ theaters). "
                   "Data: Box Office Mojo (hand-copied), TMDB, Wikipedia. "
                   "This product uses the TMDB API but is not endorsed or certified by TMDB.")

if page == "Upcoming forecasts":
    st.title("Upcoming forecasts")
    d = load("forecasts/latest_draft.csv", parse_dates=["release_date"])
    if d is None or d.empty:
        st.info("No forecasts yet — run `models/forecast_live.py`.")
        st.stop()
    if d.status.str.contains("no 2026").any():
        st.warning("Draft: the 2026 box office (current market level) isn't loaded yet, so these numbers run high. "
                   "They will not be frozen until it is.")
    st.caption("Point = primary forecast (CatBoost + attention once a film's attention window is complete, ridge before); bar = 80% range (from the model's own errors over the last 8 backtest "
               "quarters); T-28 = four weeks out (no theater count), T-7 = one week out.")
    d = d.sort_values("release_date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=d.forecast_m, y=d.title, mode="markers", marker=dict(color=BLUE, size=10, line=dict(color="white", width=2)),
        error_x=dict(type="data", symmetric=False, array=d.hi80_m - d.forecast_m,
                     arrayminus=d.forecast_m - d.lo80_m, color=BLUE, thickness=2, width=0),
        customdata=np.stack([d.lo80_m, d.hi80_m, d.checkpoint, d.release_date.dt.strftime("%b %d")], axis=1),
        hovertemplate="<b>%{y}</b> · %{customdata[3]} · %{customdata[2]}<br>forecast $%{x:.1f}M"
                      "<br>80% range $%{customdata[0]:.1f}M – $%{customdata[1]:.1f}M<extra></extra>"))
    fig.update_layout(xaxis=dict(type="log", title="Opening weekend ($M, log scale)", gridcolor=GRID),
                      yaxis=dict(autorange="reversed"), height=60 + 42 * len(d), margin=dict(l=10, r=10, t=10, b=40),
                      plot_bgcolor="white", showlegend=False)
    st.plotly_chart(fig, width="stretch")
    film = st.selectbox("Film detail", d.title)
    r = d[d.title == film].iloc[0]
    c1, c2, c3 = st.columns(3)
    c1.metric("Forecast", money(r.forecast_m), f"{r.checkpoint} · {r.get('primary_model', 'ridge')}")
    c2.metric("80% range", f"{money(r.lo80_m)} – {money(r.hi80_m)}")
    c3.metric("Ridge (traditional features)", money(r.get("ridge_m", r.forecast_m)),
              f"{money(r.get('ridge_lo80_m'))} – {money(r.get('ridge_hi80_m'))}")
    st.markdown("**Biggest pushes vs. an average film, ridge model** (log-opening units; + raises the forecast)")
    st.dataframe(pd.DataFrame([x.rsplit(" ", 1) for x in r.drivers.split("; ")], columns=["feature", "push"]),
                 hide_index=True, width="stretch")
    st.markdown("**Most similar past films** (by the features the model weighs most)")
    st.write(r.comparables.replace("; ", " · "))

elif page == "Forecast vs. actual":
    st.title("Frozen forecasts vs. what happened")
    log = load("forecasts/forecast_log.csv")
    if log is None:
        st.info("No frozen forecasts yet. Forecasts are frozen with `models/forecast_live.py --freeze` and "
                "committed to git, so they can't be quietly changed after the fact.")
        st.stop()
    act = load("data/processed/model_table.csv")[["title", "opening"]].dropna()
    m = log.merge(act, on="title", how="left")
    m["actual_m"] = m.opening / 1e6
    m["error_pct"] = (m.forecast_m / m.actual_m - 1) * 100
    m["in_range"] = (m.actual_m >= m.lo80_m) & (m.actual_m <= m.hi80_m)
    done = m.dropna(subset=["actual_m"])
    if len(done):
        c1, c2, c3 = st.columns(3)
        c1.metric("Films graded", len(done))
        c2.metric("Median miss", f"{done.error_pct.abs().median():.0f}%")
        c3.metric("Inside the 80% range", f"{done.in_range.mean() * 100:.0f}%")
    st.dataframe(m[["frozen_at_utc", "title", "checkpoint", "forecast_m", "lo80_m", "hi80_m", "actual_m",
                    "error_pct", "in_range", "git_commit"]].round(1), hide_index=True, width="stretch")

elif page == "Backtest accuracy":
    st.title("How accurate is it? (backtest 2014–2024)")
    st.caption("Retrained every quarter on past films only, then scored on the next quarter. 2020–21 excluded; "
               "2025 is a sealed holdout.")
    bt = load("data/processed/backtest_predictions.csv")
    bt["ratio"] = np.exp(bt.pred - bt.actual)
    cp = st.radio("Checkpoint", ["T-7", "T-28"], horizontal=True)
    g = bt[bt.checkpoint == cp]
    summ = g.groupby("model").apply(lambda x: pd.Series({
        "typical miss": f"{np.median(np.abs(x.ratio - 1)) * 100:.0f}%",
        "within ±25%": f"{np.mean(np.abs(x.ratio - 1) <= 0.25) * 100:.0f}%",
        "80% range coverage": f"{((x.actual >= x.lo80) & (x.actual <= x.hi80))[x.lo80.notna()].mean() * 100:.0f}%"}))
    st.dataframe(summ, width="stretch")
    yearly = g.groupby(["year", "model"]).apply(lambda x: np.median(np.abs(x.ratio - 1)) * 100).unstack()
    fig = go.Figure()
    for name, color in (("ridge", BLUE), ("comps", ORANGE)):
        fig.add_trace(go.Scatter(x=yearly.index, y=yearly[name], name=name, mode="lines+markers",
                                 line=dict(color=color, width=2), marker=dict(size=8),
                                 hovertemplate="%{x}: typical miss %{y:.0f}%<extra>" + name + "</extra>"))
    fig.update_layout(yaxis=dict(title="Typical miss (%)", gridcolor=GRID, rangemode="tozero"),
                      xaxis=dict(dtick=1), plot_bgcolor="white", height=360, margin=dict(t=10, b=30),
                      legend=dict(orientation="h", y=1.08))
    st.plotly_chart(fig, width="stretch")
    st.markdown((ROOT / "docs" / "backtest_summary.md").read_text().split("## Is CatBoost")[1].join(
        ["**Is CatBoost better than ridge?**", ""]))

else:
    st.title("What drives openings — and has it changed?")
    st.image(str(ROOT / "docs" / "figures" / "drivers_over_time.png"), width="stretch")
    st.caption("Descriptive: associations, not causes. Theater count is left out here because studios set it "
               "partly based on the other drivers.")
    with st.expander("Same chart once the opening theater count is known"):
        st.image(str(ROOT / "docs" / "figures" / "drivers_over_time_with_theaters.png"), width="stretch")
    for f in ("docs/hypothesis_results_dev.md", "docs/attention_results_dev.md"):
        p = ROOT / f
        if p.exists():
            with st.expander(p.stem.replace("_", " ").capitalize()):
                st.markdown(p.read_text())
