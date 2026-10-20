# Where attention helps — and where it can't see (development backtest, T-7, 2017-2024)

Exploratory, not confirmatory. "×" = actual opening ÷ forecast (1.0 = perfect). Traditional = CatBoost on
traditional features; attention = CatBoost + Wikipedia attention. Source: `data/processed/backtest_predictions.csv`.

## 1. Attention is best at spotting flops
For the 111 films that opened below half the traditional forecast, the median actual/forecast ratio moves
**0.36× → 0.43×** with attention. Low pre-release interest is a warning sign the traditional factors miss.

| Film | Year | Traditional | With attention |
|---|---|---|---|
| Babylon | 2022 | 0.13× | 0.25× |
| Whitney Houston: I Wanna Dance with Somebody | 2022 | 0.15× | 0.33× |
| Mary Poppins Returns | 2018 | 0.28× | 0.55× |
| Strange World | 2022 | 0.29× | 0.45× |
| Paws of Fury | 2022 | 0.30× | 0.51× |

## 2. It partly catches cultural events
| Film | Year | Traditional | With attention |
|---|---|---|---|
| Barbie | 2023 | 5.20× | 2.85× |
| Conclave | 2024 | 4.69× | 2.51× |
| Nosferatu | 2024 | 3.81× | 2.53× |
| Wicked | 2024 | 3.42× | 2.52× |
| Toy Story 4 | 2019 | 2.59× | 1.77× |
| The Little Mermaid | 2023 | 2.60× | 1.84× |
| Dragon Ball Super: Broly | 2019 | 3.85× | 1.68× |

Across all 68 big upside surprises (traditional miss > 2×), though, the median barely moves (2.59× → 2.52×):
attention narrows the biggest events but does not explain upside surprises in general.

## 3. Audiences English Wikipedia can't see
These over-performers barely improve, or get worse, with attention:

| Film | Year | Traditional | With attention | Audience |
|---|---|---|---|---|
| Sound of Freedom | 2023 | 3.61× | 4.02× | faith / church networks |
| Unplanned | 2019 | 3.63× | 3.75× | faith |
| I Can Only Imagine | 2018 | 3.98× | 3.40× | faith |
| Am I Racist? | 2024 | 2.78× | 3.22× | political / talk-radio |
| How to Be a Latin Lover | 2017 | 7.05× | 7.54× | Spanish-speaking |
| Overboard | 2018 | 2.88× | 3.47× | Spanish-speaking (Pantelion) |
| The Super Mario Bros. Movie | 2023 | 3.42× | 3.36× | families / gamers |

**Hypothesis for the paper (not yet tested):** part of the "X factor" is mobilized communities — faith groups,
Spanish-speaking audiences, families — whose enthusiasm doesn't show up in English-language online attention.
A test: add distributor-type flags (faith distributors such as Angel, Affirm, Pure Flix; Spanish-language
distributors such as Pantelion) and Spanish-Wikipedia pageviews, then check whether these residuals shrink —
pre-registered as a new hypothesis *before* running it.

## 4. Descriptive H6 check (already-seen 2014-2025 data; not a test)
Traditional ridge model, T-7 residuals (actual − forecast, log scale):

| Group | Films | Mean residual | ≈ actual ÷ forecast |
|---|---|---|---|
| Faith / Spanish-language distributors (H6 list) | 37 | +0.149 (95% CI −0.067 to +0.367) | 1.16× |
| All other films | 1,239 | −0.114 | 0.89× |

By distributor: Affirm +0.40 (6 films), Pantelion +1.44 (2), Angel +0.05 (17), Pure Flix −0.04 (11),
Pure Flix / Quality Flix −0.20 (1). **Weak and uneven** — the gap comes mostly from Affirm and Pantelion; Angel
and Pure Flix films land near forecast. The confirmatory 2026 test may be underpowered (it needs ≥ 8 flagged films).
