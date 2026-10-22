"""Forecast integration with Person A's feature builder, model artifact and rules.

The artifact interface is Person A's documented contract. Inference follows
``scripts/predict.py`` exactly (selected model or conservative weekday baseline)
without duplicating Person A's ML training/feature logic.
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

import joblib
import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT, get_settings
from backend.app.core.errors import DomainError
from backend.app.db.models import Prediction
from src.features.feature_builder import build_features
from src.ml.forecasting import train_model

MEAL_TYPES = ("breakfast", "lunch", "snacks", "dinner")


def _load_artifact(artifact_path: Path) -> dict:
    if not artifact_path.exists():
        raise DomainError(
            "MODEL_ARTIFACT_MISSING",
            f"model artifact not found: {artifact_path}",
            503,
            {
                "path": str(artifact_path),
                "remedy": "POST /api/v1/forecasts/model/train or python scripts/train_model.py",
            },
        )
    try:
        artifact = joblib.load(artifact_path)
    except Exception as exc:
        raise DomainError(
            "MODEL_ARTIFACT_INVALID", f"Could not load model artifact: {exc}", 503
        ) from exc
    required = {"features", "model_version", "training_cutoff", "baseline_lookup", "baseline_overall"}
    missing = required - set(artifact)
    if missing:
        raise DomainError(
            "MODEL_ARTIFACT_INVALID",
            "model artifact is missing required fields",
            503,
            {"missing": sorted(missing), "path": str(artifact_path)},
        )
    if artifact.get("selected_model", "context_random_forest") != "weekday_baseline":
        model = artifact.get("model")
        if model is None or not hasattr(model, "predict"):
            raise DomainError(
                "MODEL_ARTIFACT_INVALID",
                "artifact selected a context model but contains no predict-capable model",
                503,
            )
    return artifact


def _artifact_metadata(artifact: dict) -> dict:
    return {
        "model_version": artifact["model_version"],
        "selected_model": artifact.get("selected_model", "legacy_context_model"),
        "forecast_cutoff": pd.Timestamp(artifact["training_cutoff"]).date(),
        "feature_schema_version": artifact.get("feature_schema_version", "1.0"),
        "interval_method": artifact.get("interval_method", "not available"),
        "interval_is_calibrated": bool(artifact.get("interval_is_calibrated", False)),
        "unit": artifact.get("target_unit", "portions"),
    }


def forecast_demand(
    db: Session | None,
    forecast_date: date,
    meal_type: str | None = None,
    persist: bool = True,
) -> dict:
    settings = get_settings()
    artifact = _load_artifact(settings.artifact_file)
    meta = _artifact_metadata(artifact)
    cutoff = pd.Timestamp(artifact["training_cutoff"]).normalize()
    target = pd.Timestamp(forecast_date).normalize()
    if target <= cutoff:
        raise DomainError(
            "FORECAST_DATE_NOT_FUTURE",
            f"forecast date must be after model training cutoff {cutoff.date().isoformat()}",
            422,
            {"forecast_date": forecast_date.isoformat(), "training_cutoff": cutoff.date().isoformat()},
        )

    operations_path = settings.data_path / "food_operations.csv"
    if not operations_path.exists():
        raise DomainError(
            "FORECAST_DATA_MISSING",
            f"historical operations not found: {operations_path}",
            409,
            {"hint": "POST /api/v1/data/generate and POST /api/v1/data/sync"},
        )
    operations = pd.read_csv(operations_path, parse_dates=["date"])
    if operations.empty:
        raise DomainError("FORECAST_DATA_INVALID", "food_operations.csv is empty", 409)

    requested_meals = [meal_type] if meal_type else list(MEAL_TYPES)
    rows: list[dict] = []
    for meal in requested_meals:
        hist = operations[
            (operations["date"] < target) & (operations["meal_type"] == meal)
        ].copy()
        if hist.empty:
            if meal_type:
                raise DomainError(
                    "FORECAST_HISTORY_MISSING",
                    f"no historical rows for {meal} before {forecast_date.isoformat()}",
                    409,
                )
            continue
        daily = hist.groupby(["date", "dish_id"], as_index=False).agg(
            demand_qty=("demand_qty", "sum")
        )
        for dish, group in daily.groupby("dish_id"):
            group = group.sort_values("date")
            features = {
                "weekday": target.dayofweek,
                "month": target.month,
                "demand_lag_1": float(group["demand_qty"].iloc[-1]),
                "demand_rolling_7": float(group["demand_qty"].tail(7).mean()),
                "meal_type": meal,
                "dish_id": str(dish),
            }
            frame = pd.DataFrame([{name: features[name] for name in artifact["features"]}])
            if meta["selected_model"] == "weekday_baseline":
                key = f"{meal}|{dish}|{target.dayofweek}"
                prediction = float(
                    artifact["baseline_lookup"].get(key, artifact["baseline_overall"])
                )
            else:
                prediction = float(artifact["model"].predict(frame)[0])
            prediction = max(0.0, prediction)
            lower = min(prediction, max(0.0, prediction + float(artifact.get("residual_lower", 0.0))))
            upper = max(prediction, lower, prediction + float(artifact.get("residual_upper", 0.0)))
            rows.append(
                {
                    "date": forecast_date,
                    "meal_type": meal,
                    "dish_id": str(dish),
                    "prediction": round(prediction, 2),
                    "lower_bound": round(lower, 2),
                    "upper_bound": round(upper, 2),
                    "model_version": meta["model_version"],
                    "selected_model": meta["selected_model"],
                    "forecast_cutoff": meta["forecast_cutoff"],
                    "feature_schema_version": meta["feature_schema_version"],
                    "interval_method": meta["interval_method"],
                    "interval_is_calibrated": meta["interval_is_calibrated"],
                    "unit": meta["unit"],
                    "is_synthetic": True,
                }
            )
    if not rows:
        raise DomainError(
            "FORECAST_HISTORY_MISSING",
            f"no historical demand is available before {forecast_date.isoformat()}",
            409,
        )
    rows.sort(key=lambda item: (item["meal_type"], item["dish_id"]))

    forecast_run_id = str(uuid.uuid4())
    if persist and db is not None:
        for row in rows:
            db.add(
                Prediction(
                    forecast_run_id=forecast_run_id,
                    forecast_date=row["date"],
                    meal_type=row["meal_type"],
                    dish_external_id=row["dish_id"],
                    prediction=row["prediction"],
                    lower_bound=row["lower_bound"],
                    upper_bound=row["upper_bound"],
                    model_version=row["model_version"],
                    selected_model=row["selected_model"],
                    forecast_cutoff=row["forecast_cutoff"],
                    feature_schema_version=row["feature_schema_version"],
                    interval_method=row["interval_method"],
                    interval_is_calibrated=row["interval_is_calibrated"],
                    unit=row["unit"],
                    is_synthetic=True,
                )
            )
        db.flush()

    return {
        "forecast_run_id": forecast_run_id,
        "requested_date": forecast_date,
        "meal_type": meal_type,
        "model_version": meta["model_version"],
        "selected_model": meta["selected_model"],
        "forecast_cutoff": meta["forecast_cutoff"],
        "feature_schema_version": meta["feature_schema_version"],
        "interval_method": meta["interval_method"],
        "interval_is_calibrated": meta["interval_is_calibrated"],
        "unit": meta["unit"],
        "is_synthetic": True,
        "rows": rows,
    }


def train_from_generated_data() -> dict:
    settings = get_settings()
    operations_path = settings.data_path / "food_operations.csv"
    if not operations_path.exists():
        raise DomainError(
            "TRAINING_DATA_MISSING",
            f"food_operations.csv not found: {operations_path}",
            409,
            {"hint": "Generate synthetic data first."},
        )
    operations = pd.read_csv(operations_path, parse_dates=["date"])
    cutoff = operations["date"].max() + pd.DateOffset(days=1)
    features = build_features(operations, forecast_cutoff=cutoff)
    try:
        artifact = train_model(features, artifact_path=str(settings.artifact_file))
    except ValueError as exc:
        raise DomainError("MODEL_TRAINING_FAILED", str(exc), 422) from exc
    return {
        "model_version": artifact["model_version"],
        "selected_model": artifact["selected_model"],
        "training_cutoff": pd.Timestamp(artifact["training_cutoff"]).date(),
        "feature_schema_version": artifact["feature_schema_version"],
        "validation_context_mae": artifact["validation_context_mae"],
        "validation_baseline_mae": artifact["validation_baseline_mae"],
        "artifact_path": str(settings.artifact_file),
    }


def list_predictions(
    db: Session,
    forecast_run_id: str | None = None,
    forecast_date: date | None = None,
    meal_type: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Prediction], int]:
    stmt = select(Prediction)
    count_stmt = select(func.count()).select_from(Prediction)
    if forecast_run_id:
        stmt = stmt.where(Prediction.forecast_run_id == forecast_run_id)
        count_stmt = count_stmt.where(Prediction.forecast_run_id == forecast_run_id)
    if forecast_date:
        stmt = stmt.where(Prediction.forecast_date == forecast_date)
        count_stmt = count_stmt.where(Prediction.forecast_date == forecast_date)
    if meal_type:
        stmt = stmt.where(Prediction.meal_type == meal_type)
        count_stmt = count_stmt.where(Prediction.meal_type == meal_type)
    total = int(db.scalar(count_stmt) or 0)
    items = list(
        db.scalars(
            stmt.order_by(Prediction.forecast_date, Prediction.meal_type, Prediction.dish_external_id)
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return items, total
