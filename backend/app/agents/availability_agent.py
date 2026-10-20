"""Availability agent wrapping Person A's conservative availability calculator."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.agents.contracts import AvailabilityObservation
from backend.app.schemas.context import AvailabilityRequest
from backend.app.services.availability import calculate_availability_snapshot


def run(db: Session, request: AvailabilityRequest) -> dict:
    result = calculate_availability_snapshot(db, request)
    observation = AvailabilityObservation(
        occupied_population=result["occupied_population"],
        unavailable_population=result["unavailable_population"],
        available_population=result["available_population"],
        expected_arrivals=result["expected_arrivals"],
        caveats=result["caveats"],
        snapshot_id=result["snapshot_id"],
    )
    return observation.model_dump(mode="json")
