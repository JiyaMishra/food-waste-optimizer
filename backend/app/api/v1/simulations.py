from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.core.errors import DomainError
from backend.app.db.models import MealRun, Outcome
from backend.app.schemas.simulation import (
    CompareResponse,
    FinishResponse,
    OutcomeOut,
    SimulationCompareRequest,
    SimulationRunListResponse,
    SimulationRunOut,
    SimulationStartRequest,
    StepResponse,
)
from backend.app.services.simulator import (
    compare_policies,
    finish_simulation,
    serialize_run,
    start_simulation,
    step_simulation,
)

router = APIRouter(prefix="/simulations", tags=["meal-service simulation"])


@router.post("", response_model=SimulationRunOut)
def start(payload: SimulationStartRequest, db: Session = Depends(get_db)) -> SimulationRunOut:
    if not payload.persist:
        raise DomainError(
            "SIMULATION_REQUIRES_PERSISTENCE",
            "start and compare simulations must persist runs so step/finish can reference them",
            422,
        )
    return serialize_run(start_simulation(db, payload))


@router.post("/compare", response_model=CompareResponse)
def compare(payload: SimulationCompareRequest, db: Session = Depends(get_db)) -> CompareResponse:
    if not payload.persist:
        raise DomainError(
            "SIMULATION_REQUIRES_PERSISTENCE",
            "comparison runs must persist so outcomes and traces are reproducible",
            422,
        )
    return CompareResponse(**compare_policies(db, payload))


@router.get("", response_model=SimulationRunListResponse)
def list_runs(
    day: date | None = Query(default=None, alias="date"),
    meal_type: str | None = None,
    status: str | None = None,
    policy_id: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> SimulationRunListResponse:
    limit, offset = page
    stmt = select(MealRun)
    count_stmt = select(func.count()).select_from(MealRun)
    if day:
        stmt = stmt.where(MealRun.service_date == day)
        count_stmt = count_stmt.where(MealRun.service_date == day)
    if meal_type:
        stmt = stmt.where(MealRun.meal_type == meal_type)
        count_stmt = count_stmt.where(MealRun.meal_type == meal_type)
    if status:
        stmt = stmt.where(MealRun.status == status)
        count_stmt = count_stmt.where(MealRun.status == status)
    if policy_id:
        stmt = stmt.where(MealRun.policy_id == policy_id)
        count_stmt = count_stmt.where(MealRun.policy_id == policy_id)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(stmt.order_by(MealRun.created_at.desc()).limit(limit).offset(offset)).all()
    )
    return SimulationRunListResponse(
        items=[serialize_run(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/{run_id}/step", response_model=StepResponse)
def step(run_id: str, db: Session = Depends(get_db)) -> StepResponse:
    return StepResponse(**step_simulation(db, run_id))


@router.post("/{run_id}/finish", response_model=FinishResponse)
def finish(run_id: str, db: Session = Depends(get_db)) -> FinishResponse:
    return FinishResponse(**finish_simulation(db, run_id))


@router.get("/{run_id}", response_model=SimulationRunOut)
def get_run(run_id: str, db: Session = Depends(get_db)) -> SimulationRunOut:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    return serialize_run(run)


@router.get("/{run_id}/outcome", response_model=OutcomeOut)
def get_outcome(run_id: str, db: Session = Depends(get_db)) -> OutcomeOut:
    outcome = db.scalar(select(Outcome).where(Outcome.run_id == run_id))
    if outcome is None:
        raise DomainError("OUTCOME_NOT_FOUND", f"no outcome for run {run_id}", 404)
    return OutcomeOut.model_validate(outcome)
