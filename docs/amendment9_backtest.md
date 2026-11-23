# Amendment 9 candidates: backtest (exploratory)

CatBoost + attention at T-7, rolling quarterly 2017-2025 (2020-21 excluded), trained on 2016+ films before each quarter. Miss = |actual / forecast - 1|. Corrections are fitted only on earlier quarters.

Franchise families linked by title prefix (6): demon slayer (2 collections); how to train your dragon (2 collections); hunger games (2 collections); spiderman (2 collections); strangers (2 collections); teenage mutant ninja turtles (2 collections)

| Variant | Typical miss, all | 2022-2025 | 2025 | $100M+ openings: median actual/forecast | under-forecast |
|---|---|---|---|---|---|
| base | 33.4% | 35.5% | 33.7% | x1.76 | 40/42 |
| A | 34.0% | 35.9% | 35.0% | x1.84 | 40/42 |
| B | 33.3% | 34.9% | 33.9% | x1.62 | 36/42 |
| AB | 34.0% | 35.4% | 34.5% | x1.73 | 36/42 |

By year (typical miss):

| Year | base | A | B | AB |
|---|---|---|---|---|
| 2017 | 32.7% | 33.0% | 32.7% | 33.0% |
| 2018 | 29.1% | 29.4% | 29.1% | 29.4% |
| 2019 | 32.7% | 32.3% | 33.3% | 32.9% |
| 2022 | 43.5% | 45.1% | 42.8% | 45.1% |
| 2023 | 36.4% | 36.4% | 36.6% | 36.4% |
| 2024 | 30.4% | 26.6% | 29.8% | 26.6% |
| 2025 | 33.7% | 35.0% | 33.9% | 34.5% |
