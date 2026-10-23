"""Agent 2: Demand Forecasting Agent.

Loads the saved Random Forest model (rf_v1) and predicts expected consumers.
Strictly separates model loading from requests, enforces prediction bounds
(0 <= predicted <= attendance), and provides clear plain-English explanations.
"""
from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd

from backend.app.services.dataset_service import get_record, get_dish_history, get_meal_context

logger = logging.getLogger("food_optimizer.demand_agent")

MODEL_PATH = Path("ml/artifacts/messwise_rf_v1.joblib")
_cached_artifact: dict[str, Any] | None = None


def get_model_artifact() -> dict[str, Any]:
    global _cached_artifact
    if _cached_artifact is not None:
        return _cached_artifact

    if not MODEL_PATH.exists():
        # Fall back to training on the fly if artifact doesn't exist
        from scripts.train_messwise_rf import train_and_evaluate
        logger.warning(f"Model artifact not found at {MODEL_PATH}; training model now...")
        _cached_artifact = train_and_evaluate()
        return _cached_artifact

    _cached_artifact = joblib.load(MODEL_PATH)
    return _cached_artifact


def predict_demand(
    food_item: str,
    meal: str,
    date_str: str,
    attendance: int | None = None,
    exam_intensity: float | None = None,
    temperature_c: float | None = None,
    rainfall_mm: float | None = None,
    preference_score: float | None = None,
) -> dict[str, Any]:
    """Execute the Random Forest demand forecast with safe bounds and feature validation."""
    artifact = get_model_artifact()
    model = artifact["model"]
    model_version = artifact.get("model_version", "rf_v1")

    # 1. Resolve date and calendar features
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = dt.strftime("%A")
        is_weekend = 1 if dt.weekday() >= 5 else 0
    except Exception:
        dt = datetime.date.today()
        day_of_week = "Monday"
        is_weekend = 0

    # 2. Look up historical record or meal context to populate missing fields safely
    record = get_record(date_str, meal, food_item)
    meal_ctx = get_meal_context(date_str, meal)

    # Resolve attendance
    if attendance is None or attendance <= 0:
        if record and "hostel_attendance_estimate" in record:
            final_attendance = int(record["hostel_attendance_estimate"])
        else:
            final_attendance = int(meal_ctx.get("hostel_attendance_estimate", 450))
    else:
        final_attendance = int(attendance)

    # Resolve exam intensity (0.0 to 1.0)
    if exam_intensity is None:
        if record and "exam_intensity" in record:
            final_exam = float(record["exam_intensity"])
        else:
            final_exam = float(meal_ctx.get("exam_intensity", 0.35))
    else:
        final_exam = max(0.0, min(1.0, float(exam_intensity)))

    # Resolve weather
    if temperature_c is None:
        if record and "temperature_c" in record:
            final_temp = float(record["temperature_c"])
        else:
            final_temp = float(meal_ctx.get("temperature_c", 28.0))
    else:
        final_temp = float(temperature_c)

    if rainfall_mm is None:
        if record and "rainfall_mm" in record:
            final_rain = float(record["rainfall_mm"])
        else:
            final_rain = float(meal_ctx.get("rainfall_mm", 0.0))
    else:
        final_rain = max(0.0, float(rainfall_mm))

    # Resolve liking score and demand rate
    history = get_dish_history(food_item, meal=meal, limit=20)
    if preference_score is not None:
        final_liking = max(0.0, min(1.0, float(preference_score) / 100.0 if preference_score > 1.0 else float(preference_score)))
    elif record and "synthetic_liking_score" in record:
        final_liking = float(record["synthetic_liking_score"])
    elif history:
        final_liking = float(np.mean([r["synthetic_liking_score"] for r in history if "synthetic_liking_score" in r]))
    else:
        final_liking = 0.70

    if record and "historical_demand_rate" in record:
        final_demand_rate = float(record["historical_demand_rate"])
    elif history:
        final_demand_rate = float(np.mean([r["historical_demand_rate"] for r in history if "historical_demand_rate" in r]))
    else:
        final_demand_rate = 0.65

    # 3. Assemble single-row DataFrame matching the exact training schema
    feature_row = pd.DataFrame(
        [
            {
                "synthetic_liking_score": final_liking,
                "exam_intensity": final_exam,
                "temperature_c": final_temp,
                "rainfall_mm": final_rain,
                "is_weekend": is_weekend,
                "hostel_attendance_estimate": final_attendance,
                "historical_demand_rate": final_demand_rate,
                "food_item": food_item,
                "meal": meal,
                "day_of_week": day_of_week,
            }
        ]
    )

    # 4. Model Prediction
    raw_pred = model.predict(feature_row)[0]
    predicted = int(round(max(0.0, raw_pred)))

    # Bound prediction: Cannot exceed hostel attendance
    bounded_pred = min(predicted, final_attendance)

    # 5. Build uncertainty and confidence bounds (using empirical validation residual MAE)
    test_mae = artifact.get("test_mae", 3.5)
    lower_bound = max(0, int(round(bounded_pred - 1.645 * test_mae)))
    upper_bound = min(final_attendance, int(round(bounded_pred + 1.645 * test_mae)))

    input_summary = {
        "food_item": food_item,
        "date": date_str,
        "meal": meal,
        "day_of_week": day_of_week,
        "attendance_estimate": final_attendance,
        "preference_score": round(final_liking * 100),
        "historical_demand_rate": round(final_demand_rate, 3),
        "exam_intensity": round(final_exam, 2),
        "temperature_c": round(final_temp, 1),
        "rainfall_mm": round(final_rain, 1),
    }

    explanation = (
        f"Estimated demand: {bounded_pred} servings. This forecast was generated by the "
        f"trained Random Forest model ({model_version}) using an attendance estimate of {final_attendance}, "
        f"a dish preference rating of {round(final_liking * 100)}/100, and current academic/weather conditions "
        f"(exam intensity: {final_exam:.1f}, rain: {final_rain:.1f}mm)."
    )

    return {
        "agent": "demand_forecasting",
        "food_item": food_item,
        "meal": meal,
        "date": date_str,
        "predicted_consumers": bounded_pred,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "model_version": model_version,
        "input_summary": input_summary,
        "uncertainty": {
            "method": "empirical_residual_bounds (90% interval)",
            "lower": lower_bound,
            "upper": upper_bound,
            "validation_mae": round(test_mae, 2),
        },
        "explanation": explanation,
    }
