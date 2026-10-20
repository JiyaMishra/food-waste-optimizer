"""SQLAlchemy models for operational runs, traces, plans and outcomes.

Every persisted operational record carries ``is_synthetic`` and provenance fields
(dataset/scenario/model/policy versions and seeds where applicable). Model
predictions are append-only rows grouped by ``forecast_run_id``; decisions are
stored as new run records rather than overwriting earlier runs.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Dish(TimestampMixin, Base):
    __tablename__ = "dishes"
    __table_args__ = (
        CheckConstraint("prep_lead_minutes >= 0", name="prep_lead_non_negative"),
        CheckConstraint("batch_min > 0", name="batch_min_positive"),
        CheckConstraint("batch_max >= batch_min", name="batch_bounds_valid"),
        CheckConstraint("kitchen_capacity_per_interval >= 0", name="capacity_non_negative"),
        CheckConstraint(
            "typical_portion_size IS NULL OR typical_portion_size > 0",
            name="portion_size_positive",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    external_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    category: Mapped[str | None] = mapped_column(String(60), nullable=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    vegetarian_flag: Mapped[bool] = mapped_column(Boolean, default=True)
    default_unit: Mapped[str] = mapped_column(String(20), default="portions")
    typical_portion_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    prep_lead_minutes: Mapped[int] = mapped_column(Integer, default=30)
    batch_min: Mapped[float] = mapped_column(Float, default=1)
    batch_max: Mapped[float] = mapped_column(Float, default=1000)
    kitchen_capacity_per_interval: Mapped[float] = mapped_column(Float, default=0)
    menu_source: Mapped[str | None] = mapped_column(String(60), nullable=True)
    source_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="dish")


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"
    __table_args__ = (
        UniqueConstraint("meal_id", "dish_id", name="uq_menu_items_meal_dish"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    dish_id: Mapped[str] = mapped_column(
        ForeignKey("dishes.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_id: Mapped[str] = mapped_column(String(32), index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    dish: Mapped[Dish] = relationship(back_populates="menu_items")


class SyntheticContext(TimestampMixin, Base):
    __tablename__ = "synthetic_context"
    __table_args__ = (
        UniqueConstraint(
            "date", "hostel_id", "mess_id", "scenario_id", name="uq_context_day_group_scenario"
        ),
        CheckConstraint("capacity >= 0", name="capacity_non_negative"),
        CheckConstraint("occupied_count >= 0", name="occupied_non_negative"),
        CheckConstraint("occupied_count <= capacity", name="occupied_within_capacity"),
        CheckConstraint("occupancy_rate >= 0 AND occupancy_rate <= 1", name="occupancy_rate_range"),
        CheckConstraint("rain_mm >= 0", name="rain_non_negative"),
        CheckConstraint(
            "event_expected_participants IS NULL OR event_expected_participants >= 0",
            name="event_participants_non_negative",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    date: Mapped[date] = mapped_column(Date, index=True)
    hostel_id: Mapped[str] = mapped_column(String(20), index=True)
    mess_id: Mapped[str] = mapped_column(String(20), index=True)
    capacity: Mapped[int] = mapped_column(Integer, default=0)
    occupied_count: Mapped[int] = mapped_column(Integer, default=0)
    occupancy_rate: Mapped[float] = mapped_column(Float, default=0)
    rain_mm: Mapped[float] = mapped_column(Float, default=0)
    temperature_c: Mapped[float] = mapped_column(Float, default=0)
    weather_label: Mapped[str] = mapped_column(String(30), default="normal")
    event_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    event_expected_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    dataset_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class AcademicSlot(TimestampMixin, Base):
    __tablename__ = "academic_slots"
    __table_args__ = (
        UniqueConstraint(
            "date", "cohort_id", "activity_type", "start_time", "end_time",
            name="uq_academic_slot_identity",
        ),
        CheckConstraint("start_time < end_time", name="slot_time_order"),
        CheckConstraint(
            "unavailable_share IS NULL OR (unavailable_share >= 0 AND unavailable_share <= 1)",
            name="unavailable_share_range",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    date: Mapped[date] = mapped_column(Date, index=True)
    cohort_id: Mapped[str] = mapped_column(String(40), index=True)
    activity_type: Mapped[str] = mapped_column(String(40))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    location_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    unavailable_share: Mapped[float | None] = mapped_column(Float, nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class AvailabilitySnapshot(TimestampMixin, Base):
    __tablename__ = "availability_snapshots"
    __table_args__ = (
        CheckConstraint("occupied_population >= 0", name="occupied_population_non_negative"),
        CheckConstraint("available_population >= 0", name="available_population_non_negative"),
        CheckConstraint("expected_arrivals >= 0", name="expected_arrivals_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hostel_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mess_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    context_json: Mapped[dict] = mapped_column(JSON, default=dict)
    slots_json: Mapped[list] = mapped_column(JSON, default=list)
    result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    occupied_population: Mapped[int] = mapped_column(Integer, default=0)
    unavailable_population: Mapped[int] = mapped_column(Integer, default=0)
    available_population: Mapped[int] = mapped_column(Integer, default=0)
    expected_arrivals: Mapped[int] = mapped_column(Integer, default=0)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class MealRun(Base):
    __tablename__ = "meal_runs"
    __table_args__ = (
        CheckConstraint("seed >= 0", name="seed_non_negative"),
        CheckConstraint("current_interval >= 0", name="current_interval_non_negative"),
        CheckConstraint("intervals_total > 0", name="intervals_total_positive"),
        CheckConstraint(
            "status IN ('created','running','finished','failed')", name="run_status_valid"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    dataset_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    seed: Mapped[int] = mapped_column(Integer, default=42)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    dish_external_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    policy_id: Mapped[str] = mapped_column(String(64), index=True)
    policy_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    forecast_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="created", index=True)
    current_interval: Mapped[int] = mapped_column(Integer, default=0)
    intervals_total: Mapped[int] = mapped_column(Integer, default=1)
    demand_realization: Mapped[list] = mapped_column(JSON, default=list)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)

    events: Mapped[list["SimulationEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    outcome: Mapped["Outcome | None"] = relationship(
        back_populates="run", uselist=False, cascade="all, delete-orphan"
    )
    interventions: Mapped[list["Intervention"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class SimulationEvent(Base):
    __tablename__ = "simulation_events"
    __table_args__ = (
        UniqueConstraint("run_id", "interval_index", name="uq_simulation_interval"),
        CheckConstraint("interval_index >= 0", name="event_interval_non_negative"),
        CheckConstraint("arrivals >= 0", name="arrivals_non_negative"),
        CheckConstraint("stock_before >= 0", name="stock_before_non_negative"),
        CheckConstraint("stock_after >= 0", name="stock_after_non_negative"),
        CheckConstraint("prepared_qty >= 0", name="prepared_non_negative"),
        CheckConstraint("served_qty >= 0", name="served_non_negative"),
        CheckConstraint("unmet_qty >= 0", name="unmet_non_negative"),
        CheckConstraint("served_qty <= arrivals", name="served_within_arrivals"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("meal_runs.id", ondelete="CASCADE"), index=True)
    interval_index: Mapped[int] = mapped_column(Integer)
    interval_start: Mapped[time] = mapped_column(Time)
    arrivals: Mapped[float] = mapped_column(Float, default=0)
    stock_before: Mapped[float] = mapped_column(Float, default=0)
    stock_after: Mapped[float] = mapped_column(Float, default=0)
    prepared_qty: Mapped[float] = mapped_column(Float, default=0)
    served_qty: Mapped[float] = mapped_column(Float, default=0)
    unmet_qty: Mapped[float] = mapped_column(Float, default=0)
    projected_demand: Mapped[float] = mapped_column(Float, default=0)
    action: Mapped[str] = mapped_column(String(40), default="none")
    action_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[MealRun] = relationship(back_populates="events")


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        CheckConstraint("prepared_total >= 0", name="prepared_total_non_negative"),
        CheckConstraint("served_total >= 0", name="served_total_non_negative"),
        CheckConstraint("consumed_total >= 0", name="consumed_total_non_negative"),
        CheckConstraint("untouched_leftover >= 0", name="leftover_non_negative"),
        CheckConstraint("plate_waste >= 0", name="plate_waste_non_negative"),
        CheckConstraint("shortage >= 0", name="shortage_non_negative"),
        CheckConstraint("consumed_total <= served_total", name="consumed_within_served"),
        CheckConstraint("served_total <= prepared_total", name="served_within_prepared"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="CASCADE"), unique=True, index=True
    )
    prepared_total: Mapped[float] = mapped_column(Float, default=0)
    served_total: Mapped[float] = mapped_column(Float, default=0)
    consumed_total: Mapped[float] = mapped_column(Float, default=0)
    untouched_leftover: Mapped[float] = mapped_column(Float, default=0)
    plate_waste: Mapped[float] = mapped_column(Float, default=0)
    shortage: Mapped[float] = mapped_column(Float, default=0)
    excess_preparation: Mapped[float] = mapped_column(Float, default=0)
    forecast_error_abs: Mapped[float | None] = mapped_column(Float, nullable=True)
    forecast_error_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[MealRun] = relationship(back_populates="outcome")


class Prediction(TimestampMixin, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        CheckConstraint("prediction >= 0", name="prediction_non_negative"),
        CheckConstraint("lower_bound >= 0", name="lower_bound_non_negative"),
        CheckConstraint("upper_bound >= lower_bound", name="upper_bound_valid"),
        CheckConstraint(
            "prediction >= lower_bound AND prediction <= upper_bound",
            name="prediction_within_bounds",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    forecast_run_id: Mapped[str] = mapped_column(String(36), index=True)
    forecast_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    dish_external_id: Mapped[str] = mapped_column(String(32), index=True)
    prediction: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(64))
    selected_model: Mapped[str] = mapped_column(String(64))
    forecast_cutoff: Mapped[date] = mapped_column(Date)
    feature_schema_version: Mapped[str] = mapped_column(String(20))
    interval_method: Mapped[str] = mapped_column(String(160))
    interval_is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    unit: Mapped[str] = mapped_column(String(20), default="portions")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class BatchPlan(TimestampMixin, Base):
    __tablename__ = "batch_plans"
    __table_args__ = (
        CheckConstraint("initial_qty >= 0", name="initial_non_negative"),
        CheckConstraint("reserve_qty >= 0", name="reserve_non_negative"),
        CheckConstraint("trigger_qty >= 0", name="trigger_non_negative"),
        CheckConstraint("batch_min > 0", name="plan_batch_min_positive"),
        CheckConstraint("batch_max >= batch_min", name="plan_batch_bounds_valid"),
        CheckConstraint(
            "initial_qty = 0 OR (initial_qty >= batch_min AND initial_qty <= batch_max)",
            name="initial_batch_bounds",
        ),
        CheckConstraint(
            "reserve_qty = 0 OR (reserve_qty >= batch_min AND reserve_qty <= batch_max)",
            name="reserve_batch_bounds",
        ),
        CheckConstraint(
            "initial_qty + reserve_qty <= capacity_total", name="capacity_respected"
        ),
        CheckConstraint("lead_time_minutes >= 0", name="plan_lead_time_non_negative"),
        CheckConstraint(
            "approval_state IN ('proposed','approved','rejected')", name="approval_state_valid"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    forecast_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    service_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    dish_external_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    initial_qty: Mapped[float] = mapped_column(Float, default=0)
    reserve_qty: Mapped[float] = mapped_column(Float, default=0)
    trigger_qty: Mapped[float] = mapped_column(Float, default=0)
    batch_min: Mapped[float] = mapped_column(Float, default=1)
    batch_max: Mapped[float] = mapped_column(Float, default=1000)
    capacity_total: Mapped[float] = mapped_column(Float, default=0)
    capacity_remaining: Mapped[float] = mapped_column(Float, default=0)
    lead_time_minutes: Mapped[int] = mapped_column(Integer, default=0)
    service_close: Mapped[time] = mapped_column(Time)
    expected_leftover: Mapped[float] = mapped_column(Float, default=0)
    expected_shortage: Mapped[float] = mapped_column(Float, default=0)
    expected_prepared: Mapped[float] = mapped_column(Float, default=0)
    objective_value: Mapped[float] = mapped_column(Float, default=0)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    capacity_check: Mapped[dict] = mapped_column(JSON, default=dict)
    uncertainty: Mapped[dict] = mapped_column(JSON, default=dict)
    approval_state: Mapped[str] = mapped_column(String(20), default="proposed")
    policy_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class AgentTrace(Base):
    __tablename__ = "agent_traces"
    __table_args__ = (
        CheckConstraint(
            "status IN ('started','completed','failed','rejected')", name="trace_status_valid"
        ),
        CheckConstraint("duration_ms >= 0", name="trace_duration_non_negative"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    stage: Mapped[str] = mapped_column(String(60), index=True)
    agent_name: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    input_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    tool_calls: Mapped[list] = mapped_column(JSON, default=list)
    duration_ms: Mapped[float] = mapped_column(Float, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Diagnosis(TimestampMixin, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        CheckConstraint("diagnosis_type IN ('pre_meal','post_meal')", name="diagnosis_type_valid"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="risk_score_range"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    diagnosis_type: Mapped[str] = mapped_column(String(20), index=True)
    target_date: Mapped[date] = mapped_column(Date, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), index=True)
    dish_external_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    risk_score: Mapped[float] = mapped_column(Float, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    causes: Mapped[list] = mapped_column(JSON, default=list)
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    caveats: Mapped[list] = mapped_column(JSON, default=list)
    data_sources: Mapped[list] = mapped_column(JSON, default=list)
    llm_used: Mapped[bool] = mapped_column(Boolean, default=False)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('proposed','approved','rejected','scheduled','simulated','cancelled')",
            name="intervention_status_valid",
        ),
        CheckConstraint("requested_qty >= 0", name="requested_qty_non_negative"),
        CheckConstraint(
            "approved_qty IS NULL OR approved_qty >= 0", name="approved_qty_non_negative"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("meal_runs.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("simulation_events.id", ondelete="SET NULL"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(60))
    requested_qty: Mapped[float] = mapped_column(Float, default=0)
    approved_qty: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    approval_required: Mapped[bool] = mapped_column(Boolean, default=True)
    reason: Mapped[str] = mapped_column(Text, default="")
    detail_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    run: Mapped[MealRun] = relationship(back_populates="interventions")


class EvaluationRun(TimestampMixin, Base):
    __tablename__ = "evaluation_runs"
    __table_args__ = (CheckConstraint("seed >= 0", name="evaluation_seed_non_negative"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="CASCADE"), index=True
    )
    policy_id: Mapped[str] = mapped_column(String(64))
    scenario_id: Mapped[str] = mapped_column(String(64), index=True)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    denominators: Mapped[dict] = mapped_column(JSON, default=dict)
    model_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    policy_version: Mapped[str] = mapped_column(String(20), default="1.0.0")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)


class FeedbackEvent(TimestampMixin, Base):
    __tablename__ = "feedback_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("meal_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    candidate_retraining: Mapped[dict] = mapped_column(JSON, default=dict)
