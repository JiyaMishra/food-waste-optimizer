from __future__ import annotations

from datetime import date, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContextQuery(BaseModel):
    date: date
    hostel_id: str | None = None
    mess_id: str | None = None


class ContextOut(BaseModel):
    date: date
    hostel_id: str | None = None
    mess_id: str | None = None
    capacity: int
    occupied_count: int
    occupancy_rate: float
    rain_mm: float
    temperature_c: float
    weather_label: str
    event_id: str | None = None
    event_expected_participants: int | None = None
    scenario_id: str
    dataset_version: str
    is_synthetic: bool
    source: str = "synthetic_context"
    context_date: date | None = None
    caveats: list[str] = Field(default_factory=list)


class AcademicSlotInput(BaseModel):
    group_id: str
    unavailable_share: float = Field(ge=0, le=1)


class AvailabilityRequest(BaseModel):
    date: date
    meal_type: str | None = None
    hostel_id: str | None = None
    mess_id: str | None = None
    occupied_population: int | None = Field(
        default=None, ge=0, description="Optional override; otherwise derived from stored context"
    )
    attendance_probability: float = Field(default=0.65, ge=0, le=1)
    event_unavailable: int = Field(default=0, ge=0)
    returning_population: int = Field(default=0, ge=0)
    academic_slots: list[AcademicSlotInput] = Field(default_factory=list)
    group_sizes: dict[str, int] = Field(default_factory=dict)
    scenario_id: str = "synthetic_baseline_v1"
    persist: bool = True


class AvailabilityOut(BaseModel):
    date: date
    meal_type: str | None = None
    occupied_population: int
    unavailable_population: int
    available_population: int
    expected_arrivals: int
    context: dict[str, Any]
    caveats: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None
    is_synthetic: bool = True


class AvailabilitySnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    date: date
    meal_type: str | None = None
    hostel_id: str | None = None
    mess_id: str | None = None
    scenario_id: str
    occupied_population: int
    unavailable_population: int
    available_population: int
    expected_arrivals: int
    created_at: Any


class SnapshotListResponse(BaseModel):
    items: list[AvailabilitySnapshotOut]
    total: int
    limit: int
    offset: int


class TimetableSlotOut(BaseModel):
    date: date
    cohort_id: str
    activity_type: str
    start_time: time
    end_time: time
    location_id: str | None = None
    unavailable_share: float | None = None
    scenario_id: str
