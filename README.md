# Opening Night — what predicts a box office opening now?

A transparent, forward-tested model of US opening-weekend box office for **1,959 wide releases (2010–2025, opened
in 800+ theaters)**. It asks whether the traditional drivers — stars, franchises, release timing — still explain
openings after 2020, and whether pre-release audience attention explains the hits and flops they miss.

Every hypothesis was written down before modeling ([HYPOTHESES.md](HYPOTHESES.md), with dated amendments), 2025 is
a sealed holdout, and live forecasts are frozen in git before release so they can't be quietly changed.

## Status (2026-10-19) — development results, 2025 still sealed

| Question | Finding so far |
|---|---|
| Can openings be forecast a week out? | Typical miss **~34–39%** vs **~65%** for a comps baseline; 80% ranges cover ~78% of actuals |
| Ridge vs. CatBoost? | Tied on traditional features (no significant difference) |
| H1 — star power fell after 2020? | **Not supported.** Star track records barely predicted openings *before* 2020 either |
| H2 — openings got less predictable? | Only because of 2022 (reopening year); **not supported** once 2022 is excluded |
| H3 — does pre-release attention help? | **Yes (CatBoost):** error ↓ ~7%, and the gain is **larger after 2020** (H3b) |
| H4 — existing fanbase (source-work attention)? | Borderline positive |
| H5 — accelerating buzz? | Positive; narrowly misses the multiple-testing threshold |

Full numbers: [docs/backtest_summary.md](docs/backtest_summary.md), [docs/hypothesis_results_dev.md](docs/hypothesis_results_dev.md),
[docs/attention_results_dev.md](docs/attention_results_dev.md), headline chart
[docs/figures/drivers_over_time.png](docs/figures/drivers_over_time.png), case-study list [docs/biggest_misses.md](docs/biggest_misses.md).
Caveat: attention may partly reflect marketing spend, which is not observable ([LIMITATIONS.md](LIMITATIONS.md)).

## How it works

1. **Box office** — Box Office Mojo "In-year releases" tables, copied by hand (one bookmark click per year; the site
   forbids scraping) → `pipeline/build_films.py`
2. **Film details** — TMDB (genre, rating, runtime, cast, director, franchise, source flags) → `pipeline/tmdb_enrich.py`
3. **Attention** — Wikipedia pageviews before release (Wikidata maps films and their source works) →
   `pipeline/wiki_attention.py`; a daily tracker records upcoming films → `tracker/`
4. **Features** — only information knowable before release; track records use films ≥ 7 days older →
   `pipeline/features.py`, `models/feature_sets.py`
5. **Backtest** — retrain every quarter on past films only, 2014–2024 → `models/backtest.py`
6. **Tests** — `analysis/hypotheses.py`, `analysis/attention_tests.py`, `analysis/drivers_over_time.py`, `analysis/misses.py`
7. **Live forecasts** — `models/forecast_live.py` (`--freeze` appends to `forecasts/forecast_log.csv`)
8. **Dashboard** — `app/dashboard.py`

Walkthroughs in plain English (for explaining it in interviews): [`walkthroughs/`](walkthroughs/).

## Run it

```bash
./refresh.sh                                   # rebuild data, backtest, draft forecasts
.venv/bin/python models/forecast_live.py --freeze   # freeze current forecasts (then commit)
.venv/bin/streamlit run app/dashboard.py       # dashboard at http://localhost:8501
```
Box office tables: open `https://www.boxofficemojo.com/year/YYYY/?grossesOption=totalGrosses&sort=maxNumTheaters`,
click the **Copy BOM table** bookmark (install via `tracker/install_bookmark.html`) with `tracker/collect_years.py` running.

API keys live only in `.env` (gitignored; a pre-commit hook blocks keys). Raw box office tables are never committed.

This product uses the TMDB API but is not endorsed or certified by TMDB.
