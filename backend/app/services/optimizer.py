"""Deterministic constrained batch optimizer.

The optimizer never asks an LLM to perform arithmetic or override constraints.
It enumerates batch-feasible quantities and evaluates a documented weighted
objective. A plan is a proposal only; live kitchen action requires human
approval and the prototype executes simulation actions only.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.db.models import BatchPlan
from backend.app.schemas.plan import BatchPlanOut, ConstraintCheck, OptimizerRequest

POLICY_VERSION = "split-batch-v1"


def _ceil_to(value: float, step: float) -> float:
    if step <= 0:
        return float(value)
    return math.ceil(max(0.0, value) / step) * step


def _round(value: float) -> float:
    return round(float(value), 3)


def _naive(value: datetime) -> datetime:
    return value.replace(tzinfo=None) if value.tzinfo is not None else value


def _lead_window_demand(request: OptimizerRequest) -> float:
    start = datetime.combine(request.service_date, request.service_start)
    cutoff = start + timedelta(minutes=request.prep_lead_minutes)
    total = 0.0
    for interval in request.intervals:
        interval_dt = datetime.combine(request.service_date, interval.interval_start)
        if interval_dt < cutoff:
            total += float(interval.expected)
    return total


def _evaluate_candidate(
    initial: float,
    reserve: float,
    trigger: float,
    request: OptimizerRequest,
    lower: float,
    expected: float,
    upper: float,
    reserve_feasible: bool,
    initial_feasible: bool,
) -> dict:
    scenarios = ((lower, 0.25), (expected, 0.50), (upper, 0.25))
    weights = request.weights
    expected_leftover = 0.0
    expected_shortage = 0.0
    use_probability = 0.0
    for demand, probability in scenarios:
        base_supply = request.current_stock + initial
        use_reserve = reserve if demand > max(0.0, base_supply - trigger) else 0.0
        supply = base_supply + use_reserve
        expected_leftover += probability * max(0.0, supply - demand)
        expected_shortage += probability * max(0.0, demand - supply)
        use_probability += probability * (1.0 if use_reserve > 0 else 0.0)
    prepared = initial + reserve * use_probability
    batch_changes = 1.0 if reserve > 0 else 0.0
    objective = (
        weights.leftover * expected_leftover
        + weights.shortage * expected_shortage
        + weights.prep_cost * prepared
        + weights.batch_change * batch_changes
    )

    checks = [
        ConstraintCheck(
            name="non_negative_quantities",
            ok=initial >= 0 and reserve >= 0 and trigger >= 0,
            detail="initial, reserve and trigger must be non-negative",
        ),
        ConstraintCheck(
            name="initial_batch_bounds",
            ok=initial == 0
            or (request.batch_min <= initial <= request.batch_max),
            detail=(
                f"initial is 0 or within [{request.batch_min}, {request.batch_max}]"
            ),
        ),
        ConstraintCheck(
            name="reserve_batch_bounds",
            ok=reserve == 0 or (request.batch_min <= reserve <= request.batch_max),
            detail=f"reserve is 0 or within [{request.batch_min}, {request.batch_max}]",
        ),
        ConstraintCheck(
            name="kitchen_capacity",
            ok=initial + reserve <= request.kitchen_capacity,
            detail=(
                f"initial + reserve ({_round(initial + reserve)}) <= capacity "
                f"({request.kitchen_capacity})"
            ),
        ),
        ConstraintCheck(
            name="replenishment_lead_time",
            ok=reserve == 0 or reserve_feasible,
            detail=(
                "no reserve requested"
                if reserve == 0
                else "reserve must finish before service close"
            ),
        ),
        ConstraintCheck(
            name="initial_preparation_window",
            ok=initial == 0 or initial_feasible,
            detail=(
                "no initial batch requested"
                if initial == 0
                else "initial batch must finish before service start"
            ),
        ),
        ConstraintCheck(
            name="safe_availability_floor",
            ok=request.current_stock + initial + reserve >= lower,
            detail=(
                "planned supply covers the lower demand bound where feasible; "
                "the plan is never reduced to zero while demand exists"
            ),
        ),
    ]
    return {
        "initial": initial,
        "reserve": reserve,
        "trigger": trigger,
        "expected_leftover": expected_leftover,
        "expected_shortage": expected_shortage,
        "expected_prepared": prepared,
        "objective": objective,
        "checks": checks,
        "safe_availability": all(check.ok for check in checks),
    }


def optimize(request: OptimizerRequest, db: Session | None = None) -> dict:
    lower = sum(float(interval.lower) for interval in request.intervals)
    expected = sum(float(interval.expected) for interval in request.intervals)
    upper = sum(float(interval.upper) for interval in request.intervals)

    now = _naive(request.now) if request.now else (
        datetime.combine(request.service_date, request.service_start)
        - timedelta(minutes=request.prep_lead_minutes + 1)
    )
    service_start = datetime.combine(request.service_date, request.service_start)
    service_close = datetime.combine(request.service_date, request.service_close)
    initial_feasible = now + timedelta(minutes=request.prep_lead_minutes) <= service_start
    reserve_feasible = now + timedelta(minutes=request.prep_lead_minutes) <= service_close

    max_initial = min(request.batch_max, request.kitchen_capacity)
    initial_candidates: set[float] = {0.0}
    if request.current_stock < expected:
        initial_candidates.add(min(max_initial, request.batch_min))
    for target in (lower - request.current_stock, expected - request.current_stock,
                   upper - request.current_stock):
        value = min(max_initial, _ceil_to(target, request.batch_min))
        if value > 0:
            initial_candidates.add(value)
    initial_candidates.add(max_initial)

    trigger_base = _lead_window_demand(request)
    if trigger_base <= 0:
        trigger_base = max(0.0, expected * 0.35)
    trigger = _round(min(expected, trigger_base + 0.25 * max(0.0, upper - lower)))

    candidates: list[dict] = []
    for initial in sorted(initial_candidates):
        if initial < 0 or initial > request.batch_max or initial > request.kitchen_capacity:
            continue
        if initial > 0 and initial < request.batch_min:
            continue
        remaining_capacity = max(0.0, request.kitchen_capacity - initial)
        reserve_candidates: set[float] = {0.0}
        if remaining_capacity >= request.batch_min and reserve_feasible:
            need = upper - request.current_stock - initial
            if need > 0:
                reserve_candidates.add(
                    min(request.batch_max, remaining_capacity, _ceil_to(need, request.batch_min))
                )
            reserve_candidates.add(min(request.batch_max, remaining_capacity))
        for reserve in sorted(reserve_candidates):
            if reserve < 0 or reserve > request.batch_max:
                continue
            if reserve > 0 and reserve < request.batch_min:
                continue
            if initial + reserve > request.kitchen_capacity:
                continue
            candidate = _evaluate_candidate(
                initial,
                reserve,
                trigger if reserve > 0 else 0.0,
                request,
                lower,
                expected,
                upper,
                reserve_feasible,
                initial_feasible,
            )
            candidates.append(candidate)

    if not candidates:
        zero = _evaluate_candidate(
            0.0, 0.0, 0.0, request, lower, expected, upper, reserve_feasible, initial_feasible
        )
        zero["objective"] = float("inf")
        candidates = [zero]

    safe = [item for item in candidates if item["safe_availability"]]
    pool = safe if safe else candidates
    best = min(pool, key=lambda item: (item["objective"], item["expected_shortage"]))

    checks = [check.model_dump() for check in best["checks"] if check.name != "safe_availability_floor"]
    checks.append(
        ConstraintCheck(
            name="safe_availability_floor",
            ok=best["checks"][-1].ok,
            detail=best["checks"][-1].detail,
        ).model_dump()
    )
    feasible = all(check["ok"] for check in checks)
    if feasible and not initial_feasible and best["initial"] == 0:
        feasible = True
    rationale_parts = [
        f"enumerated {len(candidates)} batch-feasible plans",
        (
            f"selected initial={_round(best['initial'])} and reserve={_round(best['reserve'])} "
            f"to balance expected leftover={_round(best['expected_leftover'])}, "
            f"expected shortage={_round(best['expected_shortage'])}, prep cost and batch changes"
        ),
        "shortage is weighted above leftover by default to protect food availability",
    ]
    if not reserve_feasible:
        rationale_parts.append("reserve held at zero because preparation cannot finish before close")
    if not initial_feasible:
        rationale_parts.append("initial batch flagged infeasible for the current preparation window")
    if not safe:
        rationale_parts.append("no candidate could cover the full lower demand bound")
    rationale = "; ".join(rationale_parts) + "."

    plan_id = None
    if request.persist and db is not None:
        row = BatchPlan(
            run_id=request.run_id,
            forecast_run_id=request.forecast_run_id,
            service_date=request.service_date,
            meal_type=request.meal_type,
            dish_external_id=request.dish_external_id,
            initial_qty=_round(best["initial"]),
            reserve_qty=_round(best["reserve"]),
            trigger_qty=_round(best["trigger"]),
            batch_min=request.batch_min,
            batch_max=request.batch_max,
            capacity_total=request.kitchen_capacity,
            capacity_remaining=_round(
                request.kitchen_capacity - best["initial"] - best["reserve"]
            ),
            lead_time_minutes=request.prep_lead_minutes,
            service_close=request.service_close,
            expected_leftover=_round(best["expected_leftover"]),
            expected_shortage=_round(best["expected_shortage"]),
            expected_prepared=_round(best["expected_prepared"]),
            objective_value=_round(best["objective"]),
            weights=request.weights.model_dump(),
            rationale=rationale,
            capacity_check={"checks": checks},
            uncertainty={
                "demand_lower": _round(lower),
                "demand_expected": _round(expected),
                "demand_upper": _round(upper),
                "reserve_trigger_model": "remaining stock threshold",
                "reserve_use_probability_note": "scenario-weighted approximation",
            },
            approval_state="proposed",
            policy_version=request.policy_version,
            model_version=request.model_version,
            is_synthetic=True,
        )
        db.add(row)
        db.flush()
        plan_id = row.id

    response = BatchPlanOut(
        plan_id=plan_id,
        service_date=request.service_date,
        meal_type=request.meal_type,
        dish_external_id=request.dish_external_id,
        initial_quantity=_round(best["initial"]),
        reserve_quantity=_round(best["reserve"]),
        replenishment_trigger=_round(best["trigger"]),
        batch_min=request.batch_min,
        batch_max=request.batch_max,
        capacity_total=request.kitchen_capacity,
        capacity_remaining=_round(
            request.kitchen_capacity - best["initial"] - best["reserve"]
        ),
        lead_time_minutes=request.prep_lead_minutes,
        service_close=request.service_close,
        expected_leftover=_round(best["expected_leftover"]),
        expected_shortage=_round(best["expected_shortage"]),
        expected_prepared=_round(best["expected_prepared"]),
        objective_value=_round(best["objective"]),
        weights=request.weights.model_dump(),
        rationale=rationale,
        constraint_checks=checks,
        uncertainty={
            "demand_lower": _round(lower),
            "demand_expected": _round(expected),
            "demand_upper": _round(upper),
            "reserve_trigger_model": "remaining stock threshold",
            "reserve_use_probability_note": "scenario-weighted approximation",
        },
        approval_state="proposed",
        policy_version=request.policy_version,
        model_version=request.model_version,
    )
    return response.model_dump()
