"""Generate a future-date dish forecast from the saved artifact."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import joblib
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True, help="Forecast date, YYYY-MM-DD")
parser.add_argument("--meal-type", default="breakfast")
parser.add_argument("--data-dir", default="data/generated")
parser.add_argument("--artifact", default="ml/artifacts/context_model.joblib")
args = parser.parse_args()
forecast_date = pd.Timestamp(args.date).normalize()
artifact = joblib.load(args.artifact)
if forecast_date <= pd.Timestamp(artifact["training_cutoff"]):
    raise SystemExit(f"Forecast date must be after training cutoff {artifact['training_cutoff']}")
ops = pd.read_csv(Path(args.data_dir) / "food_operations.csv", parse_dates=["date"])
hist = ops[(ops.date < forecast_date) & (ops.meal_type == args.meal_type)].copy()
if hist.empty:
    raise SystemExit("No historical rows before requested date/meal type.")
daily = hist.groupby(["date", "dish_id"], as_index=False).agg(demand_qty=("demand_qty", "sum"))
rows = []
for dish, group in daily.groupby("dish_id"):
    group = group.sort_values("date")
    features = {"weekday": forecast_date.dayofweek, "month": forecast_date.month,
        "demand_lag_1": float(group.demand_qty.iloc[-1]),
        "demand_rolling_7": float(group.demand_qty.tail(7).mean()),
        "meal_type": args.meal_type, "dish_id": str(dish)}
    x = pd.DataFrame([{name: features[name] for name in artifact["features"]}])
    prediction = max(0.0, float(artifact["model"].predict(x)[0]))
    lower = max(0.0, prediction + float(artifact.get("residual_lower", 0.0)))
    upper = max(lower, prediction + float(artifact.get("residual_upper", 0.0)))
    rows.append({"date": forecast_date.date().isoformat(), "meal_type": args.meal_type, "dish_id": dish,
        "prediction": round(prediction, 2), "lower_bound": round(lower, 2), "upper_bound": round(upper, 2),
        "model_version": artifact["model_version"], "forecast_cutoff": forecast_date.date().isoformat(),
        "feature_schema_version": artifact.get("feature_schema_version", "1.0"),
        "interval_method": artifact.get("interval_method", "not available"),
        "interval_is_calibrated": bool(artifact.get("interval_is_calibrated", False)),
        "unit": "portions", "is_synthetic": True})
print(json.dumps(rows, indent=2))
