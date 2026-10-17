"""Train the selected demand forecasting artifact from all available historical rows."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.features.feature_builder import build_features
from src.ml.forecasting import train_model

ops = pd.read_csv("data/generated/food_operations.csv", parse_dates=["date"])
# A training cutoff is exclusive, so advance one day to include the final observed date.
features = build_features(ops, forecast_cutoff=ops["date"].max() + pd.Timedelta(days=1))
artifact = train_model(features)
print(f"Saved {artifact['model_version']} trained through {artifact['training_cutoff']}; "
      f"selected={artifact['selected_model']}; "
      f"validation MAE context={artifact['validation_context_mae']:.3f}, "
      f"baseline={artifact['validation_baseline_mae']:.3f}")
