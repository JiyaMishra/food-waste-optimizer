import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd
from src.features.feature_builder import build_features
from src.ml.forecasting import train_model
ops=pd.read_csv("data/generated/food_operations.csv")
features=build_features(ops, forecast_cutoff=ops.date.max())
artifact=train_model(features)
print(f"Saved {artifact['model_version']} trained through {artifact['training_cutoff']}")
