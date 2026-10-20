"""Typed inputs/outputs and shared trace execution for specialized agents."""
from __future__ import annotations

import time
from datetime import date
from typing import Any, Callable, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy.orm import Session

from backend.app.core.errors import DomainError
from backend.app.db.models import AgentTrace

T = TypeVar("T", bound=BaseModel)


class ContextObservation(BaseModel):
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
    occupancy_delta_vs_7d: float | None = None
    data_sources: list[str] = Field(default_factory=list)


class AvailabilityObservation(BaseModel):
    occupied_population: int
    unavailable_population: int
    available_population: int
    expected_arrivals: int
    caveats: list[str] = Field(default_factory=list)
    snapshot_id: str | None = None


class DemandObservation(BaseModel):
    forecast_run_id: str
    forecast_date: date
    meal_type: str | None = None
    total_expected: float
    total_lower: float
    total_upper: float
    model_version: str
    forecast_cutoff: date
    rows: list[dict[str, Any]]


class PlanObservation(BaseModel):
    model_config = ConfigDict(extra="allow")

    initial_quantity: float = Field(ge=0)
    reserve_quantity: float = Field(ge=0)
    replenishment_trigger: float = Field(ge=0)
    batch_min: float = Field(gt=0)
    batch_max: float = Field(gt=0)
    capacity_total: float = Field(ge=0)
    capacity_remaining: float = Field(ge=0)
    expected_leftover: float = Field(ge=0)
    expected_shortage: float = Field(ge=0)
    objective_value: float
    constraint_checks: list[dict[str, Any]]
    approval_state: str = "proposed"
    requires_human_approval: bool = True
    simulation_only: bool = True
    plan_id: str | None = None
    rationale: str = ""

    @model_validator(mode="after")
    def constraints(self):
        if self.batch_max < self.batch_min:
            raise ValueError("batch_max must be >= batch_min")
        if self.initial_quantity + self.reserve_quantity > self.capacity_total:
            raise ValueError("initial + reserve exceeds kitchen capacity")
        if self.reserve_quantity > 0 and not (
            self.batch_min <= self.reserve_quantity <= self.batch_max
        ):
            raise ValueError("reserve is outside declared batch bounds")
        if self.initial_quantity > 0 and not (
            self.batch_min <= self.initial_quantity <= self.batch_max
        ):
            raise ValueError("initial quantity is outside declared batch bounds")
        return self


class DiagnosisObservation(BaseModel):
    diagnoses: list[dict[str, Any]]
    diagnosis_ids: list[str] = Field(default_factory=list)
    llm_used: bool = False


class LearningObservation(BaseModel):
    evaluation_id: str | None = None
    metrics: dict[str, Any]
    model_metrics: dict[str, Any] | None = None
    candidate_retraining: dict[str, Any]


def execute_stage(
    db: Session,
    trace_id: str,
    stage: str,
    agent_name: str,
    input_summary: dict,
    callable_fn: Callable[[], Any],
    output_model: type[T],
    run_id: str | None = None,
) -> T:
    """Run one agent stage, validate its output, and persist a complete trace."""
    started = time.perf_counter()
    status = "completed"
    error: str | None = None
    output_summary: dict = {}
    try:
        raw = callable_fn()
        validated = output_model.model_validate(raw)
        output_summary = validated.model_dump(mode="json")
        return validated
    except ValidationError as exc:
        status = "rejected"
        error = str(exc)
        raise DomainError(
            "AGENT_OUTPUT_REJECTED",
            f"{agent_name} produced output that violates the typed contract",
            422,
            {
                "stage": stage,
                "agent": agent_name,
                "violations": [
                    {
                        "type": item.get("type"),
                        "loc": [str(part) for part in item.get("loc", [])],
                        "msg": item.get("msg"),
                    }
                    for item in exc.errors()
                ],
            },
        ) from exc
    except DomainError as exc:
        status = "failed"
        error = exc.message
        raise
    except Exception as exc:
        status = "failed"
        error = str(exc)
        raise DomainError(
            "AGENT_STAGE_FAILED",
            f"{agent_name} failed: {exc}",
            500,
            {"stage": stage, "agent": agent_name},
        ) from exc
    finally:
        duration_ms = round((time.perf_counter() - started) * 1000, 3)
        db.add(
            AgentTrace(
                trace_id=trace_id,
                run_id=run_id,
                stage=stage,
                agent_name=agent_name,
                status=status,
                input_summary=input_summary,
                output_summary=output_summary,
                tool_calls=[{"tool": agent_name, "stage": stage}],
                duration_ms=duration_ms,
                error=error,
            )
        )
        db.flush()
        if status != "completed":
            # Failed/rejected stages must remain inspectable even though the API
            # transaction will be rolled back after the exception is raised.
            db.commit()
