# DRAFT: Amendment 9 (not yet in HYPOTHESES.md; adopt only with the student's OK, before the Nov 25 lock-ins)

## Amendment 9 (2026-11-23): the big-film ceiling. Two fixes tested, one adopted, written before the Nov 25 openings

**Why.** *The Hunger Games: Sunrise on the Reaping* (Nov 20) was locked in at $43.6M and opened at about $120M.
Two causes were found:

1. **Split franchises.** TMDB files the four original Hunger Games films (2012-15, $103-158M openings) and the
   prequels as two separate collections, so the franchise inputs saw only *The Ballad of Songbirds & Snakes* ($44.6M).
2. **A ceiling on big openings.** At T-7 the model under-forecast 40 of the 42 openings above $100M in 2017-2025, by a
   median of 1.76×. Tree models predict by averaging similar past films, so they rarely forecast beyond the
   typical big release.

**Backtest** (`analysis/amendment9_backtest.py`, `docs/amendment9_backtest.md`). CatBoost + attention at T-7, rolling
quarterly 2017-2025; every correction is fitted only on earlier quarters.

| Variant | Typical miss | 2022-25 | $100M+: actual ÷ forecast | Under-forecast |
|---|---|---|---|---|
| Current | 33.4% | 35.5% | ×1.76 | 40/42 |
| A: franchise family (best, mean and last prior opening across linked collections) | 34.0% | 35.9% | ×1.84 | 40/42 |
| B: top-end correction, err = b·max(0, log forecast − log $25M) | 33.3% | 34.9% | ×1.62 | 36/42 |

Applied to *Sunrise on the Reaping*: A $40.0M, B $46.8M, actual about $120M. **Neither fixes the miss.**

**Decision.**
- **A is rejected.** It made forecasts worse overall, and the model makes little use of a franchise's best opening
  even when it is correct.
- **B is adopted as v3, locked alongside v1, v2 and Combined from the Nov 25 openings on.** The rule is v3 = v1 ×
  exp(b · max(0, log v1 − log $25M)), with b = 0.126 fixed now from the 2017-2025 backtest errors and never refit
  during the season. That is ×1.07 at a $43.6M forecast and ×1.19 at $100M; forecasts under $25M are unchanged. The
  gain is small (−0.1 points overall, −0.6 points for 2022-25, 36 rather than 40 big films under-forecast), and it
  is reported as such.
- **v1 stays the official record.** Nothing already logged changes.

**What this establishes (for the paper).** The big-film gap is a gap in **information**, not in model tuning.
Events whose demand shows up in presales, book and social buzz look the same as ordinary franchise sequels to free
public signals: on Wikipedia, *Sunrise on the Reaping* matched *Ballad* almost exactly, and it accelerated more
slowly. The pre-registered **Combined** forecast (Amendment 7), which uses Hollywood's presale-informed projection,
is the remedy this study can test. It said $69.3M for *Sunrise on the Reaping*.
