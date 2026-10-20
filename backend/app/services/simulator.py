"""Meal-service simulator comparing a fixed baseline and a split-batch policy.

Both policies can run on the exact same synthetic arrival realization. The
simulator executes simulation actions only; live kitchen action requires human
approval and is never performed here.
"""
from __future__ import annotations

import math
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.errors import DomainError
from backend.app.db.models import Intervention, MealRun, Outcome, SimulationEvent
from backend.app.schemas.plan import IntervalDemand, OptimizerRequest
from backend.app.schemas.simulation import (
    CompareResponse,
    FinishResponse,
    IntervalArrival,
    InterventionOut,
    OutcomeOut,
    SimulationCompareRequest,
    SimulationEventOut,
    SimulationRunOut,
    SimulationStartRequest,
    StepResponse,
)
from backend.app.services.optimizer import optimize

BASELINE_POLICY_ID = "baseline_fixed"
CONTEXT_POLICY_ID = "context_aware_split"
POLICY_VERSION = "1.0.0"
INTERVAL_STARTS = {
    "breakfast": [time(7, 0), time(7, 30), time(8, 0), time(8, 30)],
    "lunch": [time(12, 0), time(12, 30), time(13, 0), time(13, 30)],
    "snacks": [time(16, 0), time(16, 30), time(17, 0), time(17, 30)],
    "dinner": [time(19, 0), time(19, 30), time(20, 0), time(20, 30)],
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


def _run_out(run: MealRun) -> SimulationRunOut:
    return SimulationRunOut(
        id=run.id,
        status=run.status,
        scenario_id=run.scenario_id,
        dataset_version=run.dataset_version,
        seed=run.seed,
        service_date=run.service_date,
        meal_type=run.meal_type,
        dish_external_id=run.dish_external_id,
        policy_id=run.policy_id,
        policy_version=run.policy_version,
        model_version=run.model_version,
        forecast_run_id=run.forecast_run_id,
        current_interval=run.current_interval,
        intervals_total=run.intervals_total,
        is_synthetic=run.is_synthetic,
        created_at=run.created_at,
        config=run.config or {},
    )


def _historical_arrivals(
    meal_type: str, day: date, dish_external_id: str | None = None
) -> list[dict]:
    settings = get_settings()
    path = settings.data_path / "meal_attendance.csv"
    if not path.exists():
        raise DomainError(
            "HISTORICAL_ARRIVALS_MISSING",
            f"meal_attendance.csv not found: {path}",
            404,
            {"hint": "POST /api/v1/data/generate, or supply explicit intervals"},
        )
    frame = pd.read_csv(path, parse_dates=["date"])
    subset = frame[(frame["date"].dt.date == day) & (frame["meal_type"] == meal_type)]
    if subset.empty:
        raise DomainError(
            "HISTORICAL_ARRIVALS_MISSING",
            f"no synthetic arrivals for {day.isoformat()} / {meal_type}",
            404,
        )
    subset = subset.sort_values("interval_start")
    rows = [
        {
            "interval_start": datetime.strptime(str(row["interval_start"]), "%H:%M").time(),
            "arrivals": float(row["arrivals"]),
        }
        for row in subset.to_dict("records")
    ]
    if not dish_external_id:
        return rows
    operations_path = settings.data_path / "food_operations.csv"
    if not operations_path.exists():
        return rows
    operations = pd.read_csv(operations_path, parse_dates=["date"])
    meal_rows = operations[
        (operations["date"].dt.date == day) & (operations["meal_type"] == meal_type)
    ]
    dish_rows = meal_rows[meal_rows["dish_id"].astype(str) == str(dish_external_id)]
    total_demand = float(meal_rows["demand_qty"].sum())
    dish_demand = float(dish_rows["demand_qty"].sum())
    if total_demand <= 0 or dish_demand <= 0:
        return rows
    share = dish_demand / total_demand
    return [
        {"interval_start": row["interval_start"], "arrivals": round(row["arrivals"] * share, 4)}
        for row in rows
    ]


def _build_realization(request: SimulationStartRequest | SimulationCompareRequest) -> list[dict]:
    if request.intervals:
        return [
            {"interval_start": item.interval_start, "arrivals": float(item.arrivals)}
            for item in request.intervals
        ]
    if request.use_historical:
        return _historical_arrivals(
            request.meal_type,
            request.historical_date or request.service_date,
            request.dish_external_id,
        )
    starts = INTERVAL_STARTS.get(request.meal_type, INTERVAL_STARTS["breakfast"])
    total = request.forecast_expected
    if total is None:
        total = max(float(request.batch_min), min(float(request.capacity or 500), 240.0))
    rng = np.random.default_rng(request.seed)
    weights = rng.dirichlet(np.ones(len(starts)) * 2)
    arrivals = rng.multinomial(int(round(total)), weights)
    return [
        {"interval_start": start, "arrivals": float(amount)}
        for start, amount in zip(starts, arrivals)
    ]


def _service_close(request: SimulationStartRequest | SimulationCompareRequest, realization: list[dict]) -> time:
    if request.service_close is not None:
        return request.service_close
    last_start = max(item["interval_start"] for item in realization)
    close_dt = datetime.combine(request.service_date, last_start) + timedelta(hours=1)
    return close_dt.time()


def _context_plan(
    request: SimulationStartRequest | SimulationCompareRequest,
    realization: list[dict],
    forecast_total: float,
) -> dict:
    if request.plan is not None:
        return request.plan.model_dump()
    interval_count = len(realization)
    per_interval = forecast_total / interval_count if interval_count else 0.0
    intervals = [
        IntervalDemand(
            interval_start=item["interval_start"],
            expected=per_interval,
            lower=max(0.0, per_interval * 0.75),
            upper=per_interval * 1.25,
        )
        for item in realization
    ]
    close = _service_close(request, realization)
    plan = optimize(
        OptimizerRequest(
            service_date=request.service_date,
            meal_type=request.meal_type,
            dish_external_id=request.dish_external_id,
            intervals=intervals,
            current_stock=request.current_stock,
            batch_min=request.batch_min,
            batch_max=request.batch_max,
            kitchen_capacity=request.capacity,
            prep_lead_minutes=request.prep_lead_intervals * 30,
            service_start=request.service_start,
            service_close=close,
            now=(
                datetime.combine(request.service_date, request.service_start)
                - timedelta(minutes=request.prep_lead_intervals * 30 + 1)
            ),
            persist=False,
            model_version=None,
        ),
        db=None,
    )
    return {
        "initial_qty": plan["initial_quantity"],
        "reserve_qty": plan["reserve_quantity"],
        "trigger_qty": plan["replenishment_trigger"],
    }


def _baseline_plan(
    request: SimulationStartRequest | SimulationCompareRequest, forecast_total: float, realization: list[dict]
) -> dict:
    fixed = min(
        float(request.capacity),
        max(float(request.batch_min), math.ceil(forecast_total * 1.05)),
    )
    return {"initial_qty": fixed, "reserve_qty": 0.0, "trigger_qty": 0.0}


def _create_run(
    db: Session,
    request: SimulationStartRequest | SimulationCompareRequest,
    policy_id: str,
    realization: list[dict],
    plan: dict,
    forecast_total: float | None,
    forecast_source: str,
) -> MealRun:
    initial_qty = float(plan["initial_qty"])
    config = {
        "current_stock": float(request.current_stock),
        "initial_qty": initial_qty,
        "stock": float(request.current_stock) + initial_qty,
        "capacity": float(request.capacity),
        "batch_min": float(request.batch_min),
        "batch_max": float(request.batch_max),
        "consumption_rate": float(request.consumption_rate),
        "prep_lead_intervals": int(request.prep_lead_intervals),
        "service_start": request.service_start.strftime("%H:%M"),
        "service_close": _service_close(request, realization).strftime("%H:%M"),
        "plan": {
            "initial_qty": initial_qty,
            "reserve_qty": float(plan.get("reserve_qty", 0)),
            "trigger_qty": float(plan.get("trigger_qty", 0)),
        },
        "reserve_status": "available",
        "forecast_expected": forecast_total,
        "forecast_source": forecast_source,
        "interval_starts": [item["interval_start"].strftime("%H:%M") for item in realization],
        "demand_realization_source": (
            "explicit_intervals"
            if request.intervals
            else (
                "historical_meal_attendance_scaled_by_dish_share"
                if request.use_historical and request.dish_external_id
                else (
                    "historical_meal_attendance"
                    if request.use_historical
                    else "seeded_synthetic"
                )
            )
        ),
        "simulation_only": True,
        "human_approval_required_for_live_action": True,
    }
    run = MealRun(
        scenario_id=request.scenario_id,
        dataset_version=request.dataset_version,
        seed=request.seed,
        service_date=request.service_date,
        meal_type=request.meal_type,
        dish_external_id=request.dish_external_id,
        policy_id=policy_id,
        policy_version=POLICY_VERSION,
        model_version=request.model_version,
        forecast_run_id=request.forecast_run_id,
        status="running",
        current_interval=0,
        intervals_total=len(realization),
        demand_realization=[float(item["arrivals"]) for item in realization],
        config=_jsonable(config),
        started_at=datetime.now(timezone.utc),
        is_synthetic=True,
    )
    db.add(run)
    db.flush()
    if initial_qty > 0:
        db.add(
            Intervention(
                run_id=run.id,
                action_type="initial_batch_prepared",
                requested_qty=initial_qty,
                approved_qty=initial_qty,
                status="simulated",
                approval_required=True,
                reason="Initial batch added before service (simulation action only).",
                detail_json={
                    "human_approval_required_for_live_action": True,
                    "simulation_only": True,
                },
            )
        )
        db.flush()
    return run


def start_simulation(
    db: Session, request: SimulationStartRequest, realization: list[dict] | None = None
) -> MealRun:
    realization = realization or _build_realization(request)
    total_arrivals = sum(item["arrivals"] for item in realization)
    forecast_total = request.forecast_expected if request.forecast_expected is not None else total_arrivals
    forecast_source = (
        "supplied_forecast" if request.forecast_expected is not None else "realized_total_planning_proxy"
    )
    if request.policy == BASELINE_POLICY_ID:
        plan = _baseline_plan(request, forecast_total, realization)
    else:
        plan = _context_plan(request, realization, forecast_total)
    return _create_run(
        db, request, request.policy, realization, plan, forecast_total, forecast_source
    )


def step_simulation(db: Session, run_id: str) -> dict:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    if run.status == "finished":
        raise DomainError(
            "RUN_ALREADY_FINISHED", "cannot step a finished simulation run", 409, {"run_id": run_id}
        )
    if run.status != "running":
        raise DomainError(
            "RUN_NOT_RUNNING", f"simulation run is {run.status}, not running", 409
        )
    if run.current_interval >= run.intervals_total:
        raise DomainError(
            "SIMULATION_INTERVALS_EXHAUSTED",
            "all service intervals have already been stepped; call finish",
            409,
        )

    config = dict(run.config or {})
    plan = dict(config.get("plan", {}))
    index = run.current_interval
    arrivals = float(run.demand_realization[index])
    stock = float(config.get("stock", 0))
    action = "none"
    reason = None
    reserve_added = 0.0
    created_interventions: list[Intervention] = []

    scheduled = list(
        db.scalars(
            select(Intervention).where(
                Intervention.run_id == run_id, Intervention.status == "scheduled"
            )
        ).all()
    )
    for intervention in scheduled:
        complete_interval = int((intervention.detail_json or {}).get("complete_interval", index))
        if complete_interval <= index:
            quantity = float(intervention.approved_qty or intervention.requested_qty)
            stock += quantity
            reserve_added += quantity
            intervention.status = "simulated"
            detail = dict(intervention.detail_json or {})
            detail["completed_interval"] = index
            detail["simulation_only"] = True
            intervention.detail_json = detail
            action = "reserve_added"
            reason = "Scheduled reserve batch completed and entered service stock."
            created_interventions.append(intervention)

    reserve_qty = float(plan.get("reserve_qty", 0))
    trigger = float(plan.get("trigger_qty", 0))
    reserve_status = str(config.get("reserve_status", "available"))
    if (
        run.policy_id == CONTEXT_POLICY_ID
        and reserve_qty > 0
        and reserve_status == "available"
    ):
        if stock <= trigger:
            complete_interval = index + int(config.get("prep_lead_intervals", 0))
            if complete_interval < run.intervals_total:
                intervention = Intervention(
                    run_id=run.id,
                    action_type="replenish_reserve",
                    requested_qty=reserve_qty,
                    approved_qty=reserve_qty,
                    status="scheduled",
                    approval_required=True,
                    reason=(
                        f"Stock {stock:.2f} <= trigger {trigger:.2f}; reserve preparation is "
                        f"feasible before close."
                    ),
                    detail_json={
                        "trigger_interval": index,
                        "complete_interval": complete_interval,
                        "simulation_only": True,
                        "human_approval_required_for_live_action": True,
                    },
                )
                db.add(intervention)
                config["reserve_status"] = "scheduled"
                if action == "none":
                    action = "reserve_scheduled"
                    reason = intervention.reason
                created_interventions.append(intervention)
            else:
                intervention = Intervention(
                    run_id=run.id,
                    action_type="replenish_reserve",
                    requested_qty=reserve_qty,
                    approved_qty=None,
                    status="cancelled",
                    approval_required=True,
                    reason="Reserve preparation cannot finish before service close.",
                    detail_json={
                        "trigger_interval": index,
                        "required_complete_interval": complete_interval,
                        "intervals_total": run.intervals_total,
                        "simulation_only": True,
                    },
                )
                db.add(intervention)
                config["reserve_status"] = "cancelled"
                if action == "none":
                    action = "reserve_cancelled"
                    reason = intervention.reason
                created_interventions.append(intervention)
        elif action == "none":
            action = "hold"
            reason = f"Stock {stock:.2f} remains above reserve trigger {trigger:.2f}."

    served = min(stock, arrivals)
    stock_after = max(0.0, stock - served)
    unmet = max(0.0, arrivals - served)
    remaining = run.demand_realization[index + 1:]
    projected = float(sum(remaining))

    event = SimulationEvent(
        run_id=run.id,
        interval_index=index,
        interval_start=datetime.strptime(
            config.get("interval_starts", ["07:00"] * run.intervals_total)[index], "%H:%M"
        ).time(),
        arrivals=arrivals,
        stock_before=stock,
        stock_after=stock_after,
        prepared_qty=reserve_added,
        served_qty=served,
        unmet_qty=unmet,
        projected_demand=projected,
        action=action,
        action_reason=reason,
    )
    db.add(event)
    config["stock"] = stock_after
    run.config = _jsonable(config)
    run.current_interval = index + 1
    db.flush()

    return {
        "run": _run_out(run),
        "event": SimulationEventOut.model_validate(event),
        "interventions": [InterventionOut.model_validate(item) for item in created_interventions],
        "finished": False,
        "message": "Interval stepped. Call step again or finish when all intervals are complete.",
    }


def finish_simulation(db: Session, run_id: str) -> dict:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    existing = db.scalar(select(Outcome).where(Outcome.run_id == run_id))
    if run.status == "finished" and existing is not None:
        return _finish_response(db, run, existing)
    if run.current_interval < run.intervals_total:
        raise DomainError(
            "SIMULATION_NOT_COMPLETE",
            "cannot finish before every service interval is stepped",
            409,
            {
                "run_id": run_id,
                "step": run.current_interval,
                "intervals_total": run.intervals_total,
            },
        )
    events = list(
        db.scalars(
            select(SimulationEvent)
            .where(SimulationEvent.run_id == run_id)
            .order_by(SimulationEvent.interval_index)
        ).all()
    )
    config = dict(run.config or {})
    initial = float(config.get("initial_qty", 0))
    starting_stock = float(config.get("current_stock", 0))
    reserve_added = sum(event.prepared_qty for event in events)
    prepared_total = starting_stock + initial + reserve_added
    served_total = sum(event.served_qty for event in events)
    consumed_total = round(served_total * float(config.get("consumption_rate", 0.85)), 3)
    consumed_total = min(consumed_total, served_total)
    untouched = max(0.0, prepared_total - served_total)
    plate = max(0.0, served_total - consumed_total)
    shortage = sum(event.unmet_qty for event in events)
    forecast_expected = config.get("forecast_expected")
    forecast_error_abs = None
    forecast_error_pct = None
    actual_demand = served_total + shortage
    if forecast_expected is not None:
        forecast_error_abs = round(abs(float(forecast_expected) - actual_demand), 3)
        forecast_error_pct = (
            round(forecast_error_abs / actual_demand, 4) if actual_demand > 0 else None
        )

    outcome = Outcome(
        run_id=run.id,
        prepared_total=round(prepared_total, 3),
        served_total=round(served_total, 3),
        consumed_total=consumed_total,
        untouched_leftover=round(untouched, 3),
        plate_waste=round(plate, 3),
        shortage=round(shortage, 3),
        excess_preparation=round(untouched, 3),
        forecast_error_abs=forecast_error_abs,
        forecast_error_pct=forecast_error_pct,
    )
    db.add(outcome)
    run.status = "finished"
    run.finished_at = datetime.now(timezone.utc)
    config["final_stock"] = round(float(config.get("stock", 0)), 3)
    run.config = _jsonable(config)
    db.flush()
    return _finish_response(db, run, outcome)


def _finish_response(db: Session, run: MealRun, outcome: Outcome) -> dict:
    events = list(
        db.scalars(
            select(SimulationEvent)
            .where(SimulationEvent.run_id == run.id)
            .order_by(SimulationEvent.interval_index)
        ).all()
    )
    interventions = list(
        db.scalars(
            select(Intervention)
            .where(Intervention.run_id == run.id)
            .order_by(Intervention.created_at)
        ).all()
    )
    return {
        "run": _run_out(run),
        "outcome": OutcomeOut.model_validate(outcome),
        "events": [SimulationEventOut.model_validate(item) for item in events],
        "interventions": [InterventionOut.model_validate(item) for item in interventions],
        "message": "Simulated service finished; outcomes and events are persisted.",
    }


def compare_policies(db: Session, request: SimulationCompareRequest) -> dict:
    realization = _build_realization(request)
    total_arrivals = sum(item["arrivals"] for item in realization)
    forecast_total = request.forecast_expected if request.forecast_expected is not None else total_arrivals
    forecast_source = (
        "supplied_forecast" if request.forecast_expected is not None else "realized_total_planning_proxy"
    )
    baseline_plan = _baseline_plan(request, forecast_total, realization)
    context_plan = _context_plan(request, realization, forecast_total)

    baseline_run = _create_run(
        db,
        request,
        BASELINE_POLICY_ID,
        realization,
        baseline_plan,
        forecast_total,
        forecast_source,
    )
    context_run = _create_run(
        db,
        request,
        CONTEXT_POLICY_ID,
        realization,
        context_plan,
        forecast_total,
        forecast_source,
    )
    for _ in range(baseline_run.intervals_total):
        step_simulation(db, baseline_run.id)
    for _ in range(context_run.intervals_total):
        step_simulation(db, context_run.id)
    baseline_finish = finish_simulation(db, baseline_run.id)
    context_finish = finish_simulation(db, context_run.id)
    return {
        "baseline_run": baseline_finish,
        "context_run": context_finish,
        "same_demand_realization": True,
        "seed": request.seed,
        "demand_realization": [float(item["arrivals"]) for item in realization],
        "caveat": (
            "Both policies used the identical synthetic arrival realization. This is a "
            "simulated planning comparison, not a real cafeteria outcome."
        ),
    }


def serialize_run(run: MealRun) -> SimulationRunOut:
    return _run_out(run)
