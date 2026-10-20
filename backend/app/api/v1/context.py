from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.core.config import get_settings
from backend.app.db.models import AcademicSlot
from backend.app.schemas.context import (
    AvailabilityOut,
    AvailabilityRequest,
    AvailabilitySnapshotOut,
    ContextOut,
    SnapshotListResponse,
    TimetableSlotOut,
)
from backend.app.services.availability import (
    calculate_availability_snapshot,
    get_context,
    list_snapshots,
)

router = APIRouter(prefix="/context", tags=["context and availability"])


@router.get("", response_model=ContextOut)
def read_context(
    day: date = Query(..., alias="date"),
    hostel_id: str | None = None,
    mess_id: str | None = None,
    db: Session = Depends(get_db),
) -> ContextOut:
    context = get_context(db, day, hostel_id, mess_id)
    return ContextOut(**context)


@router.get("/timetable", response_model=list[TimetableSlotOut])
def read_timetable(
    day: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
) -> list[TimetableSlotOut]:
    rows = list(
        db.scalars(
            select(AcademicSlot)
            .where(AcademicSlot.date == day)
            .order_by(AcademicSlot.start_time, AcademicSlot.cohort_id)
        ).all()
    )
    return [
        TimetableSlotOut(
            date=row.date,
            cohort_id=row.cohort_id,
            activity_type=row.activity_type,
            start_time=row.start_time,
            end_time=row.end_time,
            location_id=row.location_id,
            unavailable_share=row.unavailable_share,
            scenario_id=row.scenario_id,
        )
        for row in rows
    ]


@router.post("/availability", response_model=AvailabilityOut)
def calculate_availability(
    payload: AvailabilityRequest,
    db: Session = Depends(get_db),
) -> AvailabilityOut:
    return AvailabilityOut(**calculate_availability_snapshot(db, payload))


@router.get("/availability/snapshots", response_model=SnapshotListResponse)
def read_availability_snapshots(
    day: date | None = Query(default=None, alias="date"),
    meal_type: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> SnapshotListResponse:
    limit, offset = page
    rows, total = list_snapshots(db, day, meal_type, limit, offset)
    return SnapshotListResponse(
        items=[AvailabilitySnapshotOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/settings", include_in_schema=False)
def read_context_settings() -> dict:
    settings = get_settings()
    return {
        "attendance_probability_default": settings.attendance_probability,
        "caveat": "Synthetic context only; no live VIT attendance or weather source is connected.",
    }
