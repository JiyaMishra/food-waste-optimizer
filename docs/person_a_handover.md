# Person A → Person B handover

## Entry points
- Generate synthetic data: python scripts/generate_synthetic_data.py --months 6 --seed 42
- Validate: python scripts/validate_data.py
- Train and save model: python scripts/train_model.py
- Evaluate baseline versus context model: python scripts/evaluate_model.py
- Predict dish demand: python scripts/predict.py --date 2026-09-01 --meal-type breakfast
- Predict 30-minute arrivals: python scripts/predict_attendance.py --date 2026-09-01 --meal-type breakfast
- Test: pytest -q

## Python interfaces
- generate_synthetic_data(output_dir, months, seed, residents)
- validate_dataset(data_dir)
- calculate_availability(context, academic_slots, groups)
- build_features(operations, forecast_cutoff)
- train_model(features, artifact_path)
- evaluate_chronologically(features, test_days=30)

## Forecast contract
Dish forecasts include date, meal_type, dish_id, prediction, lower_bound, upper_bound, model_version, forecast_cutoff, feature_schema_version, interval_method, interval_is_calibrated, unit and is_synthetic. Interval offsets are empirical and explicitly not claimed calibrated. Arrival forecasts include interval start, predicted arrivals, descriptive lower/upper estimates, rush class and sample count.

## Clean checkout run order
    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -r requirements.txt
    python scripts/generate_synthetic_data.py --months 6 --seed 42
    python scripts/validate_data.py
    pytest -q
    python scripts/train_model.py
    python scripts/evaluate_model.py
    python scripts/predict.py --date 2026-09-01 --meal-type breakfast
    python scripts/predict_attendance.py --date 2026-09-01 --meal-type breakfast

## Handover evidence
Record Python/dependency versions, commit SHA, seed, dataset version, model version and training cutoff. Keep validation output, pytest output, JSON/Markdown evaluation reports and one sample of each forecast. All data is synthetic.

## Scope exclusions
Person A does not own FastAPI orchestration, diagnosis, constrained batch optimization, dashboard, Docker deployment or hosting.
