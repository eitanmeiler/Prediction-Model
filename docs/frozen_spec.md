# Frozen specification for the confirmatory (sealed 2025) run

Committed **2026-10-19, before any 2025 result was computed or viewed**. The commit hash of this file is the
reference: the confirmatory run uses the code exactly as it stands at that commit. Nothing below changes after the
run, whatever the results.

## What is frozen
- **Data**: `data/processed/model_table.csv` as built by `pipeline/features.py` at this commit (opened in ≥ 800
  theaters; re-releases dropped; events and streaming-first titles excluded via `in_model`).
- **Features**: `models/feature_sets.py` at this commit (budget excluded; T-7 = EARLY + LATE; T-28 = EARLY;
  attention = att_level, att_accel, att_t60, src_att).
- **Models**: comps baseline, ridge (RidgeCV, alphas 10^-2..10^3), CatBoost (700 iterations, depth 6, lr 0.05,
  seed 7), CatBoost + attention (same settings, trained on 2016+ films) — `models/backtest.py`.
- **Evaluation**: the same rolling quarterly backtest, extended through 2025Q4. 80% ranges from the previous
  8 quarters' errors.
- **Primary live model** (decided 2026-10-19 on development results): **CatBoost + attention**, with ridge reported
  alongside. Chosen because it was clearly more accurate on the same 2017-2024 films (T-7 typical miss 34% vs 39%).

## Confirmatory tests (post period = 2022-2025)
| H | Test | p-value used for Holm |
|---|---|---|
| H1 | star × post interaction, OLS with year FE (with and without theater count) | the **larger** of the two one-sided p's |
| H2 | median |log error| at T-7, 2022-2025 minus 2016-2019 (bootstrap) | the **larger** bootstrap share ≤ 0 of ridge / CatBoost |
| H3 | attention gain in MAE, 2017-2025 test quarters | the **larger** bootstrap share ≤ 0 of ridge / CatBoost |
| H4 | source-work attention vs traditional-model residuals (adaptations) | one-sided p |
| H5 | attention acceleration vs residuals, controlling for level | one-sided p |

Taking the larger p across the two models means no conclusion rests on picking the model that happened to do
better (Amendment 3). **Holm correction at α = 0.05** across the five. A hypothesis is "supported" only if it
survives Holm. H3b (gain larger after 2020) is reported as secondary, without correction.

## Holdout scorecard
The 2025 films are also scored directly (every model, both checkpoints): typical miss, share within ±25%,
80%-range coverage. These are reported as they come out, good or bad.
