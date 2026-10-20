from __future__ import annotations

PAYLOAD = {
    "scenario_id": "synthetic_baseline_v1",
    "dataset_version": "1.0.0",
    "service_date": "2026-09-01",
    "meal_type": "breakfast",
    "dish_external_id": "D001",
    "seed": 11,
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
    "persist": True,
}


def _finish_run(client, payload):
    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200, response.text
    run_id = response.json()["id"]
    for _ in range(len(payload["intervals"])):
        assert client.post(f"/api/v1/simulations/{run_id}/step").status_code == 200
    finish = client.post(f"/api/v1/simulations/{run_id}/finish")
    assert finish.status_code == 200, finish.text
    return run_id, finish.json()


def test_evaluation_metrics_and_model_metrics_are_separate(client):
    run_id, _ = _finish_run(client, {**PAYLOAD, "policy": "baseline_fixed"})
    response = client.post(f"/api/v1/evaluation/runs/{run_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    metrics = body["metrics"]
    assert metrics["prepared_portions"] == 126
    assert metrics["served_portions"] == 100
    assert metrics["shortage_portions"] == 0
    assert metrics["waste_rate_per_prepared"] is not None
    assert body["denominators"]["prepared_total"] == 126
    assert "forecast_error_abs_portions" in body["model_metrics"]
    assert "note" in body["model_metrics"]
    assert "model" not in metrics

    latest = client.get(f"/api/v1/evaluation/runs/{run_id}/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == body["id"]


def test_evaluation_edge_case_zero_denominator(client):
    payload = {
        **PAYLOAD,
        "policy": "baseline_fixed",
        "capacity": 0,
        "forecast_expected": 0,
        "intervals": [
            {"interval_start": "07:00", "arrivals": 0},
            {"interval_start": "07:30", "arrivals": 0},
        ],
    }
    run_id, _ = _finish_run(client, payload)
    response = client.post(f"/api/v1/evaluation/runs/{run_id}")
    assert response.status_code == 200, response.text
    metrics = response.json()["metrics"]
    assert metrics["prepared_portions"] == 0
    assert metrics["waste_rate_per_prepared"] is None
    assert metrics["shortage_rate_per_demand"] is None
    assert metrics["interpretation_notes"]


def test_compare_evaluations_returns_deltas(client):
    baseline_response = client.post(
        "/api/v1/simulations/compare",
        json={**PAYLOAD, "plan": {"initial_qty": 40, "reserve_qty": 40, "trigger_qty": 20}},
    )
    assert baseline_response.status_code == 200, baseline_response.text
    body = baseline_response.json()
    baseline_id = body["baseline_run"]["run"]["id"]
    context_id = body["context_run"]["run"]["id"]
    comparison = client.post(
        "/api/v1/evaluation/compare",
        json={"baseline_run_id": baseline_id, "context_run_id": context_id, "persist": True},
    )
    assert comparison.status_code == 200, comparison.text
    result = comparison.json()
    assert result["baseline"]["run_id"] == baseline_id
    assert result["context"]["run_id"] == context_id
    assert "total_waste_portions" in result["deltas"]
    assert result["caveats"]


def test_feedback_is_logged_without_automatic_retraining(client):
    run_id, _ = _finish_run(client, {**PAYLOAD, "policy": "baseline_fixed"})
    response = client.post(
        "/api/v1/feedback",
        json={
            "run_id": run_id,
            "event_type": "operator_note",
            "payload": {"note": "Plate waste looked higher than expected."},
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["candidate_retraining"]["auto_retrain"] is False
    assert body["candidate_retraining"]["eligible_for_review"] is True

    listing = client.get("/api/v1/feedback", params={"run_id": run_id})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1


def test_json_and_csv_exports(client):
    run_id, _ = _finish_run(client, {**PAYLOAD, "policy": "baseline_fixed"})
    payload = client.get(f"/api/v1/exports/runs/{run_id}", params={"format": "json"})
    assert payload.status_code == 200
    body = payload.json()
    assert body["run"]["id"] == run_id
    assert body["outcome"]["prepared_total"] == 126
    assert len(body["events"]) == 4

    csv_response = client.get(f"/api/v1/exports/runs/{run_id}", params={"format": "csv"})
    assert csv_response.status_code == 200
    assert "text/csv" in csv_response.headers["content-type"]
    assert "record_type" in csv_response.text
    assert "interval_event" in csv_response.text
    assert "outcome" in csv_response.text
