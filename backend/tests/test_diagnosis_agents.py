from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import func, select

from backend.app.agents.orchestrator import planning_workflow
from backend.app.core.errors import DomainError
from backend.app.db.models import AgentTrace
from backend.app.schemas.agents import PlanningWorkflowRequest


def test_pre_meal_diagnosis_returns_ranked_evidence(client):
    response = client.post(
        "/api/v1/diagnoses/pre-meal",
        json={
            "service_date": "2026-09-01",
            "meal_type": "breakfast",
            "forecasts": [
                {"dish_id": "D001", "prediction": 100, "lower_bound": 80, "upper_bound": 120},
                {"dish_id": "D002", "prediction": 50, "lower_bound": 40, "upper_bound": 60},
            ],
            "planned_quantities": [
                {"dish_id": "D001", "prepared_qty": 140},
            ],
            "historical_waste_rate": 0.12,
            "persist": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    by_dish = {item["dish_external_id"]: item for item in body}
    assert by_dish["D001"]["risk_score"] > 0
    assert by_dish["D001"]["causes"]
    assert by_dish["D001"]["causes"][0]["code"] == "over_preparation_risk"
    assert by_dish["D001"]["evidence"]
    assert by_dish["D001"]["llm_used"] is False
    assert by_dish["D002"]["risk_score"] == 0
    assert any("planned prepared quantity" in caveat.lower() for caveat in by_dish["D002"]["caveats"])


def test_post_meal_diagnosis_uses_persisted_outcome(client):
    payload = {
        "scenario_id": "synthetic_baseline_v1",
        "dataset_version": "1.0.0",
        "service_date": "2026-09-01",
        "meal_type": "breakfast",
        "dish_external_id": "D001",
        "seed": 7,
        "service_start": "07:00",
        "intervals": [
            {"interval_start": "07:00", "arrivals": 20},
            {"interval_start": "07:30", "arrivals": 30},
            {"interval_start": "08:00", "arrivals": 30},
            {"interval_start": "08:30", "arrivals": 20},
        ],
        "current_stock": 0,
        "capacity": 200,
        "batch_min": 10,
        "batch_max": 200,
        "consumption_rate": 0.8,
        "prep_lead_intervals": 1,
        "forecast_expected": 120,
        "policy": "baseline_fixed",
        "persist": True,
    }
    start = client.post("/api/v1/simulations", json=payload)
    assert start.status_code == 200, start.text
    run_id = start.json()["id"]
    for _ in range(4):
        assert client.post(f"/api/v1/simulations/{run_id}/step").status_code == 200
    finish = client.post(f"/api/v1/simulations/{run_id}/finish")
    assert finish.status_code == 200

    diagnosis = client.post(
        "/api/v1/diagnoses/post-meal",
        json={"run_id": run_id, "persist": True},
    )
    assert diagnosis.status_code == 200, diagnosis.text
    body = diagnosis.json()
    codes = {cause["code"] for cause in body["causes"]}
    assert "over_preparation" in codes
    assert body["evidence"]
    assert body["llm_used"] is False
    assert any("correlation" in caveat.lower() for caveat in body["caveats"])
    assert body["id"]


def test_planning_workflow_produces_traceable_stage_sequence(synced_client):
    response = synced_client.post(
        "/api/v1/agents/planning",
        json={
            "service_date": "2026-09-01",
            "meal_type": "breakfast",
            "hostel_id": "H01",
            "mess_id": "M01",
            "attendance_probability": 0.65,
            "current_stock": 0,
            "batch_min": 20,
            "batch_max": 500,
            "kitchen_capacity": 500,
            "prep_lead_minutes": 30,
            "service_start": "07:00",
            "service_close": "10:00",
            "persist": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert [stage["stage"] for stage in body["stages"]] == [
        "context_observation",
        "availability_estimate",
        "demand_forecast",
        "constrained_planning",
        "pre_meal_diagnosis",
    ]
    assert all(stage["status"] == "completed" for stage in body["stages"])
    assert body["forecast_run_id"]
    assert body["plan_id"]
    assert body["diagnosis_id"]
    assert body["requires_human_approval"] is True

    traces = synced_client.get(
        "/api/v1/agents/traces", params={"trace_id": body["trace_id"]}
    )
    assert traces.status_code == 200
    assert traces.json()["total"] == 5

    exported = synced_client.get(
        "/api/v1/exports/agent-traces",
        params={"trace_id": body["trace_id"], "format": "csv"},
    )
    assert exported.status_code == 200
    assert "text/csv" in exported.headers["content-type"]
    assert "trace_id" in exported.text


def test_invalid_agent_output_is_rejected_and_traced(
    synced_client, db_session, monkeypatch
):
    import backend.app.agents.kitchen_agent as kitchen_agent

    def invalid_plan(db, request):
        return {"initial_quantity": -5}

    monkeypatch.setattr(kitchen_agent, "run", invalid_plan)
    request = PlanningWorkflowRequest(
        service_date=date(2026, 9, 1),
        meal_type="breakfast",
        hostel_id="H01",
        mess_id="M01",
        current_stock=0,
        batch_min=20,
        batch_max=500,
        kitchen_capacity=500,
        prep_lead_minutes=30,
    )
    with pytest.raises(DomainError) as exc:
        planning_workflow(db_session, request)
    assert exc.value.code == "AGENT_OUTPUT_REJECTED"

    rejected = db_session.scalar(
        select(func.count())
        .select_from(AgentTrace)
        .where(AgentTrace.status == "rejected")
    )
    assert rejected and rejected >= 1


def test_planning_workflow_lunch_and_dinner(synced_client):
    """Verify orchestrator dynamically adapts service windows for lunch and dinner."""
    for meal in ("lunch", "dinner"):
        resp = synced_client.post(
            "/api/v1/agents/planning",
            json={
                "service_date": "2026-09-01",
                "meal_type": meal,
                "hostel_id": "H01",
                "mess_id": "M01",
                "attendance_probability": 0.65,
                "current_stock": 0,
                "batch_min": 20,
                "batch_max": 500,
                "kitchen_capacity": 500,
                "prep_lead_minutes": 30,
                "persist": True,
            },
        )
        assert resp.status_code == 200, f"Planning workflow failed for {meal}: {resp.text}"
        body = resp.json()
        assert body["status"] == "completed"
        assert len(body["stages"]) == 5
