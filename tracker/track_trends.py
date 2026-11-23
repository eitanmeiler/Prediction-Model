#!/usr/bin/env python3
"""Google Trends search interest for films, a free proxy for presale demand (see HYPOTHESES.md Amendment 9, next step).

Google normalises every query to 0-100 within itself, so each film is queried together with a fixed anchor term
("Fandango", ticket buying). The film/anchor ratio is then comparable across films and years.
Each film is queried as Google's film *topic* (e.g. /m/0t_7k4v = Star Wars: The Last Jedi, 2017 film), which pools
every way people search for it ("dune 3", "dune part three"). Topic ids are looked up once and cached in
data/trends/topics.json; a film with no matching topic falls back to its title as a search term (kind "term").

  daily:    .venv/bin/python tracker/track_trends.py
            snapshot of every upcoming film (tracker/upcoming.json) opening in the next 70 days
            -> data/trends/daily/<today>.csv  (US, last 90 days, daily values)
  history:  .venv/bin/python tracker/track_trends.py --history [--limit N]
            the 63 days before release for past films in the model table (2016-2025), one file per film,
            resumable -> data/trends/history/<film_id>.csv. Slow on purpose (Google rate-limits).

Exploratory data collection only: nothing here feeds the live model. A Trends feature enters the model only through
a new pre-registered amendment, backtested on this history first.
"""
import argparse
import json
import random
import re
import sys
import time
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd
from pytrends.request import TrendReq

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "trends"
ANCHOR = "Fandango"


def term(title):
    """Search term: the title without punctuation Trends trips on (keeps the words people type)."""
    t = re.sub(r"[:\-–—!?.,'’\"&]", " ", str(title))
    return re.sub(r"\s+", " ", t).strip()[:100]


def film_id(title, release_date):
    slug = re.sub(r"[^a-z0-9]+", "_", str(title).lower()).strip("_")
    return f"{str(release_date)[:10].replace('-', '')}_{slug}"


def norm(t):
    t = re.sub(r"[^a-z0-9 ]", " ", str(t).lower())
    return re.sub(r"\s+", " ", re.sub(r"\b(the|episode [ivx]+|part)\b", " ", t)).strip()


TOPICS = OUT / "topics.json"
_topics = json.load(open(TOPICS)) if TOPICS.exists() else {}


def resolve(tr, title, year):
    """Google Trends topic for a film (type 'NNNN film', year within 1 of release); else the plain title."""
    key = f"{title}|{year}"
    if key not in _topics:
        hit, ok = None, False
        for attempt in range(3):
            try:
                best = None
                for s in tr.suggestions(title):
                    m = re.match(r"(\d{4}) film$", s.get("type", ""))
                    if not m or abs(int(m.group(1)) - int(year)) > 1:
                        continue
                    a, b = norm(title), norm(s["title"])
                    sim = SequenceMatcher(None, a, b).ratio()
                    if sim < 0.75 and not (a in b or b in a):
                        continue  # e.g. Infinity War must not match the Avengers: Endgame topic
                    score = (int(m.group(1)) == int(year), sim)  # exact year first, then closest title
                    if best is None or score > best[0]:
                        best = (score, {"query": s["mid"], "kind": "topic", "label": s["title"]})
                hit, ok = (best[1] if best else None), True
                break
            except Exception as e:
                print(f"  suggestions {title}: {type(e).__name__}; waiting", flush=True)
                time.sleep(60 * (attempt + 1))
        fallback = {"query": term(title), "kind": "term", "label": term(title)}
        if not ok:  # lookup failed (rate limit): use the title this time, but do not cache it
            return fallback
        _topics[key] = hit or fallback
        TOPICS.parent.mkdir(parents=True, exist_ok=True)
        json.dump(_topics, open(TOPICS, "w"), indent=1, ensure_ascii=False)
        time.sleep(random.uniform(2, 4))
    return _topics[key]


def fetch(tr, title, timeframe, year):
    """One query with the anchor; returns a long DataFrame or raises after repeated rate limits."""
    q = resolve(tr, title, year)
    for attempt in range(4):
        try:
            tr.build_payload([q["query"], ANCHOR], timeframe=timeframe, geo="US")
            d = tr.interest_over_time()
            if d.empty:
                return pd.DataFrame(columns=["date", "interest", "anchor_interest", "partial"]).assign(
                    query=q["query"], kind=q["kind"], label=q["label"])
            d = d.reset_index()
            return pd.DataFrame({"date": d["date"].dt.date, "interest": d[q["query"]],
                                 "anchor_interest": d[ANCHOR], "partial": d.get("isPartial", False),
                                 "query": q["query"], "kind": q["kind"], "label": q["label"]})
        except Exception as e:  # 429s and timeouts: back off and retry
            wait = 60 * (attempt + 1) + random.uniform(0, 15)
            print(f"  {title}: {type(e).__name__} ({str(e)[:80]}); waiting {wait:.0f}s", flush=True)
            time.sleep(wait)
    raise RuntimeError(f"Google Trends kept refusing ({title}); try again later")


def daily(tr):
    films = json.load(open(ROOT / "tracker" / "upcoming.json"))["films"]
    today = date.today()
    due = [f for f in films if today <= date.fromisoformat(f["release_date"]) <= today + timedelta(days=70)]
    rows = []
    for f in due:
        d = fetch(tr, f["title"], "today 3-m", f["release_date"][:4])
        rows.append(d.assign(snapshot=str(today), film_id=film_id(f["title"], f["release_date"]),
                             title=f["title"], release_date=f["release_date"]))
        print(f"  {f['title']}: {len(d)} days ({d['kind'].iat[0] if len(d) else '-'})", flush=True)
        time.sleep(random.uniform(4, 8))
    if not rows:
        print("No upcoming films in the next 70 days.")
        return
    (OUT / "daily").mkdir(parents=True, exist_ok=True)
    path = OUT / "daily" / f"{today}.csv"
    pd.concat(rows, ignore_index=True).to_csv(path, index=False)
    print(f"Wrote {path.relative_to(ROOT)} ({len(rows)} films)")


def history(tr, limit):
    df = pd.read_csv(ROOT / "data" / "processed" / "model_table.csv", parse_dates=["release_date"])
    df = df[df.in_model & df.year.between(2016, 2025) & ~df.year.isin([2020, 2021])]
    df = df.sort_values("log_opening", ascending=False)  # biggest films first: they are the question
    (OUT / "history").mkdir(parents=True, exist_ok=True)
    todo = [r for r in df.itertuples() if not (OUT / "history" / f"{r.film_id}.csv").exists()]
    print(f"{len(df)} films, {len(df) - len(todo)} already fetched, {len(todo)} to go", flush=True)
    for i, r in enumerate(todo[:limit] if limit else todo):
        start, end = (r.release_date - timedelta(days=63)).date(), r.release_date.date()
        d = fetch(tr, r.title, f"{start} {end}", r.year)
        if f"{r.title}|{r.year}" not in _topics:  # topic lookup was rate-limited: retry this film next run
            time.sleep(random.uniform(30, 60))
            continue
        d.assign(film_id=r.film_id, title=r.title, release_date=str(end)) \
         .to_csv(OUT / "history" / f"{r.film_id}.csv", index=False)
        if i % 25 == 0:
            print(f"  {i + 1}/{len(todo)} {r.title} ({r.year})", flush=True)
        time.sleep(random.uniform(8, 14))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--history", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    tr = TrendReq(hl="en-US", tz=360, timeout=(10, 25))  # no built-in retries: broken with urllib3 2.x
    try:
        history(tr, a.limit) if a.history else daily(tr)
    except RuntimeError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
