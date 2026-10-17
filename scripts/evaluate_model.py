import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
from pathlib import Path
from src.features.feature_builder import build_features
from src.ml.forecasting import evaluate_chronologically
ops=pd.read_csv("data/generated/food_operations.csv")
features=build_features(ops, forecast_cutoff=pd.to_datetime(ops.date).max()+pd.Timedelta(days=1))
result=evaluate_chronologically(features,test_days=30)
Path("data/generated").mkdir(exist_ok=True)
Path("data/generated/evaluation_report.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
