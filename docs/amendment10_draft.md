# DRAFT: Amendment 10 (not yet in HYPOTHESES.md; adopt only with the student's OK, before any Trends result is computed)

## Amendment 10 (2026-11-25): does Google search interest close the big-film gap? Written before any Trends result was seen

**Why.** Amendment 9 found that the model under-forecasts big openings (40 of 42 openings above $100M in 2017-2025,
median ×1.76) and that the cause is missing information: demand that shows up in presales, not in our free inputs.
Google Trends search interest is the best free proxy for that demand. This amendment fixes, in advance, how it will be
tested, so that the result cannot be shaped by trying variants until one works.

**Data, frozen before analysis.**
- History: `data/trends/history/`, committed at 4bebdf6 (1,009 of 1,032 model films, 2016-2025, 2020-21 excluded).
  The 23 missing films may be fetched with the same script before the analysis runs; films still missing are left
  missing (CatBoost handles gaps). No film is dropped or re-fetched after any result is seen.
- Each file is the 63 days before release, US, daily, the film queried alongside the fixed anchor "Fandango".
- Search target: Google's film topic where one matched (title similarity ≥ 0.75, film year within 1 of release),
  otherwise the plain title (`data/trends/topics.json`: 688 topic, 321 title). The mapping is frozen as of this
  amendment. It may only be corrected for clear mismatches found by reading labels, before the analysis runs.
- Google scales each query to 0-100 over the whole window. The film ÷ anchor ratio does not depend on that scale, so
  ratios are comparable across films. The query window runs to release day, but only days up to 7 days before release
  are used (the T-7 rule). The later days affect integer rounding only.

**Inputs (exactly three, fixed now).** With r(a, b) = sum of film interest ÷ sum of anchor interest, days a to b
before release:
1. `trend_level` = log(1 + r(35, 7)): how much the film is searched relative to ticket-buying in general.
2. `trend_growth` = log(1 + r(14, 7)) − log(1 + r(35, 28)): whether interest is accelerating in the last weeks.
3. `trend_topic` = 1 if the film was matched to a topic, else 0, so the model can discount title-only matches.

**Test.** Same frozen procedure as the backtest and Amendment 9: CatBoost + attention at T-7, rolling quarterly
2017-2025 (2020-21 excluded), trained on 2016+ films released before each quarter.
- **Primary comparison:** v1 features vs v1 features + the three Trends inputs. Nothing else changes: no tuning, no
  feature selection.
- **Secondary (reported, never used for the decision):** the same with ridge; the Amendment 9 stretch applied on top;
  topic-matched films only.

**Outcomes and decision rule (fixed now).**
- (a) Big films: median actual ÷ forecast for openings above $100M. Baseline ×1.76 (Amendment 9 backtest).
- (b) Overall typical miss (median |actual ÷ forecast − 1|), 2017-2025 and 2022-2025.
- (c) Selection check: because (a) selects on the outcome, also report the median ratio for the 10% of films with the
  highest *forecasts*.
- **Pass:** (a) improves to ×1.61 or lower (at least 0.15 better) **and** (b) overall is no more than 0.3 points worse.
- **Strong pass:** pass, and (b) overall improves, with a 95% confidence interval that excludes zero. The interval
  comes from a block bootstrap by quarter on the per-film change in absolute log error, 2,000 draws, seed 0.
- **Fail:** anything else. It is reported as a fail, with the numbers, and Trends is not used.

**What happens with the result.**
- v1 stays the official record whatever happens. Nothing already logged changes.
- If it **passes**, a **v4** forecast (CatBoost + attention + Trends, trained exactly as in the test through 2025) is
  locked alongside v1, v2, v3 and Combined from the first opening at least 3 days after the result is committed.
  Its Trends inputs come from the daily snapshot (`data/trends/daily/`) dated 7 days before release, or the nearest
  earlier one. This would include *Avengers: Doomsday* and *Dune: Part Three* (Dec 18) if the test is finished by
  Dec 10.
- If it **fails**, the paper says so. The big-film gap then stays the study's main stated limitation, with Combined
  (Amendment 7) as the remedy that works.
- Either way, the result is a candidate input for the 2027 model and will be re-tested on 2026 films.

**Script.** `analysis/amendment10_trends_backtest.py` will be written after this amendment is committed. The
commit order (amendment, then script, then results) is the proof that the rules came first.
