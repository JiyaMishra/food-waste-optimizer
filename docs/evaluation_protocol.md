# Forecast evaluation protocol

## Target and unit
The target is synthetic dish-level demand in portions. No metric from this generated data is evidence of real-world waste reduction.

## Split
Use a chronological holdout: the final 30 unique dates are the test period; earlier dates are training. Do not randomly split rows. Context-aware predictions and baseline predictions are scored on the same holdout rows.

## Baseline
For each test row, predict the mean demand for the same dish, meal type and weekday from training rows only. If no comparable training key exists, use the training-set overall mean.

## Metrics
Report MAE and RMSE in portions overall and by meal type. Reports include training/test date ranges, seed, model version and row counts.

## Prediction intervals
Training reserves the latest chronological calibration dates, computes residual quantiles, then fits the final model on the full available feature history. Saved interval offsets are an empirical prototype and are not called calibrated unless interval coverage is separately verified on an untouched holdout. Attendance interval spreads are descriptive, not calibrated prediction intervals.

## Leakage limitations
Demand lag and rolling features are shifted within each dish/meal series. Evaluation is a one-step-ahead backtest: a test row's lag features may use observed demand from prior test dates. This reflects daily updating when prior meal outcomes are available; it does not represent a single multi-day forecast issued before the holdout begins.
