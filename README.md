# Autonomous Context-Aware Food Waste Optimization System — Person A

Person A's phase: reproducible synthetic data, data validation, vegetarian menu catalogue,
availability/context features, baseline and context-aware forecasting, evaluation, tests and handover.

> **Synthetic-data notice:** every generated record and result is simulated. This repository is not
> connected to VIT attendance, live weather, student identities, or kitchen systems.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python scripts/generate_synthetic_data.py --months 6 --seed 42
python scripts/validate_data.py
python scripts/train_model.py
python scripts/evaluate_model.py
pytest -q
```

Run a forecast after training:

```bash
python scripts/predict.py --date 2026-09-01 --meal-type breakfast
```

Generated CSV files are written to `data/generated/`. The model is saved under `ml/artifacts/`.
Do not regenerate data automatically when an application starts.

## What is implemented

- Seeded, related synthetic datasets for residents, daily hostel state, academic slots, events,
  weather, menu calendar, preferences, meal attendance and food operations.
- Vegetarian starter menu catalogue; extend it only after manually verifying supplied menu images.
- Referential/quantity validation and synthetic provenance metadata.
- Availability estimates with overlapping-unavailability protection.
- Forecast-time feature builder with historical lag features.
- Historical weekday baseline and scikit-learn context-aware model.
- Chronological holdout evaluation (MAE/RMSE) and saved artifacts.
- Tests and handover contracts for Person B.

## Scope boundary

Person A does **not** implement the full FastAPI application, agent orchestration, waste diagnosis,
constrained batch optimizer, React dashboard, Docker deployment or hosted application. Those are
owned by other workstreams in the project blueprint.

## Units and accounting

Quantities are measured in **portions**. For each dish/meal record:
`consumed_qty <= served_qty <= prepared_qty`; all quantities are non-negative.
Unserved leftovers and plate waste are separate measures and must not be double-counted.

See `docs/data_dictionary.md`, `docs/evaluation_protocol.md` and `docs/person_a_handover.md`.
