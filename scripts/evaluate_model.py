"""Run chronological holdout evaluation and save JSON and Markdown reports."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.features.feature_builder import build_features
from src.ml.forecasting import evaluate_chronologically

data_dir = Path("data/generated")
ops = pd.read_csv(data_dir / "food_operations.csv", parse_dates=["date"])
features = build_features(ops, forecast_cutoff=ops.date.max() + pd.DateOffset(days=1))
result = evaluate_chronologically(features, test_days=30)
data_dir.mkdir(exist_ok=True)
(data_dir / "evaluation_report.json").write_text(json.dumps(result, indent=2))
lines = ["# Synthetic demand forecasting evaluation", "",
    f"- Training period: {result['train_period']}", f"- Holdout period: {result['test_period']}",
    f"- Holdout rows: {result['test_rows']}", f"- Random seed: {result['seed']}",
    f"- Model version: {result['model_version']}", f"- Target unit: {result['target_unit']}", "",
    "| Model | MAE (portions) | RMSE (portions) |", "|---|---:|---:|",
    f"| Context-aware | {result['context_mae']:.3f} | {result['context_rmse']:.3f} |",
    f"| Weekday baseline | {result['baseline_mae']:.3f} | {result['baseline_rmse']:.3f} |", "",
    f"Context model beats baseline MAE: **{result['context_beats_baseline_mae']}**", "",
    "## By meal type", "", "| Meal | Rows | Context MAE | Baseline MAE |", "|---|---:|---:|---:|"]
for meal, metrics in result["by_meal_type"].items():
    lines.append(f"| {meal} | {metrics['rows']} | {metrics['context_mae']:.3f} | {metrics['baseline_mae']:.3f} |")
lines += ["", f"> Limitation: {result['caveat']}"]
(data_dir / "evaluation_report.md").write_text("\n".join(lines) + "\n")
print(json.dumps(result, indent=2))
