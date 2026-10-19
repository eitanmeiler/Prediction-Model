# Known limitations

Written 2026-10-12, before modeling. Each item is marked **[open]**, **[mitigated]** or **[accepted]**. Updated as
issues come up.

## Data access
- **[mitigated] Box office actuals.** Free route chosen (HYPOTHESES.md, Amendment 1): film list and widest theater
  counts come from the Box Office Mojo yearly tables, copied by hand; opening weekend comes from Wikipedia text. Known
  error sources: Sunday estimates instead of actuals, extractor misreads, films with no article. The error rate is
  measured by hand-checking a sample. Earlier note: Box Office Mojo's terms prohibit automated scraping. The Numbers blocks scripted
  requests (HTTP 403). This project does not scrape either site. Route: the yearly tables are copied manually for
  personal, non-commercial research, or a licence is bought (OpusData). Raw box office tables are never published.
- **[mitigated] Python environment.** uv + Python 3.12 in `.venv`.
- **[mitigated] API keys.** Both created and working; a pre-commit hook blocks keys from reaching git. TMDB (metadata) and the YouTube Data API (trailer views) each need a free key created by the
  owner. Keys go in `.env`, which is gitignored.
- **[mitigated] Scheduled jobs can't read ~/Desktop** (macOS privacy protection). The tracker runs from
  `~/Library/Application Support/PredictionModel`, and `data/live` is a link to it. See `tracker/install.sh`.
- **[mitigated] Wikipedia rate limits** (HTTP 429). The tracker waits 1 second between requests and backs off on errors.

## What can be measured
- **[accepted] Attention may just reflect marketing spend.** Pageviews and search activity rise with ad spend, which
  is not public. Fan enthusiasm cannot be separated from marketing push, so attention results are *associations*.
- **[accepted] Theater count and release date are chosen by studios** based on their own forecasts (Cat in the Hat
  was moved from Feb to Nov for that reason). Models that use them partly learn the studio's forecast. Results are
  reported with and without theater count.
- **[accepted] Trailer views and social media cannot be recovered for past dates.** They are used only in live
  tracking, never in the backtest.
- **[accepted] No Wikipedia data before July 2015.** The attention hypotheses cover 2016 onward only.
- **[accepted] Wikipedia noise:** pages created late, pages renamed, spikes from news events and previews. Features
  are cut off at fixed checkpoints before release.
- **[accepted] Google Trends** values are relative, sampled and shift between pulls, and the unofficial API is
  fragile. Secondary feature; may be dropped.
- **[accepted] Budgets** are self-reported, rounded and often missing for non-studio films. Budget tiers plus a
  "budget unknown" flag are used.
- **[accepted] Marketing spend** is unavailable. Profitability is out of scope.
- **[accepted] Star power is tangled up with franchises**, and it is meaningless for animated films (voice casts).

## Statistical power
- **[accepted] The post-2020 sample is small** (about 3½ years of wide releases). Estimates of a change will have wide
  confidence intervals and may be inconclusive.
- **[mitigated] Testing many ideas can manufacture a finding.** Hypotheses were written down in advance in
  HYPOTHESES.md, the 2025 holdout is sealed, and a Holm correction is applied.
- **[accepted] The strike natural experiment** is underpowered (probably 10–20 films). Case study only.
- **[accepted] Films that skipped theaters in 2020–21** drop out of the data (survivorship).
- **[mitigated] Ticket-price inflation** across 2010–2025. Market-share target used as a sensitivity check.

## Live test and presentation
- **[accepted] One film is an anecdote.** A real live track record needs about 20–30 films, which runs past the Nov 6
  test.
- **[accepted] Wild Horse Nine** is likely a limited release, outside the population.
- **[open] Tight deadline.** The model must be ready by about Oct 30 to freeze the T-7 forecast before the Nov 6
  openings.
- **[accepted] Honest accuracy will look modest** (box office is dominated by a few huge hits). Success = beating
  the comparable-films baseline with well-calibrated ranges.
- **[accepted] The repo is private.** Any public demo shows forecasts and derived features only.
