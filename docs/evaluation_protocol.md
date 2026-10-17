# Evaluation protocol

1. Generate synthetic data with a recorded seed.
2. Build features using a forecast cutoff; target-date outcomes must not enter features.
3. Sort by date and reserve the latest 30 unique dates for the chronological test period.
4. Fit the context-aware model on earlier dates only.
5. Compare against a weekday/meal/dish mean computed from training rows only.
6. Report MAE and RMSE in portions, plus exact train/test date ranges, seed and test-row count.
7. Save the machine-readable report to `data/generated/evaluation_report.json`.

All scores describe a controlled synthetic simulation. They do not prove real-world food-waste
reduction. Uncertainty bounds in the starter prediction script are provisional ±20% ranges and
must not be described as statistically calibrated.
