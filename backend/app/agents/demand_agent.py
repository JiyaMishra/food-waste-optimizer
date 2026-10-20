"""Demand agent wrapping Person A's model artifact and forecasting contract."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.app.agents.contracts import DemandObservation
from backend.app.services.forecasting import forecast_demand


def run(
    db: Session,
    forecast_date: date,
    meal_type: str | None,
    persist: bool = True,
) -> dict:
    result = forecast_demand(db, forecast_date, meal_type, persist=persist)
    rows = result["rows"]
    observation = DemandObservation(
        forecast_run_id=result["forecast_run_id"],
        forecast_date=forecast_date,
        meal_type=meal_type,
        total_expected=round(sum(row["prediction"] for row in rows), 3),
        total_lower=round(sum(row["lower_bound"] for row in rows), 3),
        total_upper=round(sum(row["upper_bound"] for row in rows), 3),
        model_version=result["model_version"],
        forecast_cutoff=result["forecast_cutoff"],
        rows=rows,
    )
    return observation.model_dump(mode="json")
