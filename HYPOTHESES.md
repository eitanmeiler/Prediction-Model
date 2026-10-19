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
