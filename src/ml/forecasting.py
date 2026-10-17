"""Chronological demand forecasting and evaluation utilities."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = ["weekday", "month", "demand_lag_1", "demand_rolling_7"]
MODEL_VERSION = "context-hgb-v2"
SEED = 42

def _clean(features):
    required = set(FEATURES + ["date", "meal_type", "dish_id", "demand_qty"])
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"features missing required columns: {sorted(missing)}")
    data = features.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["demand_qty"] = pd.to_numeric(data["demand_qty"], errors="raise")
    data = data.dropna(subset=FEATURES + ["demand_qty"]).sort_values("date")
    if (data["demand_qty"] < 0).any():
        raise ValueError("demand_qty cannot be negative")
    return data

def _baseline(train, test):
    means = train.groupby(["meal_type", "dish_id", "weekday"])["demand_qty"].mean()
    overall = float(train["demand_qty"].mean())
    return test.apply(lambda row: means.get((row.meal_type, row.dish_id, row.weekday), overall), axis=1).astype(float).to_numpy()

def train_model(features, artifact_path="ml/artifacts/context_model.joblib"):
    """Fit final model and store chronological calibration-residual quantiles."""
    data = _clean(features)
    unique_dates = sorted(data["date"].dt.normalize().unique())
    if len(data) < 30 or len(unique_dates) < 10:
        raise ValueError("Need at least 30 feature rows spanning 10 dates to train")
    calibration_days = max(2, min(14, len(unique_dates) // 5))
    calibration_start = unique_dates[-calibration_days]
    fit = data[data["date"].dt.normalize() < calibration_start]
    calibration = data[data["date"].dt.normalize() >= calibration_start]
    if fit.empty or calibration.empty:
        raise ValueError("Unable to create chronological calibration split")
    calibration_model = HistGradientBoostingRegressor(max_iter=100, random_state=SEED)
    calibration_model.fit(fit[FEATURES].astype(float), fit["demand_qty"].astype(float))
    calibration_pred = np.maximum(0, calibration_model.predict(calibration[FEATURES].astype(float)))
    residuals = calibration["demand_qty"].to_numpy(dtype=float) - calibration_pred
    lower_residual, upper_residual = float(np.quantile(residuals, .10)), float(np.quantile(residuals, .90))
    model = HistGradientBoostingRegressor(max_iter=100, random_state=SEED)
    model.fit(data[FEATURES].astype(float), data["demand_qty"].astype(float))
    artifact = {"model": model, "features": FEATURES, "model_version": MODEL_VERSION,
        "training_cutoff": str(data["date"].max().date()), "random_seed": SEED,
        "feature_schema_version": "1.1", "target_unit": "portions",
        "interval_method": "10th/90th quantiles of chronological calibration residuals",
        "calibration_period": f"{calibration['date'].min().date()} to {calibration['date'].max().date()}",
        "calibration_rows": int(len(calibration)), "residual_lower": lower_residual,
        "residual_upper": upper_residual, "interval_coverage_target": .80,
        "interval_is_calibrated": False, "dependency_note": "See requirements.txt"}
    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact

def evaluate_chronologically(features, test_days=30):
    """Compare context model and historical weekday baseline on identical future dates."""
    data = _clean(features)
    unique_dates = sorted(data["date"].dt.normalize().unique())
    if len(unique_dates) <= test_days:
        raise ValueError("Not enough unique dates for chronological holdout")
    test_start = unique_dates[-test_days]
    train, test = data[data["date"].dt.normalize() < test_start], data[data["date"].dt.normalize() >= test_start]
    if train.empty or test.empty:
        raise ValueError("Chronological split produced empty train/test set")
    model = HistGradientBoostingRegressor(max_iter=100, random_state=SEED)
    model.fit(train[FEATURES].astype(float), train["demand_qty"].astype(float))
    pred = np.maximum(0, model.predict(test[FEATURES].astype(float)))
    baseline = np.maximum(0, _baseline(train, test))
    actual = test["demand_qty"].to_numpy(dtype=float)
    context_mae, baseline_mae = mean_absolute_error(actual, pred), mean_absolute_error(actual, baseline)
    results = {"train_period": f"{train.date.min().date()} to {train.date.max().date()}",
        "test_period": f"{test.date.min().date()} to {test.date.max().date()}",
        "context_mae": float(context_mae), "context_rmse": float(mean_squared_error(actual, pred)**.5),
        "baseline_mae": float(baseline_mae), "baseline_rmse": float(mean_squared_error(actual, baseline)**.5),
        "test_rows": int(len(test)), "seed": SEED, "model_version": MODEL_VERSION,
        "features": FEATURES, "target_unit": "portions", "context_beats_baseline_mae": bool(context_mae < baseline_mae),
        "caveat": "Synthetic data only; scores do not establish real-world waste reduction.", "by_meal_type": {}}
    scored = test.assign(_actual=actual, _context=pred, _baseline=baseline)
    for meal, group in scored.groupby("meal_type"):
        results["by_meal_type"][str(meal)] = {"rows": int(len(group)),
            "context_mae": float(mean_absolute_error(group["_actual"], group["_context"])),
            "baseline_mae": float(mean_absolute_error(group["_actual"], group["_baseline"]))}
    return results
