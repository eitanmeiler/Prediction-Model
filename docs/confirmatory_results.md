# Confirmatory results (sealed 2025 unsealed once; spec frozen at commit e21bcc8)

## 2025 holdout scorecard (models trained only on earlier films, retrained quarterly)

|                          |   films |   median_abs_pct_err |   within_25pct |   mae_log |   interval80_coverage |
|:-------------------------|--------:|---------------------:|---------------:|----------:|----------------------:|
| ('T-28', 'catboost')     |     148 |                 49   |           23   |       0.6 |                  85.8 |
| ('T-28', 'catboost_att') |     148 |                 42   |           29.7 |       0.6 |                  78.4 |
| ('T-28', 'catboost_t16') |     148 |                 50.4 |           26.4 |       0.6 |                  83.1 |
| ('T-28', 'comps')        |     148 |                 73.1 |           16.9 |       1.1 |                  85.1 |
| ('T-28', 'ridge')        |     148 |                 49.9 |           29.1 |       0.6 |                  82.4 |
| ('T-28', 'ridge_att')    |     148 |                 48.9 |           23   |       0.6 |                  80.4 |
| ('T-28', 'ridge_t16')    |     148 |                 47.3 |           25   |       0.6 |                  83.1 |
| ('T-7', 'catboost')      |     148 |                 32.1 |           39.9 |       0.4 |                  81.1 |
| ('T-7', 'catboost_att')  |     148 |                 34.6 |           38.5 |       0.4 |                  76.4 |
| ('T-7', 'catboost_t16')  |     148 |                 36.1 |           37.2 |       0.4 |                  81.8 |
| ('T-7', 'comps')         |     148 |                 73.1 |           16.9 |       1.1 |                  85.1 |
| ('T-7', 'ridge')         |     148 |                 35.8 |           38.5 |       0.5 |                  80.4 |
| ('T-7', 'ridge_att')     |     148 |                 35.9 |           32.4 |       0.5 |                  80.4 |
| ('T-7', 'ridge_t16')     |     148 |                 36.8 |           37.2 |       0.5 |                  79.7 |

## Hypothesis tests (post period = 2022-2025)

### H1 — star effect after 2020

- without theater count (n=963): pre-2020 star effect 0.044; change after 2020 +0.081 (95% CI -0.067 to +0.229); one-sided p = 0.858
- with theater count (n=963): pre-2020 star effect -0.002; change after 2020 +0.090 (95% CI -0.025 to +0.204); one-sided p = 0.938

### H2 — predictability at T-7 (median |log error|)

- ridge: 2016-19 0.360 → 2022-25 0.426; diff +0.065 (95% CI -0.005 to +0.125); share ≤ 0 = 0.035
- catboost: 2016-19 0.336 → 2022-25 0.416; diff +0.080 (95% CI +0.022 to +0.147); share ≤ 0 = 0.004

### H3 — attention gain at T-7 (MAE of log opening, 2017-2025; >0 = attention helps)

- ridge (n=894): gain +0.003 (95% CI -0.005 to +0.010); share ≤ 0 = 0.254; H3b post−pre +0.010 (95% CI -0.006 to +0.026; share ≤ 0 = 0.110)
- catboost (n=894): gain +0.029 (95% CI +0.016 to +0.042); share ≤ 0 = 0.000; H3b post−pre +0.019 (95% CI -0.005 to +0.045; share ≤ 0 = 0.061)

### H4 / H5 — attention vs. the traditional model's misses

- H4 (n=253): source-work attention +0.048 (95% CI +0.000 to +0.095); one-sided p = 0.024
- H5 (n=977): acceleration +0.104 (95% CI +0.037 to +0.171); one-sided p = 0.001

## Holm correction (α = 0.05; p = the conservative value defined in the frozen spec)

| H | p | Holm threshold | supported |
|---|---|---|---|
| H1 | 0.9377 | 0.0500 | no |
| H2 | 0.0348 | 0.0167 | no |
| H3 | 0.2542 | 0.0250 | no |
| H4 | 0.0245 | 0.0125 | no |
| H5 | 0.0012 | 0.0100 | **yes** |
