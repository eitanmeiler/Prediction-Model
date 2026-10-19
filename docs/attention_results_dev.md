# Attention hypotheses — DEVELOPMENT RUN (2025 sealed; post = 2022-2024)

Films with attention data: 837 of 884 (2016-2024, excl. 2020-21); source-work attention for 218 adaptations.

## H3 — does attention reduce T-7 error? (MAE of log opening; gain > 0 means attention helps)

**ridge** (n = 746): MAE traditional 0.477 → with attention 0.472

- gain, all years: +0.005 (95% CI -0.003 to +0.013; bootstrap share ≤ 0: 0.129)
- gain 2017-2019: -0.003 (95% CI -0.016 to +0.009; bootstrap share ≤ 0: 0.666)
- gain 2022-2024: +0.013 (95% CI +0.002 to +0.024; bootstrap share ≤ 0: 0.008)
- H3b (post − pre): +0.016 (95% CI +0.000 to +0.033; bootstrap share ≤ 0: 0.025)

**catboost** (n = 746): MAE traditional 0.481 → with attention 0.448

- gain, all years: +0.033 (95% CI +0.019 to +0.046; bootstrap share ≤ 0: 0.000)
- gain 2017-2019: +0.018 (95% CI +0.001 to +0.035; bootstrap share ≤ 0: 0.020)
- gain 2022-2024: +0.049 (95% CI +0.028 to +0.070; bootstrap share ≤ 0: 0.000)
- H3b (post − pre): +0.031 (95% CI +0.004 to +0.060; bootstrap share ≤ 0: 0.014)

## H4 — source-work attention vs. the traditional model's misses (adaptations)

- n = 218; coefficient +0.043 (95% CI -0.005 to +0.090); one-sided p = 0.038

## H5 — attention acceleration vs. the traditional model's misses (controlling for level)

- n = 837; acceleration coefficient +0.089 (95% CI +0.010 to +0.168); one-sided p = 0.014; level coefficient +0.057

