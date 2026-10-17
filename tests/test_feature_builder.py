import pandas as pd
import pytest
from src.features.feature_builder import build_features

def sample_ops():
    rows = []
    for day in pd.date_range("2026-01-01", periods=10):
        rows.append({"date": day, "meal_type": "lunch", "dish_id": "D1",
                     "demand_qty": 20, "consumed_qty": 15, "served_qty": 18, "plate_waste": 3})
    return pd.DataFrame(rows)

def test_features_use_only_prior_observations():
    df = sample_ops()
    features = build_features(df, forecast_cutoff="2026-01-11")
    assert len(features) == 9
    assert features.iloc[0]["demand_lag_1"] == 20
    assert features.iloc[0]["demand_rolling_7"] == 20
    assert features.iloc[0]["waste_rate_lag"] == pytest.approx(3/18)

def test_cutoff_excludes_target_and_future_rows():
    df = sample_ops()
    df.loc[df.date == pd.Timestamp("2026-01-10"), "demand_qty"] = 9999
    features = build_features(df, forecast_cutoff="2026-01-10")
    assert features.date.max() == pd.Timestamp("2026-01-09")
    assert 9999 not in features.demand_qty.tolist()

def test_missing_columns_fail_clearly():
    with pytest.raises(ValueError, match="missing required columns"):
        build_features(pd.DataFrame({"date": ["2026-01-01"]}))
