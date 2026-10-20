from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.agents.orchestrator import (
    get_traces,
    planning_workflow,
    review_workflow,
)
from backend.app.api.deps import get_db, pagination
from backend.app.core.errors import DomainError
from backend.app.schemas.agents import (
    PlanningWorkflowRequest,
    PlanningWorkflowResponse,
    ReviewWorkflowRequest,
    ReviewWorkflowResponse,
    TraceListResponse,
    TraceOut,
)

router = APIRouter(prefix="/agents", tags=["agent orchestration"])


@router.post("/planning", response_model=PlanningWorkflowResponse)
def run_planning_workflow(
    payload: PlanningWorkflowRequest, db: Session = Depends(get_db)
) -> PlanningWorkflowResponse:
    return PlanningWorkflowResponse(**planning_workflow(db, payload))


@router.post("/review", response_model=ReviewWorkflowResponse)
def run_review_workflow(
    payload: ReviewWorkflowRequest, db: Session = Depends(get_db)
) -> ReviewWorkflowResponse:
    return ReviewWorkflowResponse(**review_workflow(db, payload.run_id, payload.persist))


@router.get("/traces", response_model=TraceListResponse)
def list_traces(
    trace_id: str | None = None,
    run_id: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> TraceListResponse:
    limit, offset = page
    rows, total = get_traces(db, trace_id, run_id, limit, offset)
    return TraceListResponse(
        items=[TraceOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/traces/{trace_id}", response_model=TraceListResponse)
def get_trace(
    trace_id: str,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> TraceListResponse:
    limit, offset = page
    rows, total = get_traces(db, trace_id=trace_id, limit=limit, offset=offset)
    if total == 0:
        raise DomainError("TRACE_NOT_FOUND", f"agent trace not found: {trace_id}", 404)
    return TraceListResponse(
        items=[TraceOut.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
