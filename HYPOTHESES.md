# Pre-registered hypotheses

Written **2026-10-12, before any historical data was collected or modeled.** Only the hypotheses below count as
confirmatory findings. Anything discovered later is labeled *exploratory* in the write-up. Changes to this file
after today must be added as dated amendments, never silent edits (git history is the audit trail).

## Definitions (fixed now)

- **Population:** US domestic theatrical releases that opened in **≥ 600 theaters**, 2010–2025. 2020 and 2021 are
  excluded from model training and reported separately (pandemic closures, same-day streaming releases).
- **Target:** log(domestic opening weekend gross, Fri–Sun). The sensitivity check uses the film's share of that
  weekend's total domestic gross, which removes ticket-price inflation and overall market size.
- **Periods:** *pre* = 2010–2019, *post* = 2022–2025.
- **Sealed holdout:** films released in **2025** are not looked at until the final evaluation run.
- **Forecast checkpoints:** T-28 days (no theater count), T-7 (theater count known), T-1 (reviews in).
- **Star power:** mean log opening of the top-3 billed actors' prior wide releases in the previous 5 years,
  computed only from films released before the forecast date. Animated films: set to missing, with a flag.
- **Pre-release attention:** English Wikipedia daily user pageviews (available from July 2015 onward).
- **Significance:** α = 0.05 with Holm correction across H1–H5. Report effect sizes and 95% CIs, not only p-values.

## Hypotheses

**H1: The star-power effect is smaller after 2020.**
In a ridge/OLS model of log opening that controls for franchise/sequel, genre, MPAA rating, release season and budget
tier, the star-power × post-period interaction is negative. Reported both **with and without** opening theater count,
because theater count is partly a consequence of star power.

**H2: Openings are less predictable after 2020.**
With the same feature set and the same rolling backtest, the median absolute log error at T-7 is higher for 2022–2024
than for 2016–2019.

**H3: Pre-release attention adds predictive value beyond traditional variables.**
Adding Wikipedia attention features (level and growth over T-28…T-8) reduces backtest error versus the
traditional-only model (2016–2024). **H3b:** the gain is larger in the post period.

**H4 (X-factor candidate): An existing fanbase predicts outperformance.**
For adaptations, pageviews of the *source IP's* Wikipedia article in the 365 days ending T-180 are positively
associated with the traditional model's residuals (actual minus predicted).

**H5 (X-factor candidate): Attention acceleration predicts outperformance.**
The ratio of film-page views at T-14…T-8 to views at T-28…T-22 is positively associated with residuals, beyond the
attention level itself.

## Exploratory (not confirmatory)

- The 2023 SAG-AFTRA strike period (actors could not promote films) is too small a sample for a formal test. It is a
  case study only.
- Error patterns by genre, studio, budget tier and original vs. adapted.
- Case studies of the 10 largest over- and under-performers.

## Live forecasts

- **The Cat in the Hat (2026), Nov 6, 2026:** the primary live test. Forecasts are frozen in git at T-7 and T-1.
  *Student's prior call (2026-10-12): it flops.* "Flop" is defined as an actual opening **below the lower bound of the
  model's 80% interval at T-7**.
- **Wild Horse Nine, Nov 6, 2026:** tracked as a side case. It is likely a limited/platform release, outside the
  model's population, so no confirmatory claim is made.
- All other theatrical releases from Oct to Dec 2026 in `tracker/watchlist.json` get forecasts if they open wide. A
  single film is an anecdote; the backtest is the real validation.

## Amendment 1 (2026-10-18), made before any historical data was collected

The free data route replaces licensed data, so two definitions change:
- **Population:** "opened in ≥ 600 theaters" becomes **widest release ≥ 600 theaters** (Box Office Mojo yearly
  tables, copied manually). Opening theater counts are not available for free.
- **Target source:** opening weekend gross is extracted from English Wikipedia article text
  (`pipeline/extract_openings.py`). Its error rate is measured on a random sample of about 40 films checked by hand
  against Box Office Mojo, and reported. If a licensed source (OpusData) becomes available, it replaces Wikipedia,
  and Wikipedia figures become a cross-check.

## Amendment 2 (2026-10-19), made before any modeling

Box Office Mojo's "In-year releases" tables include official **opening weekend gross and opening theater count**,
so Amendment 1's Wikipedia extraction is no longer needed:
- **Population:** films that **opened in ≥ 800 theaters** (BOM "Open Th"), 2010–2025. 800 is used instead of 600
  because the copied tables cover films down to 800 opening theaters in *every* year (2025's page stops at 800). That
  keeps the population definition identical across years. Re-releases are excluded; event cinema (concerts, Fathom
  one-night events, TV-episode screenings) is flagged and excluded from the main models.
- **Target source:** BOM opening weekend gross for all years (one source across the whole period, so a change
  between periods can't come from switching sources). Wikipedia extraction is kept only as an optional cross-check.

## Amendment 3 (2026-10-19), during development — before the sealed 2025 run

- **Budget removed** from all models: TMDB budgets are entered after release (leakage; see LIMITATIONS.md).
- **Star-power tests start in 2013** (2010-2012 is the burn-in for cast track records; data begins in 2010).
- **Market-share sensitivity target replaced** by year fixed effects (H1) and a "current market level" feature
  (models): weekend-total box office was not collected, so share of the weekend market can't be computed.
- **H3 model:** H3 was written without naming a model. Development results are reported for both ridge and
  CatBoost; the confirmatory run will report both, and the conclusion will not rest on picking the better one.
- **Development results so far** (2025 sealed): H1 not supported; H2 not supported once 2022 is excluded;
  H3/H3b supported for CatBoost (weakly for ridge); H4 borderline; H5 positive but misses the Holm threshold narrowly.

## Amendment 4 (2026-10-19) — new hypothesis H6, written before it was tested

Motivated by exploratory case studies (`docs/case_studies_dev.md`): faith and Spanish-language over-performers
are not captured by English-Wikipedia attention.

**H6: Community audiences are systematically under-forecast.** Films whose Box Office Mojo distributor is
faith-focused (**Angel, Affirm Films, Pure Flix Entertainment, Pure Flix / Quality Flix**) or Spanish-language
(**Pantelion Films**) have **positive mean residuals** in the traditional T-7 model (actual > forecast).
- *Exploratory check:* 2014-2025 backtest residuals (already seen data — descriptive only).
- *Confirmatory test:* **2026 releases only** (not yet seen at the time of writing): mean residual of flagged
  films > 0, one-sided, with the frozen T-7 model. If fewer than 8 flagged 2026 films exist, H6 is reported as
  "insufficient data", not tested.
- *Correction (same day, before any H6 computation):* the distributor list was reworded to the five names above;
  an earlier draft ambiguously mentioned Fathom Events and Kingdom Story Company.

## Amendment 5 (2026-10-20) — the breakout question, written before any of this was analysed

Motivation (seen, so these are hypotheses, not findings): 2026 breakouts from internet-native creators
(*Obsession* — Curry Barker; *Backrooms* — Kane Parsons; *Iron Lung* — Markiplier) and the community-audience
misses in `docs/case_studies_dev.md`.

### Community-audience classes (rules fixed now; the film list is built from these rules and frozen before testing)
- **C1 creator-native**: the film's director, writer or core IP began as self-published online work (YouTube
  channel, web series, online creepypasta/ARG/indie web game), documented by a sentence in the creator's or film's
  Wikipedia article. Studio adaptations of large commercial game franchises are not C1.
- **C2 game IP**: TMDB keyword "based on video game" (existing `src_game`).
- **C3 anime**: original language Japanese and genre Animation.
- **C4 faith audience**: distributor in the H6 list or TMDB keyword "christian" / "faith" / "religion" / "bible".
- **C5 Spanish-language / Latino audience**: original language Spanish or distributor Pantelion Films.

### Hypotheses
- **H7 (creator-native under-forecast):** C1 films have positive mean residuals (actual > forecast) in the frozen
  traditional T-7 model. *Exploratory* on releases before 2026-10-20 (the motivating cases are in that set).
  *Confirmatory* only on C1 releases after 2026-10-20 (one-sided test once ≥ 8 exist; until then reported as
  "insufficient data").
- **H8 (legs):** a "legs" model (log of domestic total ÷ opening, pre-release features + the opening itself) is
  improved by attention acceleration and community class (C1-C5) beyond traditional features: paired bootstrap
  gain in MAE, rolling quarterly backtest 2017-2025, films ≥ 10 weeks past release only. This relationship has not
  been examined before this amendment.
- **Breakout model (descriptive, not a hypothesis test):** probability that a film opens at ≥ 2× its traditional
  T-7 forecast; rolling backtest; reported with Brier score, ROC-AUC vs. the base rate, and a calibration table.
