# Person A → Person B handover

## Entry points
- Generate: `python scripts/generate_synthetic_data.py --months 6 --seed 42`
- Validate: `python scripts/validate_data.py`
- Train: `python scripts/train_model.py`
- Evaluate: `python scripts/evaluate_model.py`
- Predict: `python scripts/predict.py --date YYYY-MM-DD --meal-type breakfast`

## Suggested callable interfaces
- `generate_synthetic_data(output_dir, months, seed, residents)`
- `validate_dataset(data_dir)`
- `calculate_availability(context, academic_slots, groups)`
- `build_features(operations, forecast_cutoff)`
- `train_model(features, artifact_path)`
- `evaluate_chronologically(features, test_days=30)`

## Forecast contract
`date`, `meal_type`, `dish_id`, `predicted_demand`, `lower_bound`, `upper_bound`,
`model_version`, `forecast_cutoff`, `feature_schema_version`, `is_synthetic`.

## Handover checks
- [ ] Run generator twice with the same seed and compare substantive CSV values.
- [ ] Run validation and pytest from a clean checkout.
- [ ] Confirm chronological holdout metrics are generated from code, not hard-coded.
- [ ] Record Python/dependency versions, commit hash, dataset seed/version and training cutoff.
- [ ] Person B reproduces one forecast without copying the ML implementation.
- [ ] Confirm all stakeholders understand that data/results are synthetic.

## Scope exclusions
Person A does not own FastAPI orchestration, diagnosis, constrained batch optimization, dashboard,
Docker deployment or hosting.
