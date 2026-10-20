#!/usr/bin/env python3
"""Post-release Wikipedia momentum for H9 (HYPOTHESES.md Amendment 6).
post_momentum = log(mean daily views, days +3..+9 after release) - log(mean views, days T-7..T-1).
Reuses the attention pull's article mapping and cache. Output: data/interim/wiki_post.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import wiki_attention as wa  # noqa: E402

att = pd.read_csv(ROOT / "data/interim/wiki_attention.csv")
films = pd.read_csv(ROOT / "data/processed/model_table.csv", parse_dates=["release_date"])[["film_id", "release_date"]]
d = att[att.wiki_article.notna() & ~att.att_suspect_rename].merge(films, on="film_id")
rows = []
for k, r in enumerate(d.itertuples(), 1):
    rel = r.release_date
    s = wa.daily_views(r.wiki_article, rel - pd.Timedelta(days=7), rel + pd.Timedelta(days=9))
    pre = s.reindex(pd.date_range(rel - pd.Timedelta(days=7), rel - pd.Timedelta(days=1)), fill_value=0).mean()
    post = s.reindex(pd.date_range(rel + pd.Timedelta(days=3), rel + pd.Timedelta(days=9)), fill_value=0).mean()
    rows.append({"film_id": r.film_id, "views_pre7": pre, "views_post3_9": post,
                 "post_momentum": np.log1p(post) - np.log1p(pre)})
    if k % 100 == 0:
        print(f"  {k}/{len(d)}", flush=True)
pd.DataFrame(rows).to_csv(ROOT / "data/interim/wiki_post.csv", index=False)
print(f"{len(rows)} films -> data/interim/wiki_post.csv")
