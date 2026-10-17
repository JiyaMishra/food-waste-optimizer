import pandas as pd
import pytest
from src.ml.forecasting import evaluate_chronologically, train_model

def feature_rows(days=70):
    rows=[]
    for day in pd.date_range("2026-01-01", periods=days):
        for meal in ["breakfast", "lunch"]:
            for dish in ["D1", "D2"]:
                demand=20+day.dayofweek+(3 if meal=="lunch" else 0)+(2 if dish=="D2" else 0)
                rows.append({"date":day,"meal_type":meal,"dish_id":dish,"weekday":day.dayofweek,
                    "month":day.month,"demand_lag_1":demand-1,"demand_rolling_7":demand-1,"demand_qty":demand})
    return pd.DataFrame(rows)

def test_chronological_evaluation_compares_same_holdout():
    result=evaluate_chronologically(feature_rows(),test_days=14)
    assert result["test_rows"]>0
    assert "context_mae" in result and "baseline_mae" in result
    assert result["target_unit"]=="portions"

def test_training_saves_artifact_with_schema_and_intervals(tmp_path):
    path=tmp_path/"model.joblib"
    artifact=train_model(feature_rows(),path)
    assert path.exists()
    assert artifact["features"]
    assert artifact["residual_lower"]<=artifact["residual_upper"]
    assert artifact["interval_is_calibrated"] is False

def test_evaluation_rejects_too_short_history():
    with pytest.raises(ValueError,match="Not enough unique dates"):
        evaluate_chronologically(feature_rows(20),test_days=30)
