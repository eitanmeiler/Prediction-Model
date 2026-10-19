#!/usr/bin/env python3
"""Builds the modeling table: one row per wide release, only information knowable before its opening.

Every "track record" feature (stars, director, franchise, distributor) is computed from films that opened
strictly before the film's own release date, so no future information leaks in.
Output: data/processed/model_table.csv
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FILMS = ROOT / "data" / "interim" / "films.csv"
TMDB = ROOT / "data" / "interim" / "tmdb.csv"
OUT = ROOT / "data" / "processed" / "model_table.csv"

STAR_WINDOW_YEARS = 5
KNOWN_LAG = pd.Timedelta(days=7)  # forecasts are made a week out: only openings at least 7 days old count
MAJORS = {
    "Walt Disney Studios Motion Pictures": "Disney", "Warner Bros.": "Warner", "Universal Pictures": "Universal",
    "Sony Pictures Releasing": "Sony", "Columbia Pictures": "Sony", "TriStar Pictures": "Sony", "Screen Gems": "Sony",
    "Paramount Pictures": "Paramount", "20th Century Fox": "Fox", "20th Century Studios": "Fox",
    "Lionsgate": "Lionsgate", "Summit Entertainment": "Lionsgate",
    "Amazon MGM Studios": "Amazon MGM", "Metro-Goldwyn-Mayer (MGM)": "Amazon MGM", "United Artists Releasing": "Amazon MGM",
}
STREAMING_FIRST = {"Soul", "Turning Red", "Luca", "KPop Demon Hunters", "Kill Bill: The Whole Bloody Affair"}
GENRES = ["Action", "Adventure", "Animation", "Comedy", "Crime", "Documentary", "Drama", "Family", "Fantasy",
          "History", "Horror", "Music", "Mystery", "Romance", "Science Fiction", "Thriller", "War", "Western"]


def holiday_flags(d):
    """Opening weekends that overlap the big US holiday frames."""
    y = d.year
    memorial = max(pd.date_range(f"{y}-05-01", f"{y}-05-31", freq="W-MON"))
    thanksgiving = pd.date_range(f"{y}-11-01", f"{y}-11-30", freq="W-THU")[3]
    labor = pd.date_range(f"{y}-09-01", f"{y}-09-30", freq="W-MON")[0]
    near = lambda h, before=4, after=1: (h - pd.Timedelta(days=before)) <= d <= (h + pd.Timedelta(days=after))
    return {
        "hol_memorial": near(memorial),
        "hol_july4": near(pd.Timestamp(f"{y}-07-04"), 4, 2),
        "hol_labor": near(labor),
        "hol_thanksgiving": near(thanksgiving, 2, 2),
        "hol_christmas": pd.Timestamp(f"{y}-12-18") <= d <= pd.Timestamp(f"{y}-12-31"),
        "hol_presidents_mlk": d.month in (1, 2) and d.weekday() == 4 and (15 <= d.day <= 21),
    }


def prior_track_record(df, people_col, name):
    """For each film: mean log opening and count of the listed people's earlier films (last N years)."""
    rows = []
    hist = {}  # person -> list of (date, log_opening)
    for r in df.sort_values("release_date").itertuples():
        people = [p for p in str(getattr(r, people_col)).split("|") if p and p != "nan"]
        window_start = r.release_date - pd.DateOffset(years=STAR_WINDOW_YEARS)
        per_person = []
        for p in people:
            past = [lo for dt, lo in hist.get(p, []) if window_start <= dt <= r.release_date - KNOWN_LAG]
            if past:
                per_person.append((np.mean(past), len(past), max(past)))
        rows.append({
            "film_id": r.film_id,
            f"{name}_mean": np.mean([x[0] for x in per_person]) if per_person else np.nan,
            f"{name}_best": max([x[2] for x in per_person]) if per_person else np.nan,
            f"{name}_films": sum(x[1] for x in per_person),
            f"{name}_n_with_history": len(per_person),
        })
        if pd.notna(r.log_opening):  # upcoming films have no opening yet
            for p in people:
                hist.setdefault(p, []).append((r.release_date, r.log_opening))
    return pd.DataFrame(rows)


def franchise_record(df):
    rows, hist = [], {}
    for r in df.sort_values("release_date").itertuples():
        cid = r.collection_id
        past = [lo for dt, lo in hist.get(cid, []) if dt <= r.release_date - KNOWN_LAG] if pd.notna(cid) else []
        rows.append({"film_id": r.film_id,
                     "franchise_prev_films": len(past),
                     "franchise_prev_mean": np.mean(past) if past else np.nan,
                     "franchise_prev_last": past[-1] if past else np.nan})
        if pd.notna(cid) and pd.notna(r.log_opening):
            hist.setdefault(cid, []).append((r.release_date, r.log_opening))
    return pd.DataFrame(rows)


def competition(df):
    """Other wide releases opening the same weekend, and recent openers still in theaters."""
    d = df[["film_id", "release_date", "log_opening", "open_theaters"]].copy()
    d["wkend"] = d["release_date"].dt.to_period("W-THU")
    rows = []
    for r in d.itertuples():
        same = d[(d.wkend == r.wkend) & (d.film_id != r.film_id)]
        # openers 5-19 days earlier: their opening weekends are reported before this film's forecast
        recent = d[(d.release_date <= r.release_date - pd.Timedelta(days=5)) & (d.release_date >= r.release_date - pd.Timedelta(days=19))]
        rows.append({"film_id": r.film_id,
                     "comp_same_wkend_n": len(same),
                     "comp_same_wkend_theaters": same.open_theaters.sum(),
                     # openings of the last two weeks' films are known by this film's release date
                     "comp_recent_open_sum": np.log1p(np.expm1(recent.log_opening).sum()),
                     "comp_recent_max": recent.log_opening.max() if len(recent) else np.nan})
    return pd.DataFrame(rows)


def main():
    films = pd.read_csv(FILMS, parse_dates=["release_date"])
    tmdb = pd.read_csv(TMDB)
    df = films.merge(tmdb, on="film_id", how="left")
    df["upcoming"] = False
    up_file = ROOT / "data" / "interim" / "upcoming.csv"
    if up_file.exists():  # future releases: same features, no opening yet
        up = pd.read_csv(up_file, parse_dates=["release_date"])
        up = up[~up.film_id.isin(df.film_id)]
        df = pd.concat([df, up], ignore_index=True)
    df["log_opening"] = np.log(df["opening"])
    df["matched"] = df["tmdb_id"].notna()

    # calendar
    df["month"] = df.release_date.dt.month
    df["weekofyear"] = df.release_date.dt.isocalendar().week.astype(int)
    df["opens_weekday"] = df.release_date.dt.weekday  # 4 = Friday; 2 = Wednesday (holiday openers)
    hol = pd.DataFrame([holiday_flags(d) for d in df.release_date])
    df = pd.concat([df, hol], axis=1)

    # film attributes
    for g in GENRES:
        df["g_" + g.lower().replace(" ", "_")] = df["genres"].fillna("").str.split("|").apply(lambda gs: g in gs)
    df["mpaa"] = df["mpaa"].where(df["mpaa"].isin(["G", "PG", "PG-13", "R"]), "Other")
    df["log_budget"] = np.log(df["budget"].where(df["budget"] >= 1e5))
    df["budget_known"] = df["log_budget"].notna()
    df["english"] = df["original_language"].eq("en")
    df["studio"] = df["distributor"].map(MAJORS).fillna("Other")
    df["in_collection"] = df["collection_id"].notna()
    # premiered on streaming (or as a re-cut) years before this theatrical run: not a normal opening
    df["late_theatrical"] = df["title"].isin(STREAMING_FIRST)

    base = df[df["matched"]].copy()
    feats = [prior_track_record(base, "cast_ids", "star"),
             prior_track_record(base, "director_ids", "director"),
             franchise_record(base),
             competition(df)]
    for f in feats:
        df = df.merge(f, on="film_id", how="left")
    # pre-registered: star power is undefined for animated films (voice casts) -> missing
    anim = df["g_animation"].astype(bool)
    df.loc[anim, ["star_mean", "star_best"]] = np.nan
    df.loc[anim, ["star_films", "star_n_with_history"]] = 0
    df["sequel_like"] = df["sequel"].fillna(False) | (df["franchise_prev_films"] > 0)
    # distributor's recent track record (last 2 years of its wide openings, before this film)
    dist = []
    for r in df.sort_values("release_date").itertuples():
        past = df[(df.distributor == r.distributor) & (df.release_date <= r.release_date - KNOWN_LAG)
                  & (df.release_date >= r.release_date - pd.DateOffset(years=2))]
        dist.append({"film_id": r.film_id, "dist_recent_mean": past.log_opening.mean() if len(past) else np.nan,
                     "dist_recent_n": len(past)})
    df = df.merge(pd.DataFrame(dist), on="film_id", how="left")

    # current market level: median opening of non-event wide releases 7-97 days earlier (all known at forecast time)
    mk = df[~df["event"]][["release_date", "log_opening"]]
    lvl = []
    for d in df.release_date:
        w = mk[(mk.release_date <= d - KNOWN_LAG) & (mk.release_date >= d - pd.Timedelta(days=97))]
        lvl.append((w.log_opening.median() if len(w) >= 5 else np.nan, len(w)))
    df["mkt_recent_median"], df["mkt_recent_n"] = zip(*lvl)

    df["period"] = np.select([df.year <= 2019, df.year <= 2021, df.year <= 2025], ["pre", "covid", "post"], default="other")
    df["in_model"] = ~df["upcoming"].astype(bool) & df["matched"] & ~df["event"].astype(bool) & ~df["late_theatrical"] & df["opening"].gt(0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"{len(df)} films, {df.in_model.sum()} usable for modeling; {df.shape[1]} columns -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
