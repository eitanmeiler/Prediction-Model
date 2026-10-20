#!/usr/bin/env python3
"""Matches every film in data/interim/films.csv to TMDB and pulls metadata.

Match: TMDB search by title + year, scored on title similarity and distance between TMDB's US theatrical date
(or primary date) and the Box Office Mojo opening date. One details call per film (credits, keywords,
release_dates appended). Every response is cached in data/cache/tmdb/, so reruns make no network calls.
Output: data/interim/tmdb.csv (+ data/interim/tmdb_unmatched.csv for hand review).
The API key is read from .env and never written to disk or printed.
"""
import difflib
import hashlib
import json
import re
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
FILMS = ROOT / "data" / "interim" / "films.csv"
OUT = ROOT / "data" / "interim" / "tmdb.csv"
UNMATCHED = ROOT / "data" / "interim" / "tmdb_unmatched.csv"
CACHE = ROOT / "data" / "cache" / "tmdb"
API = "https://api.themoviedb.org/3"
KEY = dotenv_values(ROOT / ".env").get("TMDB_API_KEY", "")

# TMDB keyword names that mark the source of a film's story
SOURCE_KEYWORDS = {
    "src_novel": ("based on novel or book", "based on young adult novel", "based on short story"),
    "src_comic": ("based on comic", "based on graphic novel", "superhero", "marvel cinematic universe (mcu)", "dc extended universe (dceu)"),
    "src_game": ("based on video game",),
    "src_true_story": ("based on true story", "biography", "based on real person"),
    "src_toy_tv": ("based on toy", "based on tv series", "based on cartoon", "based on children's book"),
    "remake": ("remake",),
    "sequel": ("sequel",),
}


# BOM title -> (TMDB search title, search year) where the two sites name a film differently
ALT_TITLES = {
    "The Divergent Series: Insurgent": ("Insurgent", 2015),
    "The Divergent Series: Allegiant": ("Allegiant", 2016),
    "Star Wars: Episode VII - The Force Awakens": ("Star Wars: The Force Awakens", 2015),
    "Star Wars: Episode VIII - The Last Jedi": ("Star Wars: The Last Jedi", 2017),
    "Star Wars: Episode IX - The Rise of Skywalker": ("Star Wars: The Rise of Skywalker", 2019),
    "The Brothers Grimsby": ("Grimsby", 2016),
    "X-Men: Dark Phoenix": ("Dark Phoenix", 2019),
    "The Expendables 4": ("Expend4bles", 2023),
    "Star Wars: The Mandalorian and Grogu": ("The Mandalorian and Grogu", 2026),
    "Pushpa: The Rule - Part 2": ("Pushpa 2: The Rule", 2024),
    "Atlas Shrugged II: The Strike": ("Atlas Shrugged: Part II", 2012),
    "The Christmas Ring": ("Karen Kingsbury's The Christmas Ring", 2025),
    "The Secret World of Arrietty": ("Arrietty", 2010),
    "The Pirates! Band of Misfits": ("The Pirates! In an Adventure with Scientists!", 2012),
    "The Wild Life": ("Robinson Crusoe", 2016),
    "Profile": ("Profile", 2018),
    "The Cursed": ("Eight for Silver", 2021),
}
# Checked by hand (2026-10-19): TMDB's search ranks the wrong film first, or its dates are off
FORCE_ID = {
    "20121102_flight": 87502, "20220114_belle": 776305, "20240112_soul": 508442, "20200918_infidel": 649401,
    "20230421_the_covenant": 882569, "20170224_collide": 195590, "20220218_the_cursed": 630392,
    "20241122_bonhoeffer": 1079244,
    "20260206_dracula": 1246049,  # Luc Besson; French release 2025, US (Vertical) Feb 6 2026
    "20151204_the_letters": 218275, "20170127_gold": 334524, "20240315_one_life": 760774,
    "20240524_sight": 1057006, "20150417_unfriended": 277685,  # same-title foreign films ranked first
    "20120120_haywire": 70435, "20181124_pok_mon_the_movie_the_power_of_us": 494407,  # correct, TMDB has no US date
}
# Correct title match, but TMDB's dates are years off (shelved films, festival premieres, a re-cut released later)
DATE_OK = {"20101001_case_39", "20120309_silent_house", "20251205_kill_bill_the_whole_bloody_affair"}


def get(path, **params):
    key = hashlib.sha1(json.dumps([path, sorted(params.items())]).encode()).hexdigest()
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    for attempt in range(5):
        r = requests.get(API + path, params={**params, "api_key": KEY}, timeout=20)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 * (attempt + 1))
            continue
        if r.status_code == 404:
            return None
        r.raise_for_status()
        data = r.json()
        f.write_text(json.dumps(data))
        time.sleep(0.03)
        return data
    raise RuntimeError(f"TMDB kept failing for {path}")


def norm(s, drop_articles=True):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    s = s.replace("&", "and")
    if drop_articles:
        s = re.sub(r"\b(the|a|an)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def similarity(a, b):
    raw_a, raw_b = a, b
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a == b:
        # "Spiral" vs "The Spiral" are different films: full credit only if equal with articles kept
        return 1.0 if norm(raw_a, False) == norm(raw_b, False) else 0.95
    # BOM often drops/adds subtitles ("Mission: Impossible - Fallout"); credit prefix matches
    short, long_ = sorted((a, b), key=len)
    if long_.startswith(short + " "):
        # subtitle added/dropped ("F9" vs "F9: The Fast Saga"); one-word stems are risky ("Belle" vs "Belle River")
        return 0.9 if " " in short else 0.89
    return difflib.SequenceMatcher(None, a, b).ratio()


def us_theatrical(details):
    for c in (details.get("release_dates") or {}).get("results", []):
        if c.get("iso_3166_1") == "US":
            dates = sorted(d["release_date"][:10] for d in c["release_dates"] if d.get("type") in (2, 3))
            cert = next((d.get("certification") for d in c["release_dates"] if d.get("certification")), None)
            return (dates[0] if dates else None), cert
    return None, None


def candidates(title, year):
    seen, out = set(), []
    for params in ({"year": year}, {"year": year - 1}, {}):
        res = get("/search/movie", query=title, include_adult="false", **params) or {}
        for m in res.get("results", [])[:8]:
            if m["id"] not in seen:
                seen.add(m["id"])
                out.append(m)
        if any(similarity(title, m.get("title", "")) >= 0.9 for m in out):
            break
    return out


def best_match(row):
    bom_date = pd.Timestamp(row.release_date)
    if row.film_id in FORCE_ID:
        details = get(f"/movie/{FORCE_ID[row.film_id]}", append_to_response="credits,keywords,release_dates")
        us_date, cert = us_theatrical(details)
        days = abs((pd.Timestamp(us_date) - bom_date).days) if us_date else None
        return details, 1.0, days, us_date, cert, True
    title, year = ALT_TITLES.get(row.title, (row.title, row.year))
    scored = []
    for m in candidates(title, year):
        sim = max(similarity(title, m.get("title", "")), similarity(title, m.get("original_title", "")))
        if sim < 0.6:
            continue
        rd = m.get("release_date") or ""
        days = abs((pd.Timestamp(rd) - bom_date).days) if rd else 999
        scored.append((sim - min(days, 400) / 400 * 0.5 + min(m.get("popularity", 0), 100) / 2000, sim, days, m["id"]))
    if not scored:
        return None
    score, sim, days, tmdb_id = max(scored)
    details = get(f"/movie/{tmdb_id}", append_to_response="credits,keywords,release_dates")
    us_date, cert = us_theatrical(details)
    if us_date:
        days = abs((pd.Timestamp(us_date) - bom_date).days)
    # accept close titles with a nearby date; very exact titles may have TMDB date quirks (festival premieres)
    if us_date is None and days > 45:  # no US release on record + far-off date = usually a same-title foreign film
        return details, sim, days, us_date, cert, False
    if (sim == 0.95 and days > 3) or (sim == 0.89 and days > 1):  # loose title matches need an exact date
        return details, sim, days, us_date, cert, False
    ok = (sim >= 0.85 and days <= 45) or (sim == 1.0 and days <= 400) or (sim == 1.0 and row.film_id in DATE_OK) \
        or (row.title in ALT_TITLES and sim >= 0.9)
    return details, sim, days, us_date, cert, ok


def flatten(film_id, details, sim, days, us_date, cert):
    credits = details.get("credits") or {}
    cast = sorted(credits.get("cast", []), key=lambda c: c.get("order", 99))[:3]
    directors = [c for c in credits.get("crew", []) if c.get("job") == "Director"]
    kws = {k["name"].lower() for k in (details.get("keywords") or {}).get("keywords", [])}
    coll = details.get("belongs_to_collection") or {}
    row = {
        "film_id": film_id,
        "tmdb_id": details["id"],
        "tmdb_title": details.get("title"),
        "match_title_sim": round(sim, 3),
        "match_days_off": days,
        "us_release_date": us_date,
        "mpaa": cert,
        "genres": "|".join(g["name"] for g in details.get("genres", [])),
        "runtime": details.get("runtime") or None,
        "budget": details.get("budget") or None,  # 0 in TMDB means unknown
        "original_language": details.get("original_language"),
        "collection_id": coll.get("id"),
        "collection_name": coll.get("name"),
        "production_companies": "|".join(c["name"] for c in details.get("production_companies", [])[:5]),
        "cast_ids": "|".join(str(c["id"]) for c in cast),
        "cast_names": "|".join(c["name"] for c in cast),
        "director_ids": "|".join(str(d["id"]) for d in directors),
        "director_names": "|".join(d["name"] for d in directors),
        "keywords": "|".join(sorted(kws)),
    }
    for flag, names in SOURCE_KEYWORDS.items():
        row[flag] = any(n in kws for n in names)
    return row


def main():
    if not KEY:
        raise SystemExit("TMDB_API_KEY missing from .env")
    CACHE.mkdir(parents=True, exist_ok=True)
    films = pd.read_csv(FILMS)
    rows, misses = [], []
    for i, f in enumerate(films.itertuples(), 1):
        res = best_match(f)
        if res and res[-1]:
            rows.append(flatten(f.film_id, *res[:-1]))
        else:
            misses.append({"film_id": f.film_id, "title": f.title, "year": f.year,
                           "best_guess": res[0].get("title") if res else None,
                           "title_sim": round(res[1], 3) if res else None, "days_off": res[2] if res else None})
        if i % 200 == 0:
            print(f"  {i}/{len(films)} processed, {len(misses)} unmatched", flush=True)
    pd.DataFrame(rows).to_csv(OUT, index=False)
    pd.DataFrame(misses).to_csv(UNMATCHED, index=False)
    print(f"matched {len(rows)}/{len(films)} ({len(rows) / len(films):.1%}); {len(misses)} to review in {UNMATCHED.name}")


if __name__ == "__main__":
    main()
