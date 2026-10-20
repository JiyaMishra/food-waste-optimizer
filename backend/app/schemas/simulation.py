from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

PolicyId = Literal["baseline_fixed", "context_aware_split"]


class PlanSpec(BaseModel):
    initial_qty: float = Field(ge=0)
    reserve_qty: float = Field(default=0, ge=0)
    trigger_qty: float = Field(default=0, ge=0)


class IntervalArrival(BaseModel):
    interval_start: time
    arrivals: float = Field(ge=0)


class SimulationBase(BaseModel):
    scenario_id: str = "synthetic_baseline_v1"
    dataset_version: str = "1.0.0"
    service_date: date
    meal_type: str
    dish_external_id: str = "D001"
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    service_start: time = time(7, 0)
    service_close: time | None = None
    intervals: list[IntervalArrival] | None = None
    use_historical: bool = False
    historical_date: date | None = None
    current_stock: float = Field(default=0, ge=0)
    capacity: float = Field(default=500, ge=0)
    batch_min: float = Field(default=20, gt=0)
    batch_max: float = Field(default=500, gt=0)
    consumption_rate: float = Field(default=0.85, ge=0, le=1)
    prep_lead_intervals: int = Field(default=1, ge=0, le=8)
    forecast_expected: float | None = Field(default=None, ge=0)
    forecast_run_id: str | None = None
    model_version: str | None = None
    plan: PlanSpec | None = None
    persist: bool = True

    @model_validator(mode="after")
    def validate_simulation(self):
        if self.batch_max < self.batch_min:
            raise ValueError("batch_max must be >= batch_min")
        if self.intervals is not None and len(self.intervals) < 2:
            raise ValueError("at least two service intervals are required")
        return self


class SimulationStartRequest(SimulationBase):
    policy: PolicyId


class SimulationCompareRequest(SimulationBase):
    pass


class OutcomeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    prepared_total: float
    served_total: float
    consumed_total: float
    untouched_leftover: float
    plate_waste: float
    shortage: float
    excess_preparation: float
    forecast_error_abs: float | None = None
    forecast_error_pct: float | None = None


class SimulationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    interval_index: int
    interval_start: time
    arrivals: float
    stock_before: float
    stock_after: float
    prepared_qty: float
    served_qty: float
    unmet_qty: float
    projected_demand: float
    action: str
    action_reason: str | None = None


class InterventionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action_type: str
    requested_qty: float
    approved_qty: float | None = None
    status: str
    approval_required: bool
    reason: str
    detail_json: dict = Field(default_factory=dict)


class SimulationRunOut(BaseModel):
    id: str
    status: str
    scenario_id: str
    dataset_version: str
    seed: int
    service_date: date
    meal_type: str
    dish_external_id: str | None = None
    policy_id: str
    policy_version: str
    model_version: str | None = None
    forecast_run_id: str | None = None
    current_interval: int
    intervals_total: int
    is_synthetic: bool
    created_at: datetime
    config: dict[str, Any] = Field(default_factory=dict)


class SimulationRunListResponse(BaseModel):
    items: list[SimulationRunOut]
    total: int
    limit: int
    offset: int


class StepResponse(BaseModel):
    run: SimulationRunOut
    event: SimulationEventOut | None = None
    interventions: list[InterventionOut] = Field(default_factory=list)
    finished: bool = False
    message: str


class FinishResponse(BaseModel):
    run: SimulationRunOut
    outcome: OutcomeOut
    events: list[SimulationEventOut]
    interventions: list[InterventionOut]
    message: str


class CompareResponse(BaseModel):
    baseline_run: FinishResponse
    context_run: FinishResponse
    same_demand_realization: bool
    seed: int
    demand_realization: list[float]
    caveat: str = "Simulated comparison on one synthetic realization; not a real cafeteria outcome."
