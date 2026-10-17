from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

FEATURES = ["weekday","month","demand_lag_1","demand_rolling_7"]
def train_model(features, artifact_path="ml/artifacts/context_model.joblib"):
    data = features.dropna(subset=FEATURES+["demand_qty"]).sort_values("date")
    if len(data) < 30: raise ValueError("Need at least 30 historical feature rows to train")
    cutoff = data.date.max()
    X = data[FEATURES].astype(float); y = data.demand_qty.astype(float)
    model = HistGradientBoostingRegressor(max_iter=100, random_state=42)
    model.fit(X, y)
    artifact = {"model":model,"features":FEATURES,"model_version":"context-hgb-v1",
                "training_cutoff":str(cutoff.date()),"random_seed":42,
                "dependency_note":"See requirements.txt"}
    Path(artifact_path).parent.mkdir(parents=True,exist_ok=True)
    joblib.dump(artifact,artifact_path)
    return artifact

def evaluate_chronologically(features, test_days=30):
    data = features.dropna(subset=FEATURES+["demand_qty"]).sort_values("date")
    unique_dates = sorted(data.date.unique())
    if len(unique_dates) <= test_days: raise ValueError("Not enough unique dates for chronological holdout")
    test_start = unique_dates[-test_days]
    train, test = data[data.date < test_start], data[data.date >= test_start]
    if train.empty or test.empty: raise ValueError("Chronological split produced empty train/test set")
    model = HistGradientBoostingRegressor(max_iter=100,random_state=42)
    model.fit(train[FEATURES].astype(float),train.demand_qty.astype(float))
    pred = np.maximum(0,model.predict(test[FEATURES].astype(float)))
    baseline = test.groupby(["meal_type","dish_id","weekday"]).demand_qty.transform("mean")
    # Group means on the holdout would leak labels; use the training mean by comparable weekday.
    means = train.groupby(["meal_type","dish_id","weekday"]).demand_qty.mean()
    baseline = test.apply(lambda r: means.get((r.meal_type,r.dish_id,r.weekday), train.demand_qty.mean()),axis=1)
    return {"train_period":f"{train.date.min().date()} to {train.date.max().date()}",
            "test_period":f"{test.date.min().date()} to {test.date.max().date()}",
            "context_mae":float(mean_absolute_error(test.demand_qty,pred)),
            "context_rmse":float(mean_squared_error(test.demand_qty,pred)**0.5),
            "baseline_mae":float(mean_absolute_error(test.demand_qty,baseline)),
            "baseline_rmse":float(mean_squared_error(test.demand_qty,baseline)**0.5),
            "test_rows":int(len(test)),"seed":42,
            "caveat":"Synthetic data only; scores do not establish real-world waste reduction."}
