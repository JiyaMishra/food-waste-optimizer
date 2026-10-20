"""Integration with Person A ``calculate_availability`` and context persistence."""
from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.errors import DomainError
from backend.app.db.models import AvailabilitySnapshot, SyntheticContext
from backend.app.schemas.context import AvailabilityRequest
from src.availability.availability import calculate_availability


def get_context(
    db: Session, day: date, hostel_id: str | None = None, mess_id: str | None = None
) -> dict:
    stmt = select(SyntheticContext).where(SyntheticContext.date == day)
    if hostel_id:
        stmt = stmt.where(SyntheticContext.hostel_id == hostel_id)
    if mess_id:
        stmt = stmt.where(SyntheticContext.mess_id == mess_id)
    rows = list(db.scalars(stmt).all())
    caveats: list[str] = []
    source = "synthetic_context"
    context_date = day
    if not rows:
        latest = db.scalar(
            select(func.max(SyntheticContext.date)).where(SyntheticContext.date <= day)
        )
        if latest is not None:
            fallback = select(SyntheticContext).where(SyntheticContext.date == latest)
            if hostel_id:
                fallback = fallback.where(SyntheticContext.hostel_id == hostel_id)
            if mess_id:
                fallback = fallback.where(SyntheticContext.mess_id == mess_id)
            rows = list(db.scalars(fallback).all())
            if rows:
                context_date = latest
                source = "latest_available_context_proxy"
                caveats.append(
                    f"No synthetic context exists for {day.isoformat()}; using the latest "
                    f"available context date {latest.isoformat()} as a proxy."
                )
    if not rows:
        raise DomainError(
            "CONTEXT_NOT_FOUND",
            f"No synthetic context found for {day.isoformat()}",
            404,
            {
                "date": day.isoformat(),
                "hostel_id": hostel_id,
                "mess_id": mess_id,
                "hint": "POST /api/v1/data/generate then POST /api/v1/data/sync",
            },
        )
    capacity = int(sum(row.capacity for row in rows))
    occupied = int(sum(row.occupied_count for row in rows))
    event_row = next((row for row in rows if row.event_expected_participants is not None), None)
    return {
        "date": day,
        "context_date": context_date,
        "hostel_id": hostel_id,
        "mess_id": mess_id,
        "capacity": capacity,
        "occupied_count": occupied,
        "occupancy_rate": round(occupied / capacity, 4) if capacity else 0.0,
        "rain_mm": float(max(row.rain_mm for row in rows)),
        "temperature_c": round(float(sum(row.temperature_c for row in rows) / len(rows)), 2),
        "weather_label": rows[0].weather_label,
        "event_id": event_row.event_id if event_row else None,
        "event_expected_participants": (
            event_row.event_expected_participants if event_row else None
        ),
        "scenario_id": rows[0].scenario_id,
        "dataset_version": rows[0].dataset_version,
        "is_synthetic": all(row.is_synthetic for row in rows),
        "source": source,
        "caveats": caveats,
        "row_count": len(rows),
    }


def calculate_availability_snapshot(db: Session, request: AvailabilityRequest) -> dict:
    settings = get_settings()
    context_row = get_context(db, request.date, request.hostel_id, request.mess_id)

    academic_slots = None
    groups = None
    if request.academic_slots:
        academic_slots = pd.DataFrame(
            [
                {"group_id": slot.group_id, "unavailable_share": slot.unavailable_share}
                for slot in request.academic_slots
            ]
        )
        groups = {"group_sizes": request.group_sizes}

    context_payload = {
        "occupied_population": (
            request.occupied_population
            if request.occupied_population is not None
            else context_row["occupied_count"]
        ),
        "event_unavailable": request.event_unavailable,
        "returning_population": request.returning_population,
        "attendance_probability": request.attendance_probability,
    }
    try:
        result = calculate_availability(context_payload, academic_slots, groups)
    except (ValueError, TypeError) as exc:
        raise DomainError("AVAILABILITY_INPUT_INVALID", str(exc), 422) from exc

    caveats = list(context_row.get("caveats", [])) + [
        "Availability is estimated from synthetic occupancy/context, not live VIT attendance.",
        "Event and academic unavailability may overlap; Person A uses a conservative union estimate.",
    ]
    if not request.academic_slots:
        caveats.append(
            "Person A's generated timetable does not declare per-group unavailable_share; "
            "academic unavailability is not applied unless explicit slots are supplied."
        )
    if request.event_unavailable == 0 and context_row.get("event_expected_participants"):
        caveats.append(
            "A campus event exists on this date, but its participants are not assumed unavailable "
            "without an explicit event_unavailable value."
        )

    snapshot_id = None
    if request.persist:
        snapshot = AvailabilitySnapshot(
            date=request.date,
            meal_type=request.meal_type,
            hostel_id=request.hostel_id,
            mess_id=request.mess_id,
            scenario_id=request.scenario_id,
            context_json={k: str(v) if isinstance(v, date) else v for k, v in context_row.items()},
            slots_json=[slot.model_dump() for slot in request.academic_slots],
            result_json=result,
            occupied_population=result["occupied_population"],
            unavailable_population=result["unavailable_population"],
            available_population=result["available_population"],
            expected_arrivals=result["expected_arrivals"],
            is_synthetic=True,
        )
        db.add(snapshot)
        db.flush()
        snapshot_id = snapshot.id

    return {
        "date": request.date,
        "meal_type": request.meal_type,
        "occupied_population": result["occupied_population"],
        "unavailable_population": result["unavailable_population"],
        "available_population": result["available_population"],
        "expected_arrivals": result["expected_arrivals"],
        "context": context_row,
        "caveats": caveats,
        "data_sources": [
            "synthetic_context.hostel_daily_state",
            "synthetic_context.academic_slots (explicit shares only)",
            "src.availability.availability.calculate_availability",
        ],
        "snapshot_id": snapshot_id,
        "is_synthetic": True,
    }


def list_snapshots(
    db: Session,
    day: date | None = None,
    meal_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AvailabilitySnapshot], int]:
    stmt = select(AvailabilitySnapshot)
    count_stmt = select(func.count()).select_from(AvailabilitySnapshot)
    if day:
        stmt = stmt.where(AvailabilitySnapshot.date == day)
        count_stmt = count_stmt.where(AvailabilitySnapshot.date == day)
    if meal_type:
        stmt = stmt.where(AvailabilitySnapshot.meal_type == meal_type)
        count_stmt = count_stmt.where(AvailabilitySnapshot.meal_type == meal_type)
    total = int(db.scalar(count_stmt) or 0)
    items = list(
        db.scalars(
            stmt.order_by(AvailabilitySnapshot.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return items, total
