from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

MealType = Literal["breakfast", "lunch", "snacks", "dinner"]


class ForecastRequest(BaseModel):
    date: date
    meal_type: MealType | None = None
    persist: bool = True


class ForecastRow(BaseModel):
    date: date
    meal_type: str
    dish_id: str
    prediction: float = Field(ge=0)
    lower_bound: float = Field(ge=0)
    upper_bound: float = Field(ge=0)
    model_version: str
    selected_model: str
    forecast_cutoff: date
    feature_schema_version: str
    interval_method: str
    interval_is_calibrated: bool
    unit: str = "portions"
    is_synthetic: bool = True


class ForecastResponse(BaseModel):
    forecast_run_id: str
    requested_date: date
    meal_type: str | None = None
    model_version: str
    selected_model: str
    forecast_cutoff: date
    feature_schema_version: str
    interval_method: str
    interval_is_calibrated: bool
    unit: str = "portions"
    is_synthetic: bool = True
    rows: list[ForecastRow]
    caveat: str = (
        "Synthetic forecast. Prediction intervals are empirical and not claimed calibrated."
    )


class TrainModelRequest(BaseModel):
    pass


class TrainModelResponse(BaseModel):
    model_version: str
    selected_model: str
    training_cutoff: date
    feature_schema_version: str
    validation_context_mae: float
    validation_baseline_mae: float
    artifact_path: str
    caveat: str = "Model selection uses a chronological validation window; synthetic metrics only."


class PredictionListResponse(BaseModel):
    items: list[ForecastRow]
    total: int
    limit: int
    offset: int
