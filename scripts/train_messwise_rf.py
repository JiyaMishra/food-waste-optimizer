"""Reproducible training script for the MessWise Random Forest Demand Model (rf_v1).

Strictly adheres to target-leakage prevention guidelines:
DO NOT use expected_consumers, consumed_portions, leftover_portions,
waste_rate_pct, or prepared_portions as input features.

Features used at prediction time:
- Categorical: food_item, meal, day_of_week
- Numerical: synthetic_liking_score, exam_intensity, temperature_c, rainfall_mm,
             is_weekend, hostel_attendance_estimate, historical_demand_rate
Target: expected_consumers
"""
from __future__ import annotations

import os
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

SEED = 42
MODEL_VERSION = "rf_v1"
FEATURE_SCHEMA_VERSION = "1.0"

NUMERIC_FEATURES = [
    "synthetic_liking_score",
    "exam_intensity",
    "temperature_c",
    "rainfall_mm",
    "is_weekend",
    "hostel_attendance_estimate",
    "historical_demand_rate",
]
CATEGORICAL_FEATURES = ["food_item", "meal", "day_of_week"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TARGET = "expected_consumers"

LEAKAGE_COLUMNS = [
    "expected_consumers",
    "consumed_portions",
    "leftover_portions",
    "waste_rate_pct",
    "prepared_portions",
]


def load_dataset(csv_path: str = "data/messwise_full_august_2026_menu_dataset.csv") -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        alt_path = Path("data/messwise_full_august_2026_menu_dataset(1).csv")
        if alt_path.exists():
            path = alt_path
        else:
            raise FileNotFoundError(f"Dataset not found at {csv_path}")
    df = pd.read_csv(path)
    return df


def validate_schema(df: pd.DataFrame) -> None:
    required = set(ALL_FEATURES + [TARGET])
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {missing}")


def build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", "passthrough", NUMERIC_FEATURES),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    regressor = RandomForestRegressor(
        n_estimators=150,
        max_depth=16,
        min_samples_split=3,
        min_samples_leaf=2,
        random_state=SEED,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("regressor", regressor)])


def train_and_evaluate(
    csv_path: str = "data/messwise_full_august_2026_menu_dataset.csv",
    artifact_path: str = "ml/artifacts/messwise_rf_v1.joblib",
) -> dict:
    df = load_dataset(csv_path)
    validate_schema(df)

    X = df[ALL_FEATURES]
    y = df[TARGET]

    # Chronological or held-out test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=SEED, shuffle=True
    )

    # Simple domain baseline: attendance * historical_demand_rate
    baseline_pred = (
        X_test["hostel_attendance_estimate"] * X_test["historical_demand_rate"]
    ).round()
    baseline_mae = float(mean_absolute_error(y_test, baseline_pred))

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_pred = np.maximum(0, y_pred).round()

    test_mae = float(mean_absolute_error(y_test, y_pred))
    test_rmse = float(mean_squared_error(y_test, y_pred) ** 0.5)
    test_r2 = float(r2_score(y_test, y_pred))

    # Fit final model on full dataset for production inference
    final_pipeline = build_pipeline()
    final_pipeline.fit(X, y)

    artifact = {
        "model": final_pipeline,
        "model_version": MODEL_VERSION,
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "random_seed": SEED,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_features": ALL_FEATURES,
        "target": TARGET,
        "test_mae": test_mae,
        "test_rmse": test_rmse,
        "test_r2": test_r2,
        "baseline_mae": baseline_mae,
        "training_samples": len(df),
        "dataset_name": Path(csv_path).name,
        "is_synthetic": True,
        "note": (
            "Random Forest demand model trained on synthetic menu dataset. "
            "Outcome columns (consumed_portions, leftover_portions, waste_rate_pct, prepared_portions) "
            "were strictly excluded from prediction features."
        ),
    }

    out_file = Path(artifact_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, out_file)
    print(f"Artifact successfully saved to {out_file}")
    print(f"Model Version: {MODEL_VERSION}")
    print(f"Test MAE: {test_mae:.2f} | Baseline MAE: {baseline_mae:.2f} | R²: {test_r2:.4f}")
    return artifact


if __name__ == "__main__":
    train_and_evaluate()
