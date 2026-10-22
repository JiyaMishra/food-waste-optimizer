"""Master orchestrator for specialized, callable agent modules.

Planning stages: context observation -> availability -> demand forecast ->
kitchen planning -> pre-meal diagnosis.
Review stages: post-meal diagnosis -> outcome/learning evaluation.

Every stage is validated with a Pydantic contract before it can influence the
next stage. An invalid module output is rejected and traced.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.agents import (
    availability_agent,
    context_agent,
    demand_agent,
    diagnosis_agent,
    kitchen_agent,
    learning_agent,
)
from backend.app.agents.contracts import (
    AvailabilityObservation,
    ContextObservation,
    DemandObservation,
    DiagnosisObservation,
    LearningObservation,
    PlanObservation,
    execute_stage,
)
from backend.app.db.models import AgentTrace
from backend.app.schemas.agents import (
    AgentStageOut,
    PlanningWorkflowRequest,
    PlanningWorkflowResponse,
    ReviewWorkflowResponse,
)
from backend.app.schemas.context import AvailabilityRequest
from backend.app.schemas.diagnosis import ForecastInput, PlannedQuantity, PreMealDiagnosisRequest
from backend.app.schemas.plan import IntervalDemand, OptimizerRequest

INTERVALS = {
    "breakfast": [time(7, 0), time(7, 30), time(8, 0), time(8, 30)],
    "lunch": [time(12, 0), time(12, 30), time(13, 0), time(13, 30)],
    "snacks": [time(16, 0), time(16, 30), time(17, 0), time(17, 30)],
    "dinner": [time(19, 0), time(19, 30), time(20, 0), time(20, 30)],
}


STAGE_SEQUENCE = {
    "context_observation": 1,
    "availability_estimate": 2,
    "demand_forecast": 3,
    "constrained_planning": 4,
    "pre_meal_diagnosis": 5,
    "post_meal_diagnosis": 6,
    "outcome_learning": 7,
}


def _stages(db: Session, trace_id: str) -> list[AgentStageOut]:
    rows = list(
        db.scalars(
            select(AgentTrace)
            .where(AgentTrace.trace_id == trace_id)
            .order_by(AgentTrace.created_at)
        ).all()
    )
    rows.sort(key=lambda r: (r.created_at, STAGE_SEQUENCE.get(r.stage, 99)))
    return [
        AgentStageOut(
            stage=row.stage,
            agent_name=row.agent_name,
            status=row.status,
            duration_ms=row.duration_ms,
            output=row.output_summary or {},
            error=row.error,
        )
        for row in rows
    ]


def _count_traces(db: Session, trace_id: str | None = None, run_id: str | None = None) -> int:
    stmt = select(func.count()).select_from(AgentTrace)
    if trace_id:
        stmt = stmt.where(AgentTrace.trace_id == trace_id)
    if run_id:
        stmt = stmt.where(AgentTrace.run_id == run_id)
    return int(db.scalar(stmt) or 0)


def get_traces(
    db: Session,
    trace_id: str | None = None,
    run_id: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[AgentTrace], int]:
    stmt = select(AgentTrace)
    if trace_id:
        stmt = stmt.where(AgentTrace.trace_id == trace_id)
    if run_id:
        stmt = stmt.where(AgentTrace.run_id == run_id)
    total = _count_traces(db, trace_id, run_id)
    rows = list(
        db.scalars(
            stmt.order_by(AgentTrace.created_at, AgentTrace.stage).limit(limit).offset(offset)
        ).all()
    )
    return rows, total


def planning_workflow(db: Session, request: PlanningWorkflowRequest) -> dict:
    trace_id = str(uuid.uuid4())
    context = execute_stage(
        db,
        trace_id,
        "context_observation",
        "context_observer",
        {
            "service_date": request.service_date.isoformat(),
            "hostel_id": request.hostel_id,
            "mess_id": request.mess_id,
        },
        lambda: context_agent.run(
            db, request.service_date, request.hostel_id, request.mess_id
        ),
        ContextObservation,
    )

    availability = execute_stage(
        db,
        trace_id,
        "availability_estimate",
        "availability_estimator",
        {
            "service_date": request.service_date.isoformat(),
            "meal_type": request.meal_type,
            "attendance_probability": request.attendance_probability,
        },
        lambda: availability_agent.run(
            db,
            AvailabilityRequest(
                date=request.service_date,
                meal_type=request.meal_type,
                hostel_id=request.hostel_id,
                mess_id=request.mess_id,
                attendance_probability=request.attendance_probability,
                persist=request.persist,
            ),
        ),
        AvailabilityObservation,
    )

    demand = execute_stage(
        db,
        trace_id,
        "demand_forecast",
        "demand_forecaster",
        {
            "service_date": request.service_date.isoformat(),
            "meal_type": request.meal_type,
            "model_version": request.model_version,
        },
        lambda: demand_agent.run(
            db, request.service_date, request.meal_type, persist=request.persist
        ),
        DemandObservation,
    )

    interval_count = len(INTERVALS.get(request.meal_type, INTERVALS["breakfast"]))
    expected = demand.total_expected / interval_count
    lower = min(expected, demand.total_lower / interval_count)
    upper = max(expected, demand.total_upper / interval_count)
    optimizer_request = OptimizerRequest(
        service_date=request.service_date,
        meal_type=request.meal_type,
        dish_external_id=None,
        intervals=[
            IntervalDemand(interval_start=start, expected=expected, lower=lower, upper=upper)
            for start in INTERVALS.get(request.meal_type, INTERVALS["breakfast"])
        ],
        current_stock=request.current_stock,
        batch_min=request.batch_min,
        batch_max=request.batch_max,
        kitchen_capacity=request.kitchen_capacity,
        prep_lead_minutes=request.prep_lead_minutes,
        service_start=request.service_start,
        service_close=request.service_close,
        now=(
            datetime.combine(request.service_date, request.service_start)
            - timedelta(minutes=request.prep_lead_minutes + 1)
        ),
        forecast_run_id=demand.forecast_run_id,
        model_version=demand.model_version,
        persist=request.persist,
    )
    plan = execute_stage(
        db,
        trace_id,
        "constrained_planning",
        "kitchen_planner",
        {
            "total_expected": demand.total_expected,
            "total_lower": demand.total_lower,
            "total_upper": demand.total_upper,
            "current_stock": request.current_stock,
            "capacity": request.kitchen_capacity,
        },
        lambda: kitchen_agent.run(db, optimizer_request),
        PlanObservation,
    )

    total_plan = float(plan.initial_quantity + plan.reserve_quantity)
    total_prediction = sum(float(row["prediction"]) for row in demand.rows) or 1.0
    planned_quantities = [
        PlannedQuantity(
            dish_id=str(row["dish_id"]),
            prepared_qty=round(
                total_plan * float(row["prediction"]) / total_prediction, 3
            ),
        )
        for row in demand.rows
    ]
    forecasts = [
        ForecastInput(
            dish_id=str(row["dish_id"]),
            prediction=float(row["prediction"]),
            lower_bound=float(row["lower_bound"]),
            upper_bound=float(row["upper_bound"]),
        )
        for row in demand.rows
    ]
    diagnosis_request = PreMealDiagnosisRequest(
        service_date=request.service_date,
        meal_type=request.meal_type,
        forecast_run_id=demand.forecast_run_id,
        forecasts=forecasts,
        planned_quantities=planned_quantities,
        persist=request.persist,
    )
    diagnoses = execute_stage(
        db,
        trace_id,
        "pre_meal_diagnosis",
        "waste_diagnostician",
        {
            "forecast_run_id": demand.forecast_run_id,
            "planned_total": total_plan,
            "dish_count": len(demand.rows),
        },
        lambda: diagnosis_agent.run_pre_meal(db, diagnosis_request, forecasts=demand.rows),
        DiagnosisObservation,
    )

    stages = _stages(db, trace_id)
    status = "completed" if all(stage.status == "completed" for stage in stages) else "failed"
    diagnosis_id = diagnoses.diagnosis_ids[-1] if diagnoses.diagnosis_ids else None
    response = PlanningWorkflowResponse(
        trace_id=trace_id,
        status=status,
        stages=stages,
        forecast_run_id=demand.forecast_run_id,
        plan_id=plan.plan_id,
        diagnosis_id=diagnosis_id,
        outputs={
            "context": context.model_dump(mode="json"),
            "availability": availability.model_dump(mode="json"),
            "demand": {
                "forecast_run_id": demand.forecast_run_id,
                "total_expected": demand.total_expected,
                "total_lower": demand.total_lower,
                "total_upper": demand.total_upper,
                "model_version": demand.model_version,
                "row_count": len(demand.rows),
            },
            "plan": plan.model_dump(mode="json"),
            "diagnoses": diagnoses.diagnoses,
        },
        requires_human_approval=True,
    )
    return response.model_dump(mode="json")


def review_workflow(db: Session, run_id: str, persist: bool = True) -> dict:
    trace_id = str(uuid.uuid4())
    diagnosis = execute_stage(
        db,
        trace_id,
        "post_meal_diagnosis",
        "waste_diagnostician",
        {"run_id": run_id},
        lambda: diagnosis_agent.run_post_meal(db, run_id),
        DiagnosisObservation,
        run_id=run_id,
    )
    learning = execute_stage(
        db,
        trace_id,
        "outcome_learning",
        "learning_evaluator",
        {"run_id": run_id},
        lambda: learning_agent.run(db, run_id, persist=persist),
        LearningObservation,
        run_id=run_id,
    )
    stages = _stages(db, trace_id)
    diagnosis_id = diagnosis.diagnosis_ids[0] if diagnosis.diagnosis_ids else None
    response = ReviewWorkflowResponse(
        trace_id=trace_id,
        run_id=run_id,
        status="completed",
        stages=stages,
        evaluation_id=learning.evaluation_id,
        diagnosis_id=diagnosis_id,
        outputs={
            "diagnosis": diagnosis.diagnoses,
            "evaluation": {
                "evaluation_id": learning.evaluation_id,
                "metrics": learning.metrics,
                "model_metrics": learning.model_metrics,
            },
            "candidate_retraining": learning.candidate_retraining,
        },
    )
    return response.model_dump(mode="json")


def trace_stages(db: Session, trace_id: str) -> list[dict]:
    return [stage.model_dump(mode="json") for stage in _stages(db, trace_id)]
