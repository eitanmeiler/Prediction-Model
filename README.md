# Prediction Model: what predicts a box office opening now?

A transparent, forward-tested model of US opening-weekend box office (wide releases, 2010–2025). It tests whether the
traditional drivers (stars, franchises, budget, release timing) have lost predictive power since 2020, and whether
pre-release audience attention explains the hits and flops that conventional expectations miss.

- **Hypotheses (written down before modeling):** [HYPOTHESES.md](HYPOTHESES.md)
- **Known limitations:** [LIMITATIONS.md](LIMITATIONS.md)
- **Walkthroughs (how each piece works, in interview language):** `walkthroughs/`

## Layout
| Path | What |
|---|---|
| `tracker/` | Daily live tracker: Wikipedia pageviews for upcoming releases (`watchlist.json`). Runs at 10:15 via launchd. |
| `data/live/` | Link to the tracker's runtime data (`~/Library/Application Support/PredictionModel/data/live`). |
| `data/raw/` | Source tables (box office tables are gitignored and never published). |
| `docs/` | Data dictionary, research memo. |

## Run the tracker by hand
```bash
python3 tracker/track_wiki.py --dry-run
```
After editing `track_wiki.py` or `watchlist.json`, run `tracker/install.sh` to update the scheduled copy.
