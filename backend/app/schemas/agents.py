from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlanningWorkflowRequest(BaseModel):
    service_date: date
    meal_type: str
    hostel_id: str | None = None
    mess_id: str | None = None
    attendance_probability: float = Field(default=0.65, ge=0, le=1)
    current_stock: float = Field(default=0, ge=0)
    batch_min: float = Field(default=20, gt=0)
    batch_max: float = Field(default=500, gt=0)
    kitchen_capacity: float = Field(default=500, ge=0)
    prep_lead_minutes: int = Field(default=30, ge=0)
    service_start: time = time(7, 0)
    service_close: time = time(10, 0)
    model_version: str | None = None
    persist: bool = True


class ReviewWorkflowRequest(BaseModel):
    run_id: str
    persist: bool = True


class AgentStageOut(BaseModel):
    stage: str
    agent_name: str
    status: str
    duration_ms: float
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class PlanningWorkflowResponse(BaseModel):
    trace_id: str
    status: str
    stages: list[AgentStageOut]
    forecast_run_id: str | None = None
    plan_id: str | None = None
    diagnosis_id: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = True


class ReviewWorkflowResponse(BaseModel):
    trace_id: str
    run_id: str
    status: str
    stages: list[AgentStageOut]
    evaluation_id: str | None = None
    diagnosis_id: str | None = None
    outputs: dict[str, Any] = Field(default_factory=dict)


class TraceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trace_id: str
    run_id: str | None = None
    stage: str
    agent_name: str
    status: str
    input_summary: dict = Field(default_factory=dict)
    output_summary: dict = Field(default_factory=dict)
    tool_calls: list = Field(default_factory=list)
    duration_ms: float
    error: str | None = None
    created_at: datetime


class TraceListResponse(BaseModel):
    items: list[TraceOut]
    total: int
    limit: int
    offset: int
