"""JSON/CSV export helpers for operational runs and agent traces."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import DomainError
from backend.app.db.models import (
    AgentTrace,
    BatchPlan,
    Diagnosis,
    EvaluationRun,
    Intervention,
    MealRun,
    Outcome,
    Prediction,
    SimulationEvent,
)
from backend.app.services.evaluation import latest_evaluation


def _jsonable(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def run_export(db: Session, run_id: str) -> dict:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    outcome = db.scalar(select(Outcome).where(Outcome.run_id == run_id))
    events = list(
        db.scalars(
            select(SimulationEvent)
            .where(SimulationEvent.run_id == run_id)
            .order_by(SimulationEvent.interval_index)
        ).all()
    )
    interventions = list(
        db.scalars(select(Intervention).where(Intervention.run_id == run_id)).all()
    )
    diagnoses = list(
        db.scalars(select(Diagnosis).where(Diagnosis.run_id == run_id)).all()
    )
    plans = list(
        db.scalars(select(BatchPlan).where(BatchPlan.run_id == run_id)).all()
    )
    traces = list(
        db.scalars(select(AgentTrace).where(AgentTrace.run_id == run_id)).all()
    )
    evaluation = latest_evaluation(db, run_id)
    predictions = []
    if run.forecast_run_id:
        predictions = list(
            db.scalars(
                select(Prediction).where(Prediction.forecast_run_id == run.forecast_run_id)
            ).all()
        )
    return {
        "run": {
            "id": run.id,
            "status": run.status,
            "scenario_id": run.scenario_id,
            "dataset_version": run.dataset_version,
            "seed": run.seed,
            "service_date": run.service_date,
            "meal_type": run.meal_type,
            "dish_external_id": run.dish_external_id,
            "policy_id": run.policy_id,
            "policy_version": run.policy_version,
            "model_version": run.model_version,
            "forecast_run_id": run.forecast_run_id,
            "current_interval": run.current_interval,
            "intervals_total": run.intervals_total,
            "demand_realization": run.demand_realization,
            "config": run.config,
            "is_synthetic": run.is_synthetic,
            "created_at": run.created_at,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        },
        "outcome": (
            {
                "prepared_total": outcome.prepared_total,
                "served_total": outcome.served_total,
                "consumed_total": outcome.consumed_total,
                "untouched_leftover": outcome.untouched_leftover,
                "plate_waste": outcome.plate_waste,
                "shortage": outcome.shortage,
                "excess_preparation": outcome.excess_preparation,
                "forecast_error_abs": outcome.forecast_error_abs,
                "forecast_error_pct": outcome.forecast_error_pct,
            }
            if outcome
            else None
        ),
        "events": [
            {
                "interval_index": item.interval_index,
                "interval_start": item.interval_start,
                "arrivals": item.arrivals,
                "stock_before": item.stock_before,
                "stock_after": item.stock_after,
                "prepared_qty": item.prepared_qty,
                "served_qty": item.served_qty,
                "unmet_qty": item.unmet_qty,
                "projected_demand": item.projected_demand,
                "action": item.action,
                "action_reason": item.action_reason,
            }
            for item in events
        ],
        "interventions": [
            {
                "id": item.id,
                "action_type": item.action_type,
                "requested_qty": item.requested_qty,
                "approved_qty": item.approved_qty,
                "status": item.status,
                "approval_required": item.approval_required,
                "reason": item.reason,
                "detail_json": item.detail_json,
            }
            for item in interventions
        ],
        "diagnoses": [
            {
                "id": item.id,
                "diagnosis_type": item.diagnosis_type,
                "risk_score": item.risk_score,
                "confidence": item.confidence,
                "causes": item.causes,
                "evidence": item.evidence,
                "caveats": item.caveats,
            }
            for item in diagnoses
        ],
        "batch_plans": [
            {
                "id": item.id,
                "initial_qty": item.initial_qty,
                "reserve_qty": item.reserve_qty,
                "trigger_qty": item.trigger_qty,
                "objective_value": item.objective_value,
                "approval_state": item.approval_state,
                "rationale": item.rationale,
            }
            for item in plans
        ],
        "agent_traces": [
            {
                "trace_id": item.trace_id,
                "stage": item.stage,
                "agent_name": item.agent_name,
                "status": item.status,
                "duration_ms": item.duration_ms,
                "error": item.error,
            }
            for item in traces
        ],
        "predictions": [
            {
                "dish_external_id": item.dish_external_id,
                "prediction": item.prediction,
                "lower_bound": item.lower_bound,
                "upper_bound": item.upper_bound,
                "model_version": item.model_version,
            }
            for item in predictions
        ],
        "evaluation": (
            {
                "id": evaluation.id,
                "metrics": evaluation.metrics,
                "denominators": evaluation.denominators,
                "model_metrics": evaluation.model_metrics,
            }
            if evaluation
            else None
        ),
    }


def run_export_csv(db: Session, run_id: str) -> str:
    data = run_export(db, run_id)
    output = io.StringIO()
    fieldnames = [
        "record_type", "interval_index", "interval_start", "arrivals", "stock_before",
        "stock_after", "prepared_qty", "served_qty", "unmet_qty", "projected_demand",
        "action", "action_reason", "prepared_total", "served_total", "consumed_total",
        "untouched_leftover", "plate_waste", "shortage", "excess_preparation",
        "forecast_error_abs", "forecast_error_pct", "scenario_id", "seed",
        "policy_id", "policy_version", "model_version",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    run = data["run"]
    for event in data["events"]:
        row = {
            "record_type": "interval_event",
            "scenario_id": run["scenario_id"],
            "seed": run["seed"],
            "policy_id": run["policy_id"],
            "policy_version": run["policy_version"],
            "model_version": run["model_version"],
            **{key: event.get(key) for key in fieldnames if key in event},
        }
        writer.writerow(row)
    if data["outcome"]:
        writer.writerow(
            {
                "record_type": "outcome",
                "scenario_id": run["scenario_id"],
                "seed": run["seed"],
                "policy_id": run["policy_id"],
                "policy_version": run["policy_version"],
                "model_version": run["model_version"],
                **data["outcome"],
            }
        )
    return output.getvalue()


def traces_export_json(db: Session, trace_id: str | None = None) -> dict:
    stmt = select(AgentTrace)
    if trace_id:
        stmt = stmt.where(AgentTrace.trace_id == trace_id)
    rows = list(db.scalars(stmt.order_by(AgentTrace.created_at)).all())
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "trace_id": row.trace_id,
                "run_id": row.run_id,
                "stage": row.stage,
                "agent_name": row.agent_name,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "error": row.error,
                "created_at": row.created_at,
                "input_summary": row.input_summary,
                "output_summary": row.output_summary,
                "tool_calls": row.tool_calls,
            }
            for row in rows
        ],
    }


def traces_export_csv(db: Session, trace_id: str | None = None) -> str:
    stmt = select(AgentTrace)
    if trace_id:
        stmt = stmt.where(AgentTrace.trace_id == trace_id)
    rows = list(db.scalars(stmt.order_by(AgentTrace.created_at)).all())
    output = io.StringIO()
    fieldnames = [
        "trace_id", "stage", "agent_name", "status", "duration_ms", "error",
        "created_at", "run_id", "input_summary", "output_summary", "tool_calls",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "trace_id": row.trace_id,
                "stage": row.stage,
                "agent_name": row.agent_name,
                "status": row.status,
                "duration_ms": row.duration_ms,
                "error": row.error,
                "created_at": row.created_at.isoformat() if row.created_at else "",
                "run_id": row.run_id,
                "input_summary": _jsonable(row.input_summary),
                "output_summary": _jsonable(row.output_summary),
                "tool_calls": _jsonable(row.tool_calls),
            }
        )
    return output.getvalue()
