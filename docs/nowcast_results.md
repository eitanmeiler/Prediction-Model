# H9 — catching word of mouth early (nowcast of the final total, 9 days after release)

Legs = log(domestic total ÷ opening weekend). Gain = MAE(base) − MAE(+ post-release momentum).

| Model | MAE base | MAE + momentum | Gain (95% CI) | share ≤ 0 | typical total-gross miss base → + momentum |
|---|---|---|---|---|---|
| ridge | 0.173 | 0.172 | +0.001 (-0.000 to +0.003) | 0.084 | 14% → 14% |
| catboost | 0.173 | 0.173 | -0.000 (-0.004 to +0.003) | 0.547 | 14% → 14% |

Conservative p = **0.547** → H9 **not supported** at α = 0.05.

Where momentum helped most (CatBoost; × = total ÷ opening):

| Film | Year | Actual × | Base forecast × | With momentum × |
|---|---|---|---|---|
| Reagan | 2024 | 3.9 | 2.8 | 3.3 |
| Good Boy | 2025 | 2.8 | 2.2 | 2.5 |
| Ferrari | 2023 | 4.7 | 4.1 | 4.7 |
| The Pope's Exorcist | 2023 | 2.2 | 3.0 | 2.6 |
| The Substance | 2024 | 5.5 | 2.4 | 2.8 |
| Wicked: For Good | 2025 | 2.3 | 3.8 | 3.3 |
| Homestead | 2024 | 3.5 | 5.9 | 5.2 |
| The Wild Robot | 2024 | 4.0 | 3.4 | 3.8 |
| Mortal Engines | 2018 | 2.1 | 3.8 | 3.3 |
| Babygirl | 2024 | 6.3 | 4.6 | 5.1 |
