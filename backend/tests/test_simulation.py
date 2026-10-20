from __future__ import annotations

BASE_PAYLOAD = {
    "scenario_id": "synthetic_baseline_v1",
    "dataset_version": "1.0.0",
    "service_date": "2026-09-01",
    "meal_type": "breakfast",
    "dish_external_id": "D001",
    "seed": 7,
    "service_start": "07:00",
    "intervals": [
        {"interval_start": "07:00", "arrivals": 10},
        {"interval_start": "07:30", "arrivals": 20},
        {"interval_start": "08:00", "arrivals": 30},
        {"interval_start": "08:30", "arrivals": 40},
    ],
    "current_stock": 0,
    "capacity": 100,
    "batch_min": 10,
    "batch_max": 60,
    "consumption_rate": 0.8,
    "prep_lead_intervals": 1,
    "persist": True,
}


def _start(client, policy, plan=None):
    payload = {**BASE_PAYLOAD, "policy": policy}
    if plan:
        payload["plan"] = plan
    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _step_all(client, run_id, count=4):
    results = []
    for _ in range(count):
        response = client.post(f"/api/v1/simulations/{run_id}/step")
        assert response.status_code == 200, response.text
        results.append(response.json())
    return results


def test_baseline_policy_runs_to_completion(client):
    run = _start(client, "baseline_fixed")
    assert run["status"] == "running"
    steps = _step_all(client, run["id"])
    assert steps[-1]["run"]["current_interval"] == 4
    finish = client.post(f"/api/v1/simulations/{run['id']}/finish")
    assert finish.status_code == 200, finish.text
    outcome = finish.json()["outcome"]
    assert outcome["prepared_total"] == 100
    assert outcome["served_total"] == 100
    assert outcome["shortage"] == 0
    assert outcome["untouched_leftover"] == 0
    assert outcome["plate_waste"] == 20
    assert outcome["consumed_total"] == 80


def test_context_policy_triggers_reserve_and_persists_interventions(client):
    run = _start(
        client,
        "context_aware_split",
        plan={"initial_qty": 40, "reserve_qty": 20, "trigger_qty": 10},
    )
    steps = _step_all(client, run["id"])
    actions = [step["event"]["action"] for step in steps]
    assert "reserve_scheduled" in actions
    assert "reserve_added" in actions
    finish = client.post(f"/api/v1/simulations/{run['id']}/finish")
    assert finish.status_code == 200, finish.text
    body = finish.json()
    outcome = body["outcome"]
    assert outcome["prepared_total"] == 60
    assert outcome["served_total"] == 60
    assert outcome["shortage"] == 40
    assert outcome["untouched_leftover"] == 0
    assert outcome["plate_waste"] == 12
    statuses = {item["status"] for item in body["interventions"]}
    assert "simulated" in statuses
    simulated = [
        item for item in body["interventions"] if item["action_type"] == "replenish_reserve"
    ]
    assert simulated
    assert simulated[0]["detail_json"]["simulation_only"] is True


def test_step_and_finish_transition_guards(client):
    run = _start(client, "baseline_fixed")
    early = client.post(f"/api/v1/simulations/{run['id']}/finish")
    assert early.status_code == 409
    assert early.json()["error"]["code"] == "SIMULATION_NOT_COMPLETE"

    _step_all(client, run["id"])
    finish = client.post(f"/api/v1/simulations/{run['id']}/finish")
    assert finish.status_code == 200
    again = client.post(f"/api/v1/simulations/{run['id']}/step")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "RUN_ALREADY_FINISHED"


def test_compare_policies_uses_same_demand_realization(client):
    response = client.post("/api/v1/simulations/compare", json=BASE_PAYLOAD)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["same_demand_realization"] is True
    assert body["seed"] == BASE_PAYLOAD["seed"]
    assert sum(body["demand_realization"]) == 100
    baseline = body["baseline_run"]
    context = body["context_run"]
    assert baseline["run"]["status"] == "finished"
    assert context["run"]["status"] == "finished"
    assert baseline["run"]["config"]["forecast_expected"] == context["run"]["config"]["forecast_expected"]
    assert baseline["outcome"]["shortage"] >= 0
    assert context["outcome"]["shortage"] >= 0


def test_zero_demand_run_produces_zero_prepared_outcome(client):
    payload = {
        **BASE_PAYLOAD,
        "policy": "baseline_fixed",
        "capacity": 0,
        "forecast_expected": 0,
        "intervals": [
            {"interval_start": "07:00", "arrivals": 0},
            {"interval_start": "07:30", "arrivals": 0},
        ],
    }
    response = client.post("/api/v1/simulations", json=payload)
    assert response.status_code == 200, response.text
    run_id = response.json()["id"]
    _step_all(client, run_id, count=2)
    finish = client.post(f"/api/v1/simulations/{run_id}/finish")
    assert finish.status_code == 200
    outcome = finish.json()["outcome"]
    assert outcome["prepared_total"] == 0
    assert outcome["served_total"] == 0
    assert outcome["shortage"] == 0
