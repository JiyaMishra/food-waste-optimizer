from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, Field, model_validator


class IntervalDemand(BaseModel):
    interval_start: time
    expected: float = Field(ge=0)
    lower: float = Field(ge=0)
    upper: float = Field(ge=0)

    @model_validator(mode="after")
    def bounds_ordered(self):
        if not (self.lower <= self.expected <= self.upper):
            raise ValueError("interval demand requires lower <= expected <= upper")
        return self


class OptimizerWeights(BaseModel):
    leftover: float = Field(default=1.0, ge=0)
    shortage: float = Field(default=8.0, ge=0, description="Deliberately high to protect availability")
    prep_cost: float = Field(default=0.05, ge=0)
    batch_change: float = Field(default=0.5, ge=0)


class OptimizerRequest(BaseModel):
    service_date: date
    meal_type: str
    dish_external_id: str | None = None
    intervals: list[IntervalDemand] = Field(min_length=1)
    current_stock: float = Field(default=0, ge=0)
    batch_min: float = Field(gt=0)
    batch_max: float = Field(gt=0)
    kitchen_capacity: float = Field(ge=0)
    prep_lead_minutes: int = Field(default=30, ge=0)
    service_start: time
    service_close: time
    now: datetime | None = None
    weights: OptimizerWeights = Field(default_factory=OptimizerWeights)
    persist: bool = True
    run_id: str | None = None
    forecast_run_id: str | None = None
    model_version: str | None = None
    policy_version: str = "1.0.0"

    @model_validator(mode="after")
    def batch_bounds(self):
        if self.batch_max < self.batch_min:
            raise ValueError("batch_max must be >= batch_min")
        if not (self.service_start < self.service_close):
            raise ValueError("service_start must precede service_close")
        return self


class ConstraintCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class BatchPlanOut(BaseModel):
    plan_id: str | None = None
    service_date: date
    meal_type: str
    dish_external_id: str | None = None
    initial_quantity: float
    reserve_quantity: float
    replenishment_trigger: float
    batch_min: float
    batch_max: float
    capacity_total: float
    capacity_remaining: float
    lead_time_minutes: int
    service_close: time
    expected_leftover: float
    expected_shortage: float
    expected_prepared: float
    objective_value: float
    weights: dict[str, float]
    rationale: str
    constraint_checks: list[ConstraintCheck]
    uncertainty: dict[str, Any]
    approval_state: str = "proposed"
    requires_human_approval: bool = True
    simulation_only: bool = True
    policy_version: str
    model_version: str | None = None
    is_synthetic: bool = True
