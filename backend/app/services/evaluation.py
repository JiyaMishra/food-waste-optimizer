"""Operational evaluation from persisted simulation runs.

Model forecasting metrics are deliberately kept in a separate ``model_metrics``
object and are never mixed into policy waste/shortage metrics.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import DomainError
from backend.app.db.models import (
    EvaluationRun,
    Intervention,
    MealRun,
    Outcome,
    SimulationEvent,
)
from backend.app.schemas.evaluation import EvaluationCompareResponse, EvaluationOut


def _safe_div(numerator: float, denominator: float) -> float | None:
    if denominator is None or denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _evaluation_out(row: EvaluationRun) -> EvaluationOut:
    return EvaluationOut(
        id=row.id,
        run_id=row.run_id,
        policy_id=row.policy_id,
        scenario_id=row.scenario_id,
        seed=row.seed,
        policy_version=row.policy_version,
        model_version=row.model_version,
        metrics=row.metrics,
        denominators=row.denominators,
        model_metrics=row.model_metrics,
        is_synthetic=row.is_synthetic,
        created_at=row.created_at,
    )


def evaluation_to_schema(row: EvaluationRun) -> EvaluationOut:
    return _evaluation_out(row)


def evaluate_run(db: Session, run_id: str, persist: bool = True) -> dict:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    outcome = db.scalar(select(Outcome).where(Outcome.run_id == run_id))
    if run.status != "finished" or outcome is None:
        raise DomainError(
            "RUN_NOT_FINISHED",
            "evaluation requires a finished simulation with persisted outcomes",
            409,
            {"run_id": run_id, "status": run.status},
        )
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
    total_demand = float(outcome.served_total + outcome.shortage)
    total_waste = float(outcome.untouched_leftover + outcome.plate_waste)
    completed_reserve = [
        item
        for item in interventions
        if item.action_type == "replenish_reserve" and item.status == "simulated"
    ]
    successful_reserve = [
        item
        for item in completed_reserve
        if outcome.shortage <= 0
        and int(((item.detail_json or {}).get("completed_interval") or 0))
        < (run.intervals_total or 1)
    ]
    response_times = [
        int((item.detail_json or {}).get("completed_interval", 0))
        - int((item.detail_json or {}).get("trigger_interval", 0))
        for item in completed_reserve
    ]
    notes: list[str] = []
    denominators = {
        "prepared_total": outcome.prepared_total,
        "served_total": outcome.served_total,
        "total_demand": total_demand,
        "service_intervals": len(events),
    }
    for name in ("prepared_total", "served_total", "total_demand"):
        if denominators[name] <= 0:
            notes.append(
                f"{name} is zero; ratio metrics with this denominator are returned as null."
            )
    metrics = {
        "prepared_portions": outcome.prepared_total,
        "served_portions": outcome.served_total,
        "consumed_portions": outcome.consumed_total,
        "untouched_leftover_portions": outcome.untouched_leftover,
        "plate_waste_portions": outcome.plate_waste,
        "total_waste_portions": round(total_waste, 3),
        "shortage_portions": outcome.shortage,
        "excess_preparation_portions": outcome.excess_preparation,
        "waste_rate_per_prepared": _safe_div(total_waste, outcome.prepared_total),
        "leftover_rate_per_prepared": _safe_div(
            outcome.untouched_leftover, outcome.prepared_total
        ),
        "plate_waste_rate_per_served": _safe_div(outcome.plate_waste, outcome.served_total),
        "shortage_rate_per_demand": _safe_div(outcome.shortage, total_demand),
        "excess_preparation_rate": _safe_div(
            outcome.excess_preparation, outcome.prepared_total
        ),
        "total_arrivals": round(sum(event.arrivals for event in events), 3),
        "intervention_count": len(interventions),
        "completed_reserve_interventions": len(completed_reserve),
        "successful_reserve_interventions": len(successful_reserve),
        "intervention_success_rate": _safe_div(
            len(successful_reserve), len(completed_reserve)
        ),
        "average_response_time_intervals": (
            round(sum(response_times) / len(response_times), 3)
            if response_times
            else None
        ),
        "interpretation_notes": notes,
    }
    model_metrics = {
        "forecast_error_abs_portions": outcome.forecast_error_abs,
        "forecast_error_pct": outcome.forecast_error_pct,
        "note": (
            "Model forecast accuracy is reported separately and is not an operational "
            "waste-reduction metric."
        ),
    }
    if persist:
        row = EvaluationRun(
            run_id=run.id,
            policy_id=run.policy_id,
            scenario_id=run.scenario_id,
            seed=run.seed,
            metrics=metrics,
            denominators=denominators,
            model_metrics=model_metrics,
            model_version=run.model_version,
            policy_version=run.policy_version,
            is_synthetic=True,
        )
        db.add(row)
        db.flush()
        return _evaluation_out(row).model_dump()
    return EvaluationOut(
        id="",
        run_id=run.id,
        policy_id=run.policy_id,
        scenario_id=run.scenario_id,
        seed=run.seed,
        policy_version=run.policy_version,
        model_version=run.model_version,
        metrics=metrics,
        denominators=denominators,
        model_metrics=model_metrics,
        is_synthetic=True,
        created_at=run.created_at,
    ).model_dump()


def latest_evaluation(db: Session, run_id: str) -> EvaluationRun | None:
    return db.scalar(
        select(EvaluationRun)
        .where(EvaluationRun.run_id == run_id)
        .order_by(EvaluationRun.created_at.desc())
    )


def compare_runs(
    db: Session, baseline_run_id: str, context_run_id: str, persist: bool = True
) -> dict:
    if baseline_run_id == context_run_id:
        raise DomainError(
            "EVALUATION_COMPARISON_INVALID",
            "baseline and context run ids must be different",
            422,
        )
    baseline = evaluate_run(db, baseline_run_id, persist=persist)
    context = evaluate_run(db, context_run_id, persist=persist)
    keys = [
        "total_waste_portions",
        "shortage_portions",
        "waste_rate_per_prepared",
        "shortage_rate_per_demand",
        "excess_preparation_portions",
        "intervention_success_rate",
        "average_response_time_intervals",
    ]
    deltas: dict[str, float | None] = {}
    for key in keys:
        base_value = baseline["metrics"].get(key)
        context_value = context["metrics"].get(key)
        if base_value is None or context_value is None:
            deltas[key] = None
        else:
            deltas[key] = round(float(context_value) - float(base_value), 6)
    caveats = [
        "Both runs must use the same demand realization and seed for a fair comparison.",
        "Synthetic simulation metrics do not establish real-world waste reduction.",
        (
            "Evaluation returns null deltas when a denominator is zero; it does not "
            "fabricate a percentage."
        ),
    ]
    response = EvaluationCompareResponse(
        baseline=EvaluationOut(**{**baseline, "id": baseline["id"] or "not-persisted"}),
        context=EvaluationOut(**{**context, "id": context["id"] or "not-persisted"}),
        deltas=deltas,
        caveats=caveats,
    )
    return response.model_dump()
