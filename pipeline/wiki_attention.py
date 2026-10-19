#!/usr/bin/env python3
"""Pre-release Wikipedia attention for every wide release from 2016 on (pageview data starts July 2015).

1. Wikidata maps each TMDB id (property P4947) to its English Wikipedia article, and its "based on" (P144)
   source works to theirs.
2. Wikimedia pageviews give daily user views before release. Features (pre-registered, HYPOTHESES.md):
     att_level  : log mean daily views of the film article, T-28..T-8          (H3)
     att_accel  : log(mean T-14..T-8) - log(mean T-28..T-22)                     (H5)
     src_att    : log mean daily views of the source work, 365 days ending T-180 (H4)
Responses are cached in data/cache/wiki_attention/. Output: data/interim/wiki_attention.csv

Known gap: the pageviews API counts one title only. If an article was renamed (e.g. "X (2023 film)" moved to
"X"), views under the old title are missed; such films show unusually low pre-release views and are flagged.
"""
import hashlib
import json
import time
import urllib.parse
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "data" / "processed" / "model_table.csv"
OUT = ROOT / "data" / "interim" / "wiki_attention.csv"
CACHE = ROOT / "data" / "cache" / "wiki_attention"
UA = {"User-Agent": "PredictionModel-research/0.1 (personal research; contact via GitHub)"}
PV = "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{}/daily/{}/{}"
DATA_START = pd.Timestamp("2015-07-01")


def cached(key, fetch):
    f = CACHE / (hashlib.sha1(key.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    data = fetch()
    f.write_text(json.dumps(data))
    return data


def http_get(url, **kw):
    for attempt in range(30):  # Wikimedia rate-limits per IP; wait it out patiently
        r = requests.get(url, headers=UA, timeout=60, **kw)
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(max(int(r.headers.get("Retry-After", 0) or 0), 5) + 5 * min(attempt, 6))
            continue
        return r
    r.raise_for_status()


def wikidata_titles(tmdb_ids):
    """TMDB id -> (enwiki title, [source-work enwiki titles])."""
    out = {}
    ids = [str(int(i)) for i in tmdb_ids]
    for i in range(0, len(ids), 150):
        chunk = ids[i:i + 150]
        q = f"""SELECT ?tmdb ?article ?srcArticle WHERE {{
          VALUES ?tmdb {{ {' '.join(f'"{x}"' for x in chunk)} }}
          ?film wdt:P4947 ?tmdb .
          OPTIONAL {{ ?article schema:about ?film ; schema:isPartOf <https://en.wikipedia.org/> . }}
          OPTIONAL {{ ?film wdt:P144 ?src . ?srcArticle schema:about ?src ; schema:isPartOf <https://en.wikipedia.org/> . }}
        }}"""

        def fetch():
            time.sleep(1)
            r = http_get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"})
            r.raise_for_status()
            return r.json()["results"]["bindings"]

        for b in cached("wd:" + ",".join(chunk), fetch):
            tid = int(b["tmdb"]["value"])
            title = lambda k: urllib.parse.unquote(b[k]["value"].rsplit("/wiki/", 1)[1]) if k in b else None
            film_t, src_t = title("article"), title("srcArticle")
            entry = out.setdefault(tid, [film_t, set()])
            entry[0] = entry[0] or film_t
            if src_t:
                entry[1].add(src_t)
        print(f"  wikidata {min(i + 150, len(ids))}/{len(ids)}", flush=True)
    return out


def daily_views(article, start, end):
    start, end = max(start, DATA_START), end
    if end < start:
        return pd.Series(dtype=float)
    url = PV.format(urllib.parse.quote(article, safe=""), f"{start:%Y%m%d}", f"{end:%Y%m%d}")

    def fetch():
        time.sleep(1.5)
        r = http_get(url)
        return r.json().get("items", []) if r.status_code == 200 else []

    items = cached(url, fetch)
    return pd.Series({pd.Timestamp(it["timestamp"][:8]): it["views"] for it in items}, dtype=float)


def window_mean(s, rel, a, b):
    """Mean daily views between day `a` and day `b` before release (missing days count as 0 views)."""
    days = pd.date_range(rel - pd.Timedelta(days=a), rel - pd.Timedelta(days=b))
    days = days[days >= DATA_START]
    return s.reindex(days, fill_value=0).mean() if len(days) else np.nan


def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(TABLE, parse_dates=["release_date"])
    df = df[df.in_model & (df.release_date >= "2016-01-01")]
    titles = wikidata_titles(df.tmdb_id.dropna().unique())
    rows = []
    for k, r in enumerate(df.itertuples(), 1):
        art, srcs = titles.get(int(r.tmdb_id), [None, set()])
        rel = r.release_date
        row = {"film_id": r.film_id, "wiki_article": art, "wiki_sources": "|".join(sorted(srcs))}
        if art:
            s = daily_views(art, rel - pd.Timedelta(days=60), rel - pd.Timedelta(days=1))
            lvl, late, early = window_mean(s, rel, 28, 8), window_mean(s, rel, 14, 8), window_mean(s, rel, 28, 22)
            row.update(att_level=np.log1p(lvl), att_accel=np.log1p(late) - np.log1p(early),
                       att_t60=np.log1p(window_mean(s, rel, 60, 29)), att_days_with_views=int((s > 0).sum()))
        if srcs:
            vals = []
            for src in sorted(srcs):
                s = daily_views(src, rel - pd.Timedelta(days=545), rel - pd.Timedelta(days=180))
                if len(s) >= 90:
                    vals.append(window_mean(s, rel, 545, 180))
            row["src_att"] = np.log1p(max(vals)) if vals else np.nan
        rows.append(row)
        if k % 100 == 0:
            print(f"  pageviews {k}/{len(df)}", flush=True)
    out = pd.DataFrame(rows)
    out["att_suspect_rename"] = out.att_days_with_views.lt(20)  # article probably created/renamed late
    out.to_csv(OUT, index=False)
    print(f"{len(out)} films; article found {out.wiki_article.notna().mean():.1%}; "
          f"attention {out.att_level.notna().mean():.1%}; source attention {out.src_att.notna().sum()} films")


if __name__ == "__main__":
    main()
