from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.db.models import Prediction
from backend.app.schemas.forecast import (
    ForecastRequest,
    ForecastResponse,
    ForecastRow,
    PredictionListResponse,
    TrainModelResponse,
)
from backend.app.services.forecasting import (
    forecast_demand,
    list_predictions,
    train_from_generated_data,
)

router = APIRouter(prefix="/forecasts", tags=["forecasting"])


def _prediction_row(row: Prediction) -> ForecastRow:
    return ForecastRow(
        date=row.forecast_date,
        meal_type=row.meal_type,
        dish_id=row.dish_external_id,
        prediction=row.prediction,
        lower_bound=row.lower_bound,
        upper_bound=row.upper_bound,
        model_version=row.model_version,
        selected_model=row.selected_model,
        forecast_cutoff=row.forecast_cutoff,
        feature_schema_version=row.feature_schema_version,
        interval_method=row.interval_method,
        interval_is_calibrated=row.interval_is_calibrated,
        unit=row.unit,
        is_synthetic=row.is_synthetic,
    )


@router.post("", response_model=ForecastResponse)
def create_forecast(payload: ForecastRequest, db: Session = Depends(get_db)) -> ForecastResponse:
    result = forecast_demand(db, payload.date, payload.meal_type, persist=payload.persist)
    return ForecastResponse(**result)


@router.post("/model/train", response_model=TrainModelResponse)
def train_forecast_model() -> TrainModelResponse:
    return TrainModelResponse(**train_from_generated_data())


@router.get("/predictions", response_model=PredictionListResponse)
def read_predictions(
    forecast_run_id: str | None = None,
    day: date | None = Query(default=None, alias="date"),
    meal_type: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> PredictionListResponse:
    limit, offset = page
    rows, total = list_predictions(
        db, forecast_run_id, day, meal_type, limit=limit, offset=offset
    )
    return PredictionListResponse(
        items=[_prediction_row(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/runs/{forecast_run_id}", response_model=PredictionListResponse)
def read_forecast_run(
    forecast_run_id: str,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> PredictionListResponse:
    limit, offset = page
    rows, total = list_predictions(
        db, forecast_run_id=forecast_run_id, limit=limit, offset=offset
    )
    return PredictionListResponse(
        items=[_prediction_row(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
