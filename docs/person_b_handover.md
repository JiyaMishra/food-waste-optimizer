# Person B → Person C handover

## Status

Person B's backend is implemented on branch `person-b` and builds on Person A's `main`
deliverables. Person A's data generator, validator, availability calculator, feature builder and
model training/evaluation code are imported, not copied.

All records, forecasts, diagnoses and outcomes are **synthetic**. Do not present them as real VIT
measurements or real cafeteria performance. The prototype performs simulation actions only; it
never executes a live kitchen action.

## What is delivered

- FastAPI app with validated Pydantic contracts, OpenAPI docs, consistent errors and request IDs.
- SQLAlchemy models and an Alembic migration from an empty database.
- PostgreSQL support through `DATABASE_URL` and `psycopg`; SQLite fallback for local development.
- Person A integration: synthetic generation, validation, availability, feature schema and model
  artifact inference.
- Pre-meal waste-risk estimates and post-meal evidence-based diagnosis with uncertainty/caveats.
- Typed agent modules and a master orchestrator with persisted stage traces.
- Deterministic constrained batch optimizer with explicit objective weights.
- Meal-service simulator comparing fixed baseline and context-aware split-batch policies on the
  same synthetic demand realization.
- Persisted outcomes separating untouched leftovers, plate waste and shortage.
- Evaluation metrics with separate model-forecast metrics, plus feedback/candidate-retraining
  metadata (no automatic retraining).
- JSON/CSV exports and a reproducible end-to-end demo.

## Person A integration contract

| Concern | Person A entry point | Backend usage |
|---|---|---|
| Synthetic data | `generate_synthetic_data(output_dir, months, seed, residents)` | `services/data_service.generate_dataset` |
| Validation | `validate_dataset(data_dir)` | generation and `/data/validate` |
| Availability | `calculate_availability(context, academic_slots, groups)` | `/context/availability`, availability agent |
| Features | `build_features(operations, forecast_cutoff)` | training endpoint |
| Model training/selection | `train_model(features, artifact_path)` | `/forecasts/model/train` |
| Model artifact | `ml/artifacts/context_model.joblib` | `/forecasts` inference |
| Forecast contract | date, meal_type, dish_id, prediction, bounds, model/cutoff/schema versions, units | `/forecasts` response |

The artifact is gitignored. If it is missing, forecasting returns `503 MODEL_ARTIFACT_MISSING`
with the training remedy. Forecast dates at or before the training cutoff return
`422 FORECAST_DATE_NOT_FUTURE`.

Generated timetables do not declare per-group `unavailable_share`; academic unavailability is only
applied when explicit slots are supplied. Event and academic unavailability can overlap, so
Person A's conservative `max()` union is retained.

## Database model

| Table | Purpose |
|---|---|
| `dishes`, `menu_items` | Catalogue and persisted menu snapshots |
| `synthetic_context`, `academic_slots` | Synthetic occupancy/weather/event/timetable context |
| `availability_snapshots` | Append-only availability estimates |
| `meal_runs`, `simulation_events` | Policy run and interval-by-interval state |
| `outcomes` | Served/consumed, untouched leftovers, plate waste, shortage, excess prep |
| `predictions` | Append-only dish forecasts grouped by `forecast_run_id` |
| `batch_plans` | Initial/reserve quantities, trigger, weights, checks, uncertainty |
| `agent_traces` | Stage input/output summaries, tool calls, duration, status, errors |
| `diagnoses` | Risk/confidence, ranked causes, evidence, caveats, sources |
| `interventions` | Scheduled/simulated/cancelled reserve actions (never live) |
| `evaluation_runs` | Persisted policy metrics and separate model metrics |
| `feedback_events` | Observations and candidate-retraining metadata |

Run records carry `scenario_id`, `dataset_version`, `seed`, `policy_id`, `policy_version` and,
when available, `model_version`/`forecast_run_id`. Predictions are never overwritten.

## Local setup and migration

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements.txt
alembic -c backend/alembic.ini upgrade head
uvicorn backend.app.main:app --reload --port 8000
```

If using PostgreSQL, set:

```dotenv
DATABASE_URL=postgresql+psycopg://user:password@host:5432/food_optimizer
```

Then run `alembic -c backend/alembic.ini upgrade head` against that instance.

Base URL for local integration: `http://localhost:8000`.
Default CORS origins: `http://localhost:3000,http://localhost:5173` (override `CORS_ORIGINS`).

## Demo scenario

Run:

```bash
alembic -c backend/alembic.ini upgrade head
python backend/scripts/demo_workflow.py
```

The script performs:

1. `GET /health`, `GET /ready`.
2. `POST /api/v1/data/generate` with 2 months, seed 42, 200 residents.
3. `POST /api/v1/data/sync` and `POST /api/v1/menu/sync`.
4. `POST /api/v1/forecasts/model/train`.
5. `GET /api/v1/context?date=2026-09-01`.
6. `POST /api/v1/context/availability`.
7. `POST /api/v1/forecasts` for 2026-09-01 breakfast.
8. `POST /api/v1/plans`.
9. `POST /api/v1/simulations/compare` using historical arrivals from 2026-08-31.
10. `POST /api/v1/evaluation/runs/{run_id}` for both runs and `/evaluation/compare`.
11. `POST /api/v1/agents/planning` and inspect `/agents/traces`.
12. `POST /api/v1/agents/review` for the context run.
13. `GET /api/v1/exports/runs/{run_id}` as JSON and CSV.

Example IDs from the local demo run (not portable across databases):

```
baseline_run_id = 9736ef13-716c-4709-87d7-bcb491336b3c
context_run_id  = c9212063-01da-47d6-8d76-09c5f02c7575
forecast_run_id = 75bdb1cf-c2c8-4e5b-a612-1d607711088f
planning_trace  = 2da24c40-75d2-474f-a1e4-b38793022e95
```

## API examples

### Health

```http
GET /health
```

```json
{"status":"ok","app":"Autonomous Food Waste Optimization API","version":"1.0.0","environment":"local","synthetic_only":true}
```

### Generate and sync

```http
POST /api/v1/data/generate
Content-Type: application/json

{"months": 2, "seed": 42, "residents": 200, "validate_after": true}
```

```json
{"ok":true,"output_dir":".../data/generated","months":2,"seed":42,"residents":200,"scenario_id":"synthetic_baseline_v1","dataset_version":"1.0.0","validation":{"ok":true,"errors":[],"files":{}}}
```

```http
POST /api/v1/data/sync
```

### Forecast

```http
POST /api/v1/forecasts
Content-Type: application/json

{"date": "2026-09-01", "meal_type": "breakfast", "persist": true}
```

```json
{
  "forecast_run_id": "75bdb1cf-c2c8-4e5b-a612-1d607711088f",
  "requested_date": "2026-09-01",
  "meal_type": "breakfast",
  "model_version": "context-rf-v4",
  "selected_model": "weekday_baseline",
  "forecast_cutoff": "2026-08-31",
  "feature_schema_version": "1.3",
  "interval_method": "10th/90th quantiles of chronological validation residuals",
  "interval_is_calibrated": false,
  "unit": "portions",
  "is_synthetic": true,
  "rows": [
    {
      "date": "2026-09-01", "meal_type": "breakfast", "dish_id": "D001",
      "prediction": 288.38, "lower_bound": 183.86, "upper_bound": 346.12,
      "model_version": "context-rf-v4", "selected_model": "weekday_baseline",
      "forecast_cutoff": "2026-08-31", "feature_schema_version": "1.3",
      "interval_method": "10th/90th quantiles of chronological validation residuals",
      "interval_is_calibrated": false, "unit": "portions", "is_synthetic": true
    }
  ]
}
```

### Plan

```http
POST /api/v1/plans
Content-Type: application/json

{
  "service_date": "2026-09-01",
  "meal_type": "breakfast",
  "dish_external_id": "D001",
  "intervals": [
    {"interval_start": "07:00", "expected": 40, "lower": 30, "upper": 50},
    {"interval_start": "07:30", "expected": 50, "lower": 40, "upper": 60},
    {"interval_start": "08:00", "expected": 45, "lower": 35, "upper": 55},
    {"interval_start": "08:30", "expected": 35, "lower": 25, "upper": 45}
  ],
  "current_stock": 0,
  "batch_min": 20,
  "batch_max": 500,
  "kitchen_capacity": 500,
  "prep_lead_minutes": 30,
  "service_start": "07:00",
  "service_close": "10:00",
  "forecast_run_id": "75bdb1cf-c2c8-4e5b-a612-1d607711088f",
  "model_version": "context-rf-v4",
  "persist": true
}
```

Response includes `initial_quantity`, `reserve_quantity`, `replenishment_trigger`,
`expected_leftover`, `expected_shortage`, `constraint_checks`, `rationale`, `uncertainty`,
`approval_state: "proposed"`, `requires_human_approval: true`, `simulation_only: true`.

### Simulate

```http
POST /api/v1/simulations/compare
Content-Type: application/json

{
  "scenario_id": "synthetic_baseline_v1",
  "dataset_version": "1.0.0",
  "service_date": "2026-09-01",
  "meal_type": "breakfast",
  "dish_external_id": "D001",
  "seed": 42,
  "service_start": "07:00",
  "use_historical": true,
  "historical_date": "2026-08-31",
  "current_stock": 0,
  "capacity": 500,
  "batch_min": 20,
  "batch_max": 500,
  "consumption_rate": 0.85,
  "prep_lead_intervals": 1,
  "forecast_expected": 288.38,
  "forecast_run_id": "75bdb1cf-c2c8-4e5b-a612-1d607711088f",
  "persist": true
}
```

Both runs share the identical `demand_realization`. Outcomes distinguish
`untouched_leftover`, `plate_waste`, `shortage`, `consumed_total` and `excess_preparation`.

### Evaluate

```http
POST /api/v1/evaluation/runs/{run_id}
POST /api/v1/evaluation/compare

{"baseline_run_id": "...", "context_run_id": "...", "persist": true}
```

Metrics include waste/shortage totals and rates, excess preparation, intervention counts/success
and average response time. Denominators are returned explicitly; ratios with a zero denominator
are `null` with an interpretation note. Model forecast error is in a separate `model_metrics`
object.

### Diagnose

```http
POST /api/v1/diagnoses/pre-meal
Content-Type: application/json

{
  "service_date": "2026-09-01",
  "meal_type": "breakfast",
  "forecasts": [
    {"dish_id": "D001", "prediction": 100, "lower_bound": 80, "upper_bound": 120}
  ],
  "planned_quantities": [{"dish_id": "D001", "prepared_qty": 140}],
  "historical_waste_rate": 0.12,
  "persist": true
}
```

Post-meal diagnosis:

```http
POST /api/v1/diagnoses/post-meal
{"run_id": "...", "persist": true}
```

Both return ranked causes with confidence, field-level evidence sources and caveats. No LLM is
used; `llm_used` is `false`, and correlation is never presented as proven causation.

### Agent traces

```http
POST /api/v1/agents/planning
POST /api/v1/agents/review
GET  /api/v1/agents/traces?trace_id=...
```

Planning stages: `context_observation`, `availability_estimate`, `demand_forecast`,
`constrained_planning`, `pre_meal_diagnosis`.
Review stages: `post_meal_diagnosis`, `outcome_learning`.

Each stage persists input summary, output summary, tool calls, duration, status and error.
Invalid agent output is rejected with `AGENT_OUTPUT_REJECTED` and a `rejected` trace row.

### Export

```http
GET /api/v1/exports/runs/{run_id}?format=json
GET /api/v1/exports/runs/{run_id}?format=csv
GET /api/v1/exports/agent-traces?format=csv&trace_id=...
```

CSV run exports contain interval-event rows plus one outcome row; nested JSON is omitted in
favour of stable flat columns.

## Error format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [{"type": "greater_than_equal", "loc": ["body", "months"], "msg": "..."}],
    "request_id": "a4f7..."
  }
}
```

`X-Request-ID` is returned on every response. Common codes: `VALIDATION_ERROR`,
`MODEL_ARTIFACT_MISSING`, `MODEL_ARTIFACT_INVALID`, `FORECAST_DATE_NOT_FUTURE`,
`CONTEXT_NOT_FOUND`, `RUN_NOT_FOUND`, `RUN_ALREADY_FINISHED`, `SIMULATION_NOT_COMPLETE`,
`SIMULATION_INTERVALS_EXHAUSTED`, `AGENT_OUTPUT_REJECTED`, `DIAGNOSIS_EVIDENCE_MISSING`.

## Optimizer objective and constraints

Default weights: leftover `1.0`, shortage `8.0`, preparation cost `0.05`, batch change `0.5`.
Shortage is weighted deliberately high to protect availability. Sensitivity is tested in
`backend/tests/test_optimizer.py::test_optimizer_shortage_sensitivity`.

Hard constraints checked in the response:

- all quantities non-negative;
- initial/reserve are zero or inside `[batch_min, batch_max]`;
- `initial + reserve <= kitchen_capacity`;
- reserve preparation finishes before `service_close`;
- initial preparation fits before `service_start`;
- planned supply covers the lower demand bound where feasible.

Uncertainty is represented by lower/expected/upper interval demand and a scenario-weighted
reserve-use estimate. Approval state is always `proposed`; live execution is out of scope.

## Evaluation definitions

- `total_waste = untouched_leftover + plate_waste`
- `waste_rate_per_prepared = total_waste / prepared_total`
- `leftover_rate_per_prepared = untouched_leftover / prepared_total`
- `plate_waste_rate_per_served = plate_waste / served_total`
- `shortage_rate_per_demand = shortage / (served_total + shortage)`
- `intervention_success_rate = successful reserve interventions / completed reserve interventions`
  where success means no final shortage and completion before service close.
- `average_response_time_intervals = mean(completed_interval - trigger_interval)`.

## Acceptance checklist

- [x] Fresh database migrations succeed (`test_fresh_database_migrates_from_zero`).
- [x] Health/readiness endpoints work.
- [x] Person A forecast/availability modules integrated, not duplicated.
- [x] Required endpoints have validated contracts and OpenAPI docs.
- [x] Diagnosis uses evidence and exposes uncertainty/caveats.
- [x] Agent orchestration logs each stage and rejects invalid outputs.
- [x] Optimizer respects capacity, lead time, batch and service-close constraints.
- [x] Simulator compares both policies on the same demand realization.
- [x] Outcomes distinguish plate waste, untouched leftovers and shortages.
- [x] Evaluation metrics are persisted and reproducible; zero denominators handled.
- [x] Automated tests pass: 36 backend tests, 14 Person A tests.
- [x] Person C has setup instructions, stable contracts and a complete demo scenario.

## Known limitations and not implemented

- PostgreSQL is supported by configuration and generic SQLAlchemy/Alembic types, but CI and the
  local demo use SQLite. Run the migration against the deployment PostgreSQL instance and smoke
  test before release.
- The simulator is per dish; a meal is a collection of per-dish runs.
- Historical arrival realization comes from Person A's meal-level attendance and is scaled by the
  dish's historical demand share. This is recorded in `run.config.demand_realization_source`.
- Future-date context falls back to the latest available synthetic date; the response includes a
  caveat and `context_date`.
- Forecast intervals are empirical and not claimed calibrated.
- No LLM explainer is enabled; diagnoses are deterministic rules over validated evidence.
- No automatic retraining or production model replacement occurs after feedback.
- No live kitchen execution, no human approval UI, no authentication/authorization layer.
- React dashboard, deployment and hosting belong to Person C.

## Person C integration checklist

1. Backend base URL: `http://localhost:8000`; confirm CORS `CORS_ORIGINS` includes the frontend.
2. Freeze against the OpenAPI document at `/openapi.json`; contracts live in
   `backend/app/schemas/`.
3. Use `limit`/`offset` pagination and read `total` from list responses.
4. Treat `null` ratio metrics as “undefined denominator”, never as zero.
5. Display `interval_is_calibrated: false`, synthetic provenance and diagnosis caveats in the UI.
6. Treat plans as proposals and interventions as simulated actions only.
7. Request a migration/contract review before any breaking API change.
8. Walk through `backend/scripts/demo_workflow.py` to verify the full flow without modifying core
   service logic.
