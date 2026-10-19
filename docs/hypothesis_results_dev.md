# Hypothesis results — DEVELOPMENT RUN (2025 sealed; post = 2022-2024)

Not the confirmatory result: that run adds 2025 once the model is frozen. Holm correction across H1-H5 is applied in the confirmatory run.

## H1 — star-power effect after 2020

**without theater count** (n = 872)

- star effect, 2013-2019: 0.061
- change after 2020: 0.032 (95% CI -0.139 to 0.202), one-sided p = 0.641

**with theater count** (n = 872)

- star effect, 2013-2019: 0.010
- change after 2020: 0.058 (95% CI -0.072 to 0.189), one-sided p = 0.809

Year-by-year star coefficient (descriptive):

| year | coef | 95% CI |
|---|---|---|
| 2013 | -0.253 | -0.525 to 0.018 |
| 2014 | 0.093 | -0.243 to 0.429 |
| 2015 | -0.005 | -0.296 to 0.287 |
| 2016 | 0.040 | -0.238 to 0.318 |
| 2017 | 0.019 | -0.271 to 0.308 |
| 2018 | 0.122 | -0.184 to 0.428 |
| 2019 | 0.327 | 0.010 to 0.644 |
| 2022 | 0.152 | -0.130 to 0.433 |
| 2023 | 0.043 | -0.248 to 0.334 |
| 2024 | 0.027 | -0.209 to 0.263 |

## H2 — predictability at T-7 (median absolute log error)

**ridge**: 2016-2019 = 0.362 (n=525), 2022-2024 = 0.400 (n=359)

- difference +0.038 (95% CI -0.024 to +0.132); bootstrap share ≤ 0: 0.121
- excluding 2022: +0.016 (95% CI -0.048 to +0.103); share ≤ 0: 0.292

**catboost**: 2016-2019 = 0.340 (n=525), 2022-2024 = 0.434 (n=359)

- difference +0.094 (95% CI +0.026 to +0.163); bootstrap share ≤ 0: 0.002
- excluding 2022: +0.015 (95% CI -0.021 to +0.088); share ≤ 0: 0.189

