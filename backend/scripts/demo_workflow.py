"""Reproducible end-to-end demo against the FastAPI app (no server required).

Run from the repository root after applying migrations:
    alembic -c backend/alembic.ini upgrade head
    python backend/scripts/demo_workflow.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.main import app

SERVICE_DATE = "2026-09-01"
HISTORICAL_DATE = "2026-08-31"
MEAL = "breakfast"


def show(label: str, response) -> dict:
    print(f"\n[{label}] HTTP {response.status_code}")
    try:
        body = response.json()
    except Exception:
        body = {"raw": response.text[:500]}
    print(json.dumps(body, indent=2, default=str)[:1200])
    if response.status_code >= 400:
        raise SystemExit(f"Demo failed at {label}: {response.text}")
    return body


def main() -> None:
    with TestClient(app) as client:
        show("health", client.get("/health"))
        show("readiness", client.get("/ready"))

        generated = show(
            "generate synthetic data",
            client.post(
                "/api/v1/data/generate",
                json={"months": 2, "seed": 42, "residents": 200, "validate_after": True},
            ),
        )
        show("sync synthetic data", client.post("/api/v1/data/sync"))
        show("sync menu catalogue", client.post("/api/v1/menu/sync"))
        show(
            "train demand model",
            client.post("/api/v1/forecasts/model/train"),
        )
        show(
            "context",
            client.get("/api/v1/context", params={"date": SERVICE_DATE, "hostel_id": "H01"}),
        )
        show(
            "availability",
            client.post(
                "/api/v1/context/availability",
                json={
                    "date": SERVICE_DATE,
                    "meal_type": MEAL,
                    "hostel_id": "H01",
                    "mess_id": "M01",
                    "attendance_probability": 0.65,
                    "academic_slots": [{"group_id": "H01_COHORT", "unavailable_share": 0.4}],
                    "group_sizes": {"H01_COHORT": 200},
                    "persist": True,
                },
            ),
        )
        forecast = show(
            "forecast",
            client.post(
                "/api/v1/forecasts",
                json={"date": SERVICE_DATE, "meal_type": MEAL, "persist": True},
            ),
        )
        dish_forecast = forecast["rows"][0]
        show(
            "batch plan",
            client.post(
                "/api/v1/plans",
                json={
                    "service_date": SERVICE_DATE,
                    "meal_type": MEAL,
                    "dish_external_id": dish_forecast["dish_id"],
                    "intervals": [
                        {
                            "interval_start": "07:00",
                            "expected": dish_forecast["prediction"] * 0.2,
                            "lower": dish_forecast["lower_bound"] * 0.2,
                            "upper": dish_forecast["upper_bound"] * 0.2,
                        },
                        {
                            "interval_start": "07:30",
                            "expected": dish_forecast["prediction"] * 0.3,
                            "lower": dish_forecast["lower_bound"] * 0.3,
                            "upper": dish_forecast["upper_bound"] * 0.3,
                        },
                        {
                            "interval_start": "08:00",
                            "expected": dish_forecast["prediction"] * 0.3,
                            "lower": dish_forecast["lower_bound"] * 0.3,
                            "upper": dish_forecast["upper_bound"] * 0.3,
                        },
                        {
                            "interval_start": "08:30",
                            "expected": dish_forecast["prediction"] * 0.2,
                            "lower": dish_forecast["lower_bound"] * 0.2,
                            "upper": dish_forecast["upper_bound"] * 0.2,
                        },
                    ],
                    "current_stock": 0,
                    "batch_min": 20,
                    "batch_max": 500,
                    "kitchen_capacity": 500,
                    "prep_lead_minutes": 30,
                    "service_start": "07:00",
                    "service_close": "10:00",
                    "forecast_run_id": forecast["forecast_run_id"],
                    "model_version": forecast["model_version"],
                    "persist": True,
                },
            ),
        )

        comparison = show(
            "simulate baseline vs context-aware",
            client.post(
                "/api/v1/simulations/compare",
                json={
                    "scenario_id": "synthetic_baseline_v1",
                    "dataset_version": generated["dataset_version"],
                    "service_date": SERVICE_DATE,
                    "meal_type": MEAL,
                    "dish_external_id": dish_forecast["dish_id"],
                    "seed": 42,
                    "service_start": "07:00",
                    "use_historical": True,
                    "historical_date": HISTORICAL_DATE,
                    "current_stock": 0,
                    "capacity": 500,
                    "batch_min": 20,
                    "batch_max": 500,
                    "consumption_rate": 0.85,
                    "prep_lead_intervals": 1,
                    "forecast_expected": dish_forecast["prediction"],
                    "forecast_run_id": forecast["forecast_run_id"],
                    "model_version": forecast["model_version"],
                    "persist": True,
                },
            ),
        )
        baseline_id = comparison["baseline_run"]["run"]["id"]
        context_id = comparison["context_run"]["run"]["id"]
        show("evaluate baseline", client.post(f"/api/v1/evaluation/runs/{baseline_id}"))
        show("evaluate context", client.post(f"/api/v1/evaluation/runs/{context_id}"))
        show(
            "compare evaluations",
            client.post(
                "/api/v1/evaluation/compare",
                json={"baseline_run_id": baseline_id, "context_run_id": context_id},
            ),
        )

        planning = show(
            "agent planning workflow",
            client.post(
                "/api/v1/agents/planning",
                json={
                    "service_date": SERVICE_DATE,
                    "meal_type": MEAL,
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
            ),
        )
        show("agent traces", client.get("/api/v1/agents/traces", params={"trace_id": planning["trace_id"]}))
        show(
            "agent review workflow",
            client.post("/api/v1/agents/review", json={"run_id": context_id, "persist": True}),
        )
        show("run export JSON", client.get(f"/api/v1/exports/runs/{context_id}"))
        csv_response = client.get(f"/api/v1/exports/runs/{context_id}", params={"format": "csv"})
        print(f"\n[CSV export] HTTP {csv_response.status_code}, bytes={len(csv_response.text)}")
        print(csv_response.text[:800])

        print("\nDemo completed successfully.")
        print(f"baseline_run_id={baseline_id}")
        print(f"context_run_id={context_id}")
        print(f"forecast_run_id={forecast['forecast_run_id']}")
        print(f"planning_trace_id={planning['trace_id']}")


if __name__ == "__main__":
    main()
