"""Context observation agent: deterministic database joins, no LLM."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.contracts import ContextObservation
from backend.app.db.models import SyntheticContext
from backend.app.services.availability import get_context


def run(db: Session, day: date, hostel_id: str | None = None, mess_id: str | None = None) -> dict:
    context = get_context(db, day, hostel_id, mess_id)
    context_date = context.get("context_date", day)
    stmt = select(SyntheticContext).where(
        SyntheticContext.date >= context_date - timedelta(days=7),
        SyntheticContext.date < context_date,
    )
    if hostel_id:
        stmt = stmt.where(SyntheticContext.hostel_id == hostel_id)
    if mess_id:
        stmt = stmt.where(SyntheticContext.mess_id == mess_id)
    history = list(db.scalars(stmt).all())
    baseline = None
    if history:
        daily: dict[date, list[SyntheticContext]] = {}
        for row in history:
            daily.setdefault(row.date, []).append(row)
        rates = []
        for rows in daily.values():
            capacity = sum(item.capacity for item in rows)
            if capacity:
                rates.append(sum(item.occupied_count for item in rows) / capacity)
        if rates:
            baseline = sum(rates) / len(rates)
    delta = (
        round(context["occupancy_rate"] - baseline, 4) if baseline is not None else None
    )
    observation = ContextObservation(
        date=day,
        hostel_id=hostel_id,
        mess_id=mess_id,
        capacity=context["capacity"],
        occupied_count=context["occupied_count"],
        occupancy_rate=context["occupancy_rate"],
        rain_mm=context["rain_mm"],
        temperature_c=context["temperature_c"],
        weather_label=context["weather_label"],
        event_id=context["event_id"],
        event_expected_participants=context["event_expected_participants"],
        occupancy_delta_vs_7d=delta,
        data_sources=["synthetic_context", "hostel_daily_state", "weather_daily"],
    )
    return observation.model_dump(mode="json")
