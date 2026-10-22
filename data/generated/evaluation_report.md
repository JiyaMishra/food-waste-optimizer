# Synthetic demand forecasting evaluation

- Training period: 2026-07-04 to 2026-08-01
- Holdout period: 2026-08-02 to 2026-08-31
- Holdout rows: 2160
- Random seed: 42
- Model version: context-rf-v4
- Target unit: portions

| Model | MAE (portions) | RMSE (portions) |
|---|---:|---:|
| Context-aware | 6.884 | 8.580 |
| Weekday baseline | 7.065 | 8.836 |

Context model beats baseline MAE: **True**

## By meal type

| Meal | Rows | Context MAE | Baseline MAE |
|---|---:|---:|---:|
| breakfast | 660 | 5.354 | 5.681 |
| dinner | 450 | 9.483 | 9.331 |
| lunch | 660 | 7.199 | 7.417 |
| snacks | 390 | 5.941 | 6.200 |

> Limitation: Synthetic data only; scores do not establish real-world waste reduction.
