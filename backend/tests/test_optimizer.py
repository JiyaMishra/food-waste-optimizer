from __future__ import annotations

from datetime import date, datetime, time

import pytest
from pydantic import ValidationError

from backend.app.schemas.plan import IntervalDemand, OptimizerRequest, OptimizerWeights
from backend.app.services.optimizer import optimize


def make_request(**overrides):
    values = {
        "service_date": date(2026, 9, 1),
        "meal_type": "breakfast",
        "dish_external_id": "D001",
        "intervals": [
            IntervalDemand(interval_start=time(7, 0), expected=40, lower=30, upper=50),
            IntervalDemand(interval_start=time(7, 30), expected=50, lower=40, upper=60),
            IntervalDemand(interval_start=time(8, 0), expected=45, lower=35, upper=55),
            IntervalDemand(interval_start=time(8, 30), expected=35, lower=25, upper=45),
        ],
        "current_stock": 10,
        "batch_min": 20,
        "batch_max": 200,
        "kitchen_capacity": 300,
        "prep_lead_minutes": 30,
        "service_start": time(7, 0),
        "service_close": time(10, 0),
        "now": datetime(2026, 9, 1, 5, 0),
        "persist": False,
    }
    values.update(overrides)
    return OptimizerRequest(**values)


def test_optimizer_respects_batch_capacity_and_non_negative_constraints():
    result = optimize(make_request())
    assert result["initial_quantity"] >= 0
    assert result["reserve_quantity"] >= 0
    assert result["replenishment_trigger"] >= 0
    assert result["initial_quantity"] == 0 or (
        result["batch_min"] <= result["initial_quantity"] <= result["batch_max"]
    )
    assert result["reserve_quantity"] == 0 or (
        result["batch_min"] <= result["reserve_quantity"] <= result["batch_max"]
    )
    assert result["initial_quantity"] + result["reserve_quantity"] <= result["capacity_total"]
    checks = {check["name"]: check for check in result["constraint_checks"]}
    assert checks["non_negative_quantities"]["ok"] is True
    assert checks["kitchen_capacity"]["ok"] is True
    assert checks["initial_batch_bounds"]["ok"] is True
    assert checks["reserve_batch_bounds"]["ok"] is True
    assert checks["safe_availability_floor"]["ok"] is True
    assert result["requires_human_approval"] is True
    assert result["simulation_only"] is True


def test_optimizer_holds_reserve_when_lead_time_cannot_finish_before_close():
    result = optimize(
        make_request(
            now=datetime(2026, 9, 1, 9, 45),
            prep_lead_minutes=60,
        )
    )
    assert result["reserve_quantity"] == 0
    checks = {check["name"]: check for check in result["constraint_checks"]}
    assert checks["replenishment_lead_time"]["ok"] is True


def test_optimizer_respects_tight_capacity():
    result = optimize(make_request(kitchen_capacity=30, batch_max=200))
    assert result["initial_quantity"] + result["reserve_quantity"] <= 30
    assert result["reserve_quantity"] == 0 or result["reserve_quantity"] >= 20


def test_optimizer_rejects_invalid_service_window():
    with pytest.raises(ValidationError):
        make_request(service_start=time(10, 0), service_close=time(9, 0))


def test_optimizer_shortage_sensitivity():
    low = optimize(make_request(weights=OptimizerWeights(shortage=1.0)))
    high = optimize(make_request(weights=OptimizerWeights(shortage=50.0)))
    assert high["expected_shortage"] <= low["expected_shortage"] + 1e-9


def test_optimizer_persists_plan(db_session):
    result = optimize(make_request(persist=True), db=db_session)
    db_session.commit()
    assert result["plan_id"]
    from backend.app.db.models import BatchPlan

    row = db_session.get(BatchPlan, result["plan_id"])
    assert row is not None
    assert row.expected_leftover == result["expected_leftover"]
    assert row.expected_shortage == result["expected_shortage"]
