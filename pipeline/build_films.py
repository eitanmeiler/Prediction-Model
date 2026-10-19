#!/usr/bin/env python3
"""Builds the master film list from the Box Office Mojo 'In-year releases' tables (data/raw/boxoffice/<year>.tsv).

Population (HYPOTHESES.md, Amendment 2): films that OPENED in >= 800 theaters, 2010-2025.
Re-releases are dropped; event cinema (concerts, Fathom one-nights, TV episodes) is kept but flagged so models
can exclude it. Output: data/interim/films.csv
"""
import io
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "boxoffice"
OUT = ROOT / "data" / "interim" / "films.csv"
MIN_OPEN_THEATERS = 800

RERELEASE = re.compile(r"re-?release|anniversary|\b3d release\b|special edition|double bill|triple bill|"
                       r"extended cut|pg-13 version|original release|\bimax\b|studio ghibli fest|encore", re.I)
EVENT_DISTRIBUTORS = {"Fathom Events", "Trafalgar Releasing", "AMC Theatres", "Iconic Events Releasing"}
EVENT_TITLE = re.compile(r"concert|live viewing|\blive\b|world tour|\btour\b(?!nament)|the chosen|in cinemas|broadway|musical live|"
                         r"metropolitan opera|national theatre|sight & sound presents|cirque du soleil", re.I)


def money(s):
    return pd.to_numeric(s.astype(str).str.replace(r"[$,%]", "", regex=True), errors="coerce")


def load_year(year):
    lines = (RAW / f"{year}.tsv").read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith("Rank\t"))
    df = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep="\t", dtype=str)
    df = df[df["Rank"].str.strip().str.isdigit()]
    out = pd.DataFrame({
        "year": year,
        "title": df["Release"].str.strip(),
        "distributor": df["Distributor"].str.strip().replace("-", pd.NA),
        "domestic_total": money(df["Gross"]),
        "max_theaters": money(df["Max Th"]),
        "opening": money(df["Opening"]),
        "open_theaters": money(df["Open Th"]),
        "release_date": pd.to_datetime(df["Open"].str.strip() + f" {year}", format="%b %d %Y", errors="coerce"),
        "bom_estimated": df["Estimated"].str.strip().eq("true"),
    })
    return out


def main():
    years = [y for y in range(2010, 2027) if (RAW / f"{y}.tsv").exists()]  # 2026 = current year, partial
    films = pd.concat([load_year(y) for y in years], ignore_index=True)
    total = len(films)
    films["rerelease"] = films["title"].str.contains(RERELEASE)
    films["event"] = films["distributor"].isin(EVENT_DISTRIBUTORS) | films["title"].str.contains(EVENT_TITLE)
    wide = films[(films["open_theaters"] >= MIN_OPEN_THEATERS) & ~films["rerelease"]].copy()
    wide = wide.sort_values(["release_date", "title"]).reset_index(drop=True)
    wide.insert(0, "film_id", [f"{d:%Y%m%d}_{re.sub(r'[^a-z0-9]+', '_', t.lower()).strip('_')[:40]}"
                                for d, t in zip(wide["release_date"], wide["title"])])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    wide.to_csv(OUT, index=False)

    print(f"{total} rows read; {len(wide)} wide releases kept (opened in {MIN_OPEN_THEATERS}+ theaters, re-releases dropped)")
    summary = wide.groupby("year").agg(films=("title", "size"), events=("event", "sum"),
                                       median_opening_m=("opening", lambda s: round(s.median() / 1e6, 1)))
    print(summary.to_string())
    print(f"missing release dates: {wide['release_date'].isna().sum()}, missing openings: {wide['opening'].isna().sum()}")


if __name__ == "__main__":
    main()
