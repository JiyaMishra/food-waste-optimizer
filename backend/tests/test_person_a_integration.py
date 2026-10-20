from __future__ import annotations

from datetime import date


def test_data_validation_and_sync(synced_client):
    validation = synced_client.post("/api/v1/data/validate")
    assert validation.status_code == 200
    assert validation.json()["ok"] is True

    menu = synced_client.get("/api/v1/menu/database")
    assert menu.status_code == 200
    dishes = menu.json()
    assert len(dishes) >= 9
    assert all(item["is_synthetic"] for item in dishes)


def test_context_and_availability_integration(synced_client):
    context = synced_client.get(
        "/api/v1/context", params={"date": "2026-09-01"}
    )
    assert context.status_code == 200
    body = context.json()
    assert body["occupied_count"] > 0
    assert body["source"] == "latest_available_context_proxy"
    assert body["caveats"]

    availability = synced_client.post(
        "/api/v1/context/availability",
        json={
            "date": "2026-09-01",
            "meal_type": "breakfast",
            "attendance_probability": 0.65,
            "academic_slots": [
                {"group_id": "H01_COHORT", "unavailable_share": 0.5}
            ],
            "group_sizes": {"H01_COHORT": 200},
            "persist": True,
        },
    )
    assert availability.status_code == 200
    result = availability.json()
    assert result["available_population"] <= result["occupied_population"]
    assert result["expected_arrivals"] >= 0
    assert result["snapshot_id"]
    assert any("conservative" in caveat.lower() for caveat in result["caveats"])

    snapshots = synced_client.get(
        "/api/v1/context/availability/snapshots", params={"date": "2026-09-01"}
    )
    assert snapshots.status_code == 200
    assert snapshots.json()["total"] >= 1


def test_forecast_uses_person_a_artifact(synced_client, generated_dataset):
    response = synced_client.post(
        "/api/v1/forecasts",
        json={"date": "2026-09-01", "meal_type": "breakfast", "persist": True},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rows"]
    assert body["model_version"] == generated_dataset["model"]["model_version"]
    assert body["feature_schema_version"] == generated_dataset["model"]["feature_schema_version"]
    assert body["forecast_cutoff"] == generated_dataset["model"]["training_cutoff"].isoformat()
    assert body["interval_is_calibrated"] is False
    for row in body["rows"]:
        assert row["lower_bound"] <= row["prediction"] <= row["upper_bound"]
        assert row["unit"] == "portions"
        assert row["is_synthetic"] is True

    persisted = synced_client.get(
        f"/api/v1/forecasts/runs/{body['forecast_run_id']}"
    )
    assert persisted.status_code == 200
    assert persisted.json()["total"] == len(body["rows"])


def test_forecast_rejects_date_at_or_before_cutoff(synced_client, generated_dataset):
    cutoff = generated_dataset["model"]["training_cutoff"]
    response = synced_client.post(
        "/api/v1/forecasts",
        json={"date": cutoff.isoformat(), "meal_type": "breakfast", "persist": False},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FORECAST_DATE_NOT_FUTURE"


def test_training_endpoint_returns_documented_metadata(synced_client):
    response = synced_client.post("/api/v1/forecasts/model/train")
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"]
    assert body["feature_schema_version"]
    assert body["training_cutoff"]
    assert body["validation_context_mae"] >= 0
