from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationOut(BaseModel):
    id: str
    run_id: str
    policy_id: str
    scenario_id: str
    seed: int
    policy_version: str
    model_version: str | None = None
    metrics: dict[str, Any]
    denominators: dict[str, Any]
    model_metrics: dict[str, Any] | None = None
    is_synthetic: bool
    created_at: datetime


class EvaluationCompareRequest(BaseModel):
    baseline_run_id: str
    context_run_id: str
    persist: bool = True


class EvaluationCompareResponse(BaseModel):
    baseline: EvaluationOut
    context: EvaluationOut
    deltas: dict[str, float | None]
    caveats: list[str] = Field(default_factory=list)


class FeedbackRequest(BaseModel):
    run_id: str | None = None
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class FeedbackOut(BaseModel):
    id: str
    run_id: str | None = None
    event_type: str
    payload: dict[str, Any]
    candidate_retraining: dict[str, Any]
    created_at: datetime
    caveat: str = (
        "Feedback is logged only. No production model is retrained or replaced automatically."
    )


class FeedbackListResponse(BaseModel):
    items: list[FeedbackOut]
    total: int
    limit: int
    offset: int
