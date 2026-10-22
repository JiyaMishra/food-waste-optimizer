from __future__ import annotations


def test_health_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["synthetic_only"] is True
    assert response.headers["x-request-id"]


def test_menu_retrieval(client):
    response = client.get("/api/v1/menu")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(body["items"])
    assert body["count"] >= 9
    assert body["items"][0]["external_id"].startswith("D")
    assert body["items"][0]["is_synthetic"] is True


def test_validation_error_shape(client):
    response = client.post("/api/v1/data/generate", json={"months": 0, "seed": 1})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["message"] == "Request validation failed"
    assert body["error"]["request_id"] == response.headers["x-request-id"]
    assert isinstance(body["error"]["details"], list)


def test_domain_error_shape(client):
    response = client.get("/api/v1/simulations/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "RUN_NOT_FOUND"
    assert body["error"]["request_id"] == response.headers["x-request-id"]


def test_openapi_exposes_required_endpoints(client):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    required = [
        "/api/v1/menu",
        "/api/v1/data/generate",
        "/api/v1/context",
        "/api/v1/context/availability",
        "/api/v1/forecasts",
        "/api/v1/plans",
        "/api/v1/simulations",
        "/api/v1/simulations/{run_id}/step",
        "/api/v1/simulations/{run_id}/finish",
        "/api/v1/evaluation/runs/{run_id}",
        "/api/v1/agents/traces",
        "/api/v1/diagnoses/pre-meal",
        "/api/v1/diagnoses/post-meal",
        "/api/v1/exports/runs/{run_id}",
    ]
    for path in required:
        assert path in paths, f"missing OpenAPI path {path}"


def test_readiness_reports_checks(client):
    response = client.get("/ready")
    assert response.status_code in (200, 503)
    body = response.json()
    names = {item["name"] for item in body["checks"]}
    assert {"database", "person_a_modules", "menu_seed", "synthetic_dataset", "model_artifact"} <= names
