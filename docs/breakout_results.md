# The breakout chapter — results

Pre-registered in HYPOTHESES.md Amendment 5 (commit 250c058; C1 list b5de31a). Section A is exploratory; B is the H8 test; C is descriptive.

## A. Who does the traditional forecast miss? (exploratory)

Mean residual of the traditional T-7 forecast, log scale (positive = opened above forecast); ×≈ = exp(mean). 2014-2025 rolling backtest.

| Class | Films | Ridge mean (95% CI) | ×≈ | CatBoost mean (95% CI) | ×≈ |
|---|---|---|---|---|---|
| C1 creator-native | 8 | +0.26 (-0.19 to +0.68) | 1.30 | +0.29 (-0.11 to +0.63) | 1.33 |
| C2 game IP | 22 | +0.18 (-0.12 to +0.49) | 1.19 | -0.01 (-0.27 to +0.26) | 0.99 |
| C3 anime | 20 | +0.12 (-0.25 to +0.44) | 1.13 | +0.18 (-0.23 to +0.52) | 1.20 |
| C4 faith audience | 53 | +0.09 (-0.07 to +0.26) | 1.09 | +0.14 (-0.01 to +0.31) | 1.15 |
| C5 Spanish-language | 3 | +0.63 (-1.00 to +1.63) | 1.87 | +0.64 (-1.08 to +1.95) | 1.91 |
| All other films (reference) | 1276 | -0.11 | 0.90 | | |

C1 films individually (ridge, T-7; ×  = actual ÷ forecast):

| Film | Year | × |
|---|---|---|
| Hardcore Henry | 2016 | 0.44 |
| Lights Out | 2016 | 2.01 |
| Slender Man | 2018 | 1.28 |
| Talk to Me | 2023 | 1.36 |
| Five Nights at Freddy's | 2023 | 2.74 |
| Ryan's World the Movie: Titan Universe Adventure | 2024 | 0.48 |
| Bring Her Back | 2025 | 1.39 |
| Five Nights at Freddy's 2 | 2025 | 2.85 |

## B. H8 — legs: does attention + community class predict how long a film runs?

Target: log(domestic total ÷ opening weekend). Rolling quarterly backtest 2017-2025, trained on 2016+ films; the opening weekend itself is a feature (forecast made after opening). Gain = MAE(traditional) − MAE(plus).

| Model | MAE traditional | MAE + attention & community | Gain (95% CI) | share ≤ 0 |
|---|---|---|---|---|
| ridge | 0.175 | 0.177 | -0.002 (-0.004 to +0.001) | 0.885 |
| catboost | 0.174 | 0.173 | +0.002 (-0.002 to +0.005) | 0.169 |

Conservative p (larger of the two) = **0.885**; H8 not supported at α = 0.05 (single pre-registered test, no further correction).

Longest runs vs. the legs forecast (CatBoost + attention & community; × = total ÷ opening):

| Film | Year | Actual × | Forecast × |
|---|---|---|---|
| The Greatest Showman | 2017 | 19.8 | 5.2 |
| Anyone But You | 2023 | 14.7 | 4.2 |
| Puss in Boots: The Last Wish | 2022 | 15.0 | 5.5 |
| Jumanji: Welcome to the Jungle | 2017 | 11.2 | 4.5 |
| Sinners | 2025 | 5.8 | 2.5 |
| Sound of Freedom | 2023 | 9.4 | 4.2 |
| The Substance | 2024 | 5.5 | 2.5 |
| Mrs. Harris Goes to Paris | 2022 | 5.3 | 2.4 |
| Godzilla Minus One | 2023 | 5.0 | 2.5 |
| Crazy Rich Asians | 2018 | 6.6 | 3.4 |

## C. Breakout probability: can a model flag a 2× surprise before opening?

Breakout = opened at ≥ 2× the traditional ridge T-7 forecast. Rolling quarterly 2017-2025, n = 860, base rate 9.0%.

- ROC-AUC **0.68** (0.5 = no better than chance)
- Brier score 0.0849 vs 0.0815 for always predicting the base rate (skill = -4.1%)

Calibration:

| bin            |   films |   predicted |   actual |
|:---------------|--------:|------------:|---------:|
| (-0.001, 0.05] |     673 |       0.017 |    0.062 |
| (0.05, 0.1]    |      92 |       0.073 |    0.163 |
| (0.1, 0.2]     |      61 |       0.141 |    0.213 |
| (0.2, 0.3]     |      12 |       0.24  |    0.25  |
| (0.3, 1.0]     |      22 |       0.483 |    0.182 |

Highest predicted breakout probabilities (and what happened):

| Film | Year | P(breakout) | Broke out? |
|---|---|---|---|
| Belle | 2022 | 0.91 | no |
| Phoenix Forgotten | 2017 | 0.80 | no |
| Kalki 2898 AD | 2024 | 0.72 | no |
| Inspector Sun | 2023 | 0.68 | no |
| Vengeance | 2022 | 0.66 | no |
| Good Boy | 2025 | 0.65 | no |
| The SpongeBob Movie: Search for SquarePants | 2025 | 0.62 | no |
| Lilo & Stitch | 2025 | 0.58 | yes |
| Die My Love | 2025 | 0.50 | no |
| Zootopia 2 | 2025 | 0.45 | yes |
| Ryan's World the Movie: Titan Universe Adventure | 2024 | 0.39 | no |
| The Promise | 2017 | 0.36 | no |
| Fear | 2023 | 0.36 | no |
| Jawan | 2023 | 0.36 | no |
| Born in China | 2017 | 0.35 | no |

