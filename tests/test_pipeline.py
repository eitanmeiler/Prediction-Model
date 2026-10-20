"""Checks that would silently ruin the project if they broke.  Run:  .venv/bin/python -m pytest tests -q"""
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "model_table.csv"


@pytest.fixture(scope="module")
def df():
    return pd.read_csv(TABLE, parse_dates=["release_date"])


@pytest.fixture(scope="module")
def hist(df):
    return df[~df.upcoming.astype(bool)]


# ---------- data integrity ----------
def test_no_duplicate_films(hist):
    assert not hist.film_id.duplicated().any()
    assert not hist.tmdb_id.dropna().duplicated().any(), "one TMDB film matched to two box office rows"


def test_population_rule(hist):
    assert (hist.open_theaters >= 800).all()
    assert not hist.rerelease.astype(bool).any()


def test_opening_not_above_total(hist):
    h = hist.dropna(subset=["opening", "domestic_total"])
    bad = h[h.opening > h.domestic_total * 1.01]
    assert len(bad) == 0, bad[["title", "opening", "domestic_total"]].to_string()


def test_open_theaters_not_above_max(hist):
    bad = hist[hist.open_theaters > hist.max_theaters]
    assert len(bad) == 0, bad[["title", "open_theaters", "max_theaters"]].to_string()


def test_release_year_matches_table(hist):
    assert (hist.release_date.dt.year == hist.year).all()


# ---------- leakage ----------
def test_star_track_record_uses_only_earlier_films(df, hist):
    """Recompute star_mean for random films from scratch and compare."""
    rng = np.random.default_rng(1)
    sample = hist[hist.star_mean.notna()].sample(40, random_state=1)
    matched = hist[hist.tmdb_id.notna()]
    for r in sample.itertuples():
        cast = str(r.cast_ids).split("|")
        means = []
        for person in cast:
            prior = matched[(matched.cast_ids.fillna("").str.split("|").apply(lambda c: person in c))
                            & (matched.release_date <= r.release_date - pd.Timedelta(days=7))
                            & (matched.release_date >= r.release_date - pd.DateOffset(years=5))]
            if len(prior):
                means.append(prior.log_opening.mean())
        assert means, f"{r.title}: star_mean set but no qualifying earlier films"
        assert abs(np.mean(means) - r.star_mean) < 1e-6, f"{r.title}: star_mean {r.star_mean} != recomputed {np.mean(means)}"


def test_no_feature_from_the_future(df):
    """A film's own opening must not appear in any track-record feature: perturbing it can't be detected here,
    so instead check the ordering rule on franchise counts."""
    h = df[df.collection_id.notna() & ~df.upcoming.astype(bool)].sort_values("release_date")
    for cid, g in h.groupby("collection_id"):
        g = g.reset_index(drop=True)
        for i, r in g.iterrows():
            earlier = g[g.release_date <= r.release_date - pd.Timedelta(days=7)]
            assert r.franchise_prev_films == len(earlier), f"{r.title}: franchise count {r.franchise_prev_films} vs {len(earlier)}"


def test_backtest_trains_only_on_past():
    bt = pd.read_csv(ROOT / "data" / "processed" / "backtest_predictions.csv")
    assert bt.year.max() <= 2024, "backtest touched sealed/live years"
    assert not bt.year.isin([2020, 2021]).any()


# ---------- secrets ----------
def test_no_api_keys_in_git():
    env = (ROOT / ".env").read_text() if (ROOT / ".env").exists() else ""
    keys = [line.split("=", 1)[1].strip() for line in env.splitlines() if "=" in line and line.split("=", 1)[1].strip()]
    tracked = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=ROOT).stdout.split()
    assert ".env" not in tracked
    for k in keys:
        log = subprocess.run(["git", "log", "-p", "--all", "-S", k, "--oneline"], capture_output=True, text=True, cwd=ROOT)
        assert log.stdout.strip() == "", "an API key appears in git history"
