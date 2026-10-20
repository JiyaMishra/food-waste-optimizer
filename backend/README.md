# Person B backend — Autonomous Context-Aware Food Waste Optimization

FastAPI backend for synthetic-data ingestion, forecasting integration, waste diagnosis,
constrained batch planning, meal-service simulation, agent orchestration, evaluation and
CSV/JSON export.

> **Synthetic-only notice:** every dataset, forecast, diagnosis and outcome in this backend is
> simulated. No endpoint reads live VIT attendance, weather, student identities or kitchen
> systems, and no endpoint performs a real kitchen action.

## Layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app, CORS, error contract, request IDs
│   ├── api/v1/                 # health, menu, data, context, forecasts, plans,
│   │                           # simulations, diagnoses, agents, evaluation,
│   │                           # feedback, exports
│   ├── core/config.py          # environment variables and paths
│   ├── db/models.py            # relational models and integrity constraints
│   ├── schemas/                # Pydantic request/response contracts
│   ├── services/               # menu, data, availability, forecasting,
│   │                           # waste_diagnosis, optimizer, simulator,
│   │                           # evaluation, feedback, exports
│   ├── agents/                 # typed agents + master orchestrator
│   └── tests/                  # pytest suite (36 tests)
├── alembic/                    # initial migration + env.py
├── alembic.ini
├── Dockerfile
├── requirements.txt
└── scripts/demo_workflow.py    # reproducible end-to-end demo
```

Person A's modules remain in `src/` and are imported directly (`src.data`, `src.availability`,
`src.features`, `src.ml`). They are not copied or reimplemented.

## Prerequisites

- Python 3.11+ (CI uses 3.11; this repository was also exercised with 3.14)
- PostgreSQL for deployment, or SQLite for local development
- The repository root must be the working directory when running commands

## Environment variables

Copy `.env.example` to `.env` and adjust. The application reads:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///backend/data/food_optimizer.db` | SQLAlchemy DSN. Production: `postgresql+psycopg://user:password@host:5432/db` |
| `CORS_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Comma-separated Person C origins |
| `LOG_LEVEL` | `INFO` | Structured JSON log level |
| `DATA_DIR` | `data/generated` | Person A synthetic CSV directory |
| `MENU_SEED_PATH` | `data/menu_seed/vegetarian_menu.csv` | Starter vegetarian catalogue |
| `MODEL_ARTIFACT_PATH` | `ml/artifacts/context_model.joblib` | Person A model artifact |
| `SQL_ECHO` | `false` | SQLAlchemy statement echo |
| `ATTENDANCE_PROBABILITY` | `0.65` | Default availability multiplier |
| `DEFAULT_CONSUMPTION_RATE` | `0.85` | Default simulator consumption fraction |

Secrets belong in `.env`, which is gitignored. Do not commit production DSNs.

## Local setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
python -m pip install -r requirements.txt

# Apply the schema from zero
alembic -c backend/alembic.ini upgrade head

# Explicit data preparation (never runs on application startup)
python scripts/generate_synthetic_data.py --months 6 --seed 42
python scripts/validate_data.py
python scripts/train_model.py
```

Alternatively use the API: `POST /api/v1/data/generate` → `POST /api/v1/data/sync` →
`POST /api/v1/forecasts/model/train`.

## Run the API

```bash
uvicorn backend.app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI: http://localhost:8000/openapi.json
- Health: `GET /health`; readiness: `GET /ready`

## Run the end-to-end demo

```bash
alembic -c backend/alembic.ini upgrade head
python backend/scripts/demo_workflow.py
```

The demo exercises: health → generate → sync → menu sync → train → context → availability →
forecast → plan → simulate both policies on the same arrival realization → evaluate → compare →
agent planning trace → agent review trace → JSON/CSV export.

## Tests

```bash
pytest backend/tests -q
```

The suite covers migrations from zero, constraints/foreign keys, Person A integration, forecast
contracts, optimizer constraints and sensitivity, simulator transitions, both policies on the
same demand realization, diagnosis evidence, agent output rejection, evaluation edge cases,
feedback and exports.

Person A's original suite still runs from the repository root:

```bash
pytest -q
```

## Endpoint inventory

| Method | Path | Purpose |
|---|---|---|
| GET | `/health`, `/ready` | Liveness and dependency/data readiness |
| GET | `/api/v1/menu` | Starter menu catalogue from Person A CSV |
| POST | `/api/v1/menu/sync` | Persist catalogue to `dishes` |
| GET | `/api/v1/menu/database` | Persisted dishes |
| POST | `/api/v1/data/generate` | Explicit Person A synthetic data generation |
| POST | `/api/v1/data/validate` | Person A structural/quantity validation |
| POST | `/api/v1/data/sync` | Persist generated menu/context/slots |
| GET | `/api/v1/context?date=` | Synthetic context; latest-available fallback is explicit |
| GET | `/api/v1/context/timetable?date=` | Academic slots |
| POST | `/api/v1/context/availability` | Person A `calculate_availability` |
| GET | `/api/v1/context/availability/snapshots` | Persisted availability snapshots |
| POST | `/api/v1/forecasts` | Dish forecast from Person A artifact |
| POST | `/api/v1/forecasts/model/train` | Train/select artifact from generated data |
| GET | `/api/v1/forecasts/predictions` | Persisted predictions |
| GET | `/api/v1/forecasts/runs/{forecast_run_id}` | Predictions for one forecast run |
| POST | `/api/v1/plans` | Constrained batch plan |
| GET | `/api/v1/plans`, `/api/v1/plans/{plan_id}` | Persisted plans |
| POST | `/api/v1/simulations` | Start a policy run |
| POST | `/api/v1/simulations/compare` | Run baseline + context on one realization |
| POST | `/api/v1/simulations/{run_id}/step` | Reveal one service interval |
| POST | `/api/v1/simulations/{run_id}/finish` | Close service and persist outcomes |
| GET | `/api/v1/simulations`, `/api/v1/simulations/{run_id}` | Run records |
| GET | `/api/v1/simulations/{run_id}/outcome` | Persisted outcome |
| POST | `/api/v1/diagnoses/pre-meal` | Evidence-based risk estimate |
| POST | `/api/v1/diagnoses/post-meal` | Retrospective diagnosis of a finished run |
| GET | `/api/v1/diagnoses`, `/api/v1/diagnoses/{id}` | Stored diagnoses |
| POST | `/api/v1/agents/planning` | Context → availability → forecast → plan → diagnosis trace |
| POST | `/api/v1/agents/review` | Post-meal diagnosis → evaluation trace |
| GET | `/api/v1/agents/traces`, `/api/v1/agents/traces/{trace_id}` | Agent traces |
| POST | `/api/v1/evaluation/runs/{run_id}` | Compute + persist operational metrics |
| GET | `/api/v1/evaluation/runs/{run_id}/latest` | Latest evaluation |
| POST | `/api/v1/evaluation/compare` | Baseline vs context deltas |
| GET | `/api/v1/evaluation/{evaluation_id}` | Evaluation record |
| POST/GET | `/api/v1/feedback` | Feedback + candidate-retraining metadata (no auto-retrain) |
| GET | `/api/v1/exports/runs/{run_id}?format=json\|csv` | Full run export |
| GET | `/api/v1/exports/agent-traces?format=json\|csv` | Trace export |

## Error contract

Every error uses the same shape:

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

The `X-Request-ID` response header carries the same correlation id. Domain failures use stable
codes such as `MODEL_ARTIFACT_MISSING`, `FORECAST_DATE_NOT_FUTURE`, `RUN_ALREADY_FINISHED`,
`AGENT_OUTPUT_REJECTED` and `DIAGNOSIS_EVIDENCE_MISSING`.

## Database and migrations

The initial migration creates: `dishes`, `menu_items`, `synthetic_context`, `academic_slots`,
`availability_snapshots`, `meal_runs`, `simulation_events`, `outcomes`, `predictions`,
`batch_plans`, `agent_traces`, `diagnoses`, `interventions`, `evaluation_runs`, `feedback_events`.

Integrity rules include non-negative quantities, batch bounds, kitchen capacity, valid service
intervals, optimistic run status values, status enums, `consumed <= served <= prepared`, and
foreign keys. SQLite enforces foreign keys through `PRAGMA foreign_keys=ON`; PostgreSQL enforces
them natively.

```bash
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini check
alembic -c backend/alembic.ini downgrade base
```

## Local Docker

Build from the repository root:

```bash
docker build -f backend/Dockerfile -t food-optimizer-backend .
docker run --rm -p 8000:8000 --env-file .env food-optimizer-backend
```

## Known limitations

- CI and local tests use SQLite for portability. PostgreSQL is supported through
  `DATABASE_URL` and `psycopg`; run the migration against the target PostgreSQL instance before
  deployment.
- The simulator is per dish. A full meal is represented by a set of per-dish runs.
- Historical arrival realization is meal-level in Person A's data; the simulator scales it by the
  selected dish's historical demand share and records that in `run.config`.
- Forecast intervals are empirical Person A offsets, not statistically calibrated intervals.
- Context for a future service date falls back to the latest available synthetic date and returns
  an explicit caveat.
- No LLM is enabled. Diagnoses are deterministic rule-based evidence, and no production model is
  retrained automatically after feedback.
- No live kitchen execution or approval workflow is implemented. Plans are proposals and
  interventions are simulation actions only.
- The full React dashboard, deployment and hosting belong to Person C.

See `docs/person_b_handover.md` for API examples, the demo scenario, acceptance evidence and
Person C integration notes.
