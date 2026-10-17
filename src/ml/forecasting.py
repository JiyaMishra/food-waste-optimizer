"""Chronological demand forecasting, baseline selection, and evaluation."""
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

NUMERIC_FEATURES = ["weekday", "month", "demand_lag_1", "demand_rolling_7"]
CATEGORICAL_FEATURES = ["meal_type", "dish_id"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
MODEL_VERSION = "context-rf-v4"
SEED = 42

def _clean(features):
    required = set(FEATURES + ["date", "demand_qty"])
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"features missing required columns: {sorted(missing)}")
    data = features.copy()
    data["date"] = pd.to_datetime(data["date"], errors="raise")
    data["demand_qty"] = pd.to_numeric(data["demand_qty"], errors="raise")
    for col in NUMERIC_FEATURES:
        data[col] = pd.to_numeric(data[col], errors="raise")
    data = data.dropna(subset=FEATURES + ["demand_qty"]).sort_values("date")
    if data.empty:
        raise ValueError("No complete feature rows to train/evaluate")
    if (data["demand_qty"] < 0).any():
        raise ValueError("demand_qty cannot be negative")
    for col in CATEGORICAL_FEATURES:
        data[col] = data[col].astype(str)
    return data

def _make_model():
    preprocess = ColumnTransformer([
        ("numeric", "passthrough", NUMERIC_FEATURES),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
    ])
    estimator = RandomForestRegressor(n_estimators=250, min_samples_leaf=3, max_features=0.9,
                                      random_state=SEED, n_jobs=-1)
    return Pipeline([("preprocess", preprocess), ("model", estimator)])

def _baseline_map(train):
    grouped = train.groupby(["meal_type", "dish_id", "weekday"])["demand_qty"].mean()
    return {f"{meal}|{dish}|{int(day)}": float(value)
            for (meal, dish, day), value in grouped.items()}, float(train["demand_qty"].mean())

def _baseline_predict(train, test):
    lookup, overall = _baseline_map(train)
    return np.asarray([lookup.get(f"{row.meal_type}|{row.dish_id}|{int(row.weekday)}", overall)
                       for row in test.itertuples()], dtype=float)

def _baseline_from_artifact(artifact, row):
    key = f"{row['meal_type']}|{row['dish_id']}|{int(row['weekday'])}"
    return float(artifact["baseline_lookup"].get(key, artifact["baseline_overall"]))

def train_model(features, artifact_path="ml/artifacts/context_model.joblib"):
    """Select a model only if it beats the weekday baseline on a chronological validation window."""
    data = _clean(features)
    dates = sorted(data["date"].dt.normalize().unique())
    if len(data) < 30 or len(dates) < 10:
        raise ValueError("Need at least 30 feature rows spanning 10 dates to train")
    validation_days = max(2, min(30, len(dates) // 5))
    validation_start = dates[-validation_days]
    fit = data[data["date"].dt.normalize() < validation_start]
    validation = data[data["date"].dt.normalize() >= validation_start]
    if fit.empty or validation.empty:
        raise ValueError("Unable to create chronological validation split")
    candidate = _make_model()
    candidate.fit(fit[FEATURES], fit["demand_qty"].astype(float))
    candidate_pred = np.maximum(0, candidate.predict(validation[FEATURES]))
    baseline_pred = np.maximum(0, _baseline_predict(fit, validation))
    candidate_mae = float(mean_absolute_error(validation["demand_qty"], candidate_pred))
    baseline_mae = float(mean_absolute_error(validation["demand_qty"], baseline_pred))
    selected = "context_random_forest" if candidate_mae < baseline_mae else "weekday_baseline"
    # Residual intervals are descriptive empirical offsets; do not claim statistical calibration.
    selected_residuals = (validation["demand_qty"].to_numpy(dtype=float) -
        (candidate_pred if selected == "context_random_forest" else baseline_pred))
    lower_residual = float(np.quantile(selected_residuals, .10))
    upper_residual = float(np.quantile(selected_residuals, .90))
    final_model = _make_model()
    final_model.fit(data[FEATURES], data["demand_qty"].astype(float))
    baseline_lookup, baseline_overall = _baseline_map(data)
    artifact = {"model": final_model, "selected_model": selected, "baseline_lookup": baseline_lookup,
        "baseline_overall": baseline_overall, "validation_context_mae": candidate_mae,
        "validation_baseline_mae": baseline_mae, "features": FEATURES,
        "numeric_features": NUMERIC_FEATURES, "categorical_features": CATEGORICAL_FEATURES,
        "model_version": MODEL_VERSION, "training_cutoff": str(data["date"].max().date()),
        "random_seed": SEED, "feature_schema_version": "1.3", "target_unit": "portions",
        "interval_method": "10th/90th quantiles of chronological validation residuals",
        "calibration_period": f"{validation['date'].min().date()} to {validation['date'].max().date()}",
        "calibration_rows": int(len(validation)), "residual_lower": lower_residual,
        "residual_upper": upper_residual, "interval_coverage_target": .80,
        "interval_is_calibrated": False,
        "selection_note": "Context model selected only when its chronological validation MAE is lower than the weekday baseline."}
    Path(artifact_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, artifact_path)
    return artifact

def evaluate_chronologically(features, test_days=30):
    """Compare candidate model and weekday baseline on identical future holdout dates."""
    data = _clean(features)
    dates = sorted(data["date"].dt.normalize().unique())
    if len(dates) <= test_days:
        raise ValueError("Not enough unique dates for chronological holdout")
    test_start = dates[-test_days]
    train, test = data[data["date"].dt.normalize() < test_start], data[data["date"].dt.normalize() >= test_start]
    if train.empty or test.empty:
        raise ValueError("Chronological split produced empty train/test set")
    model = _make_model()
    model.fit(train[FEATURES], train["demand_qty"].astype(float))
    pred = np.maximum(0, model.predict(test[FEATURES]))
    baseline = np.maximum(0, _baseline_predict(train, test))
    actual = test["demand_qty"].to_numpy(dtype=float)
    context_mae, baseline_mae = mean_absolute_error(actual, pred), mean_absolute_error(actual, baseline)
    results = {"train_period": f"{train.date.min().date()} to {train.date.max().date()}",
        "test_period": f"{test.date.min().date()} to {test.date.max().date()}",
        "context_mae": float(context_mae), "context_rmse": float(mean_squared_error(actual, pred)**.5),
        "baseline_mae": float(baseline_mae), "baseline_rmse": float(mean_squared_error(actual, baseline)**.5),
        "test_rows": int(len(test)), "seed": SEED, "model_version": MODEL_VERSION,
        "features": FEATURES, "target_unit": "portions",
        "context_beats_baseline_mae": bool(context_mae < baseline_mae),
        "caveat": "Synthetic data only; scores do not establish real-world waste reduction.",
        "by_meal_type": {}}
    scored = test.assign(_actual=actual, _context=pred, _baseline=baseline)
    for meal, group in scored.groupby("meal_type"):
        results["by_meal_type"][str(meal)] = {"rows": int(len(group)),
            "context_mae": float(mean_absolute_error(group["_actual"], group["_context"])),
            "baseline_mae": float(mean_absolute_error(group["_actual"], group["_baseline"]))}
    return results
