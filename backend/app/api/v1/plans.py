from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.core.errors import DomainError
from backend.app.db.models import BatchPlan
from backend.app.schemas.plan import BatchPlanOut, ConstraintCheck, OptimizerRequest
from backend.app.services.optimizer import optimize

router = APIRouter(prefix="/plans", tags=["batch planning"])


def _plan_out(row: BatchPlan) -> BatchPlanOut:
    checks = [
        ConstraintCheck(**item)
        for item in (row.capacity_check or {}).get("checks", [])
    ]
    return BatchPlanOut(
        plan_id=row.id,
        service_date=row.service_date,
        meal_type=row.meal_type,
        dish_external_id=row.dish_external_id,
        initial_quantity=row.initial_qty,
        reserve_quantity=row.reserve_qty,
        replenishment_trigger=row.trigger_qty,
        batch_min=row.batch_min,
        batch_max=row.batch_max,
        capacity_total=row.capacity_total,
        capacity_remaining=row.capacity_remaining,
        lead_time_minutes=row.lead_time_minutes,
        service_close=row.service_close,
        expected_leftover=row.expected_leftover,
        expected_shortage=row.expected_shortage,
        expected_prepared=row.expected_prepared,
        objective_value=row.objective_value,
        weights=row.weights or {},
        rationale=row.rationale,
        constraint_checks=checks,
        uncertainty=row.uncertainty or {},
        approval_state=row.approval_state,
        policy_version=row.policy_version,
        model_version=row.model_version,
        is_synthetic=row.is_synthetic,
    )


@router.post("", response_model=BatchPlanOut)
def create_plan(payload: OptimizerRequest, db: Session = Depends(get_db)) -> BatchPlanOut:
    return BatchPlanOut(**optimize(payload, db=db))


@router.get("", response_model=list[BatchPlanOut])
def list_plans(
    day: date | None = Query(default=None, alias="date"),
    meal_type: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> list[BatchPlanOut]:
    limit, offset = page
    stmt = select(BatchPlan)
    if day:
        stmt = stmt.where(BatchPlan.service_date == day)
    if meal_type:
        stmt = stmt.where(BatchPlan.meal_type == meal_type)
    rows = list(
        db.scalars(
            stmt.order_by(BatchPlan.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return [_plan_out(row) for row in rows]


@router.get("/{plan_id}", response_model=BatchPlanOut)
def get_plan(plan_id: str, db: Session = Depends(get_db)) -> BatchPlanOut:
    row = db.get(BatchPlan, plan_id)
    if row is None:
        raise DomainError("PLAN_NOT_FOUND", f"batch plan not found: {plan_id}", 404)
    return _plan_out(row)
