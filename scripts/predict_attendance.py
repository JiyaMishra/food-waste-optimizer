"""Charts-ready synthetic 30-minute arrival forecasts for a future meal."""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
p = argparse.ArgumentParser()
p.add_argument("--date", required=True)
p.add_argument("--meal-type", choices=["breakfast", "lunch", "snacks", "dinner"], default="breakfast")
p.add_argument("--data-dir", default="data/generated")
a = p.parse_args()
target = pd.Timestamp(a.date).normalize()
attendance = pd.read_csv(Path(a.data_dir) / "meal_attendance.csv", parse_dates=["date"])
hist = attendance[(attendance.date < target) & (attendance.meal_type == a.meal_type)].copy()
if hist.empty: raise SystemExit("No historical arrival intervals available before requested date.")
hist["weekday"] = hist.date.dt.dayofweek
comparable = hist[hist.weekday == target.dayofweek]
if comparable.empty: comparable = hist
summary = comparable.groupby("interval_start").arrivals.agg(["mean", "std", "count"]).reset_index().sort_values("interval_start")
total = float(summary["mean"].sum()); average = total / max(1, len(summary))
rows = []
for row in summary.to_dict("records"):
    prediction = max(0.0, float(row["mean"]))
    spread = float(row["std"]) if pd.notna(row["std"]) else 0.0
    rows.append({"date": target.date().isoformat(), "meal_type": a.meal_type,
        "interval_start": row["interval_start"], "predicted_arrivals": round(prediction, 2),
        "lower_bound": round(max(0, prediction - 1.28 * spread), 2),
        "upper_bound": round(prediction + 1.28 * spread, 2),
        "rush_class": "high" if prediction >= max(1, average * 1.5) else ("low" if prediction <= average * .65 else "normal"),
        "historical_samples": int(row["count"]), "is_synthetic": True,
        "interval_method": "weekday interval mean with descriptive standard-deviation spread; not calibrated"})
print(json.dumps(rows, indent=2))
