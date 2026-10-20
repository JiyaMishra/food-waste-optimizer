from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class ForecastInput(BaseModel):
    dish_id: str
    prediction: float = Field(ge=0)
    lower_bound: float = Field(ge=0)
    upper_bound: float = Field(ge=0)


class PlannedQuantity(BaseModel):
    dish_id: str
    prepared_qty: float = Field(ge=0)


class PreMealDiagnosisRequest(BaseModel):
    service_date: date
    meal_type: str
    forecast_run_id: str | None = None
    forecasts: list[ForecastInput] = Field(default_factory=list)
    planned_quantities: list[PlannedQuantity] = Field(default_factory=list)
    historical_waste_rate: float | None = Field(default=None, ge=0, le=1)
    context_notes: dict = Field(default_factory=dict)
    persist: bool = True


class PostMealDiagnosisRequest(BaseModel):
    run_id: str
    recent_menu_counts: dict[str, int] = Field(default_factory=dict)
    context_baseline: dict = Field(default_factory=dict)
    persist: bool = True


class EvidenceOut(BaseModel):
    field: str
    value: float | int | str | None = None
    comparison: str | None = None
    source: str


class CauseOut(BaseModel):
    code: str
    title: str
    confidence: float = Field(ge=0, le=1)
    evidence: list[EvidenceOut]
    explanation: str


class DiagnosisOut(BaseModel):
    id: str | None = None
    diagnosis_type: Literal["pre_meal", "post_meal"]
    target_date: date
    meal_type: str
    dish_external_id: str | None = None
    risk_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    causes: list[CauseOut] = Field(default_factory=list)
    evidence: list[EvidenceOut] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    llm_used: bool = False
    is_synthetic: bool = True


class DiagnosisListResponse(BaseModel):
    items: list[DiagnosisOut]
    total: int
    limit: int
    offset: int
