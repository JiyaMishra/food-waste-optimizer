"""Leakage-aware feature engineering for dish-level demand forecasts."""
import pandas as pd

REQUIRED_COLUMNS = {"date", "meal_type", "dish_id", "demand_qty", "consumed_qty",
                    "plate_waste", "served_qty"}

def build_features(operations, forecast_cutoff=None):
    """Build daily dish features using only records strictly before forecast_cutoff.

    The cutoff applies to source rows; lag/rolling values are shifted so each training
    row uses only earlier observations for that dish and meal.
    """
    missing = REQUIRED_COLUMNS - set(operations.columns)
    if missing:
        raise ValueError(f"operations missing required columns: {sorted(missing)}")
    df = operations.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    for col in ["demand_qty", "consumed_qty", "plate_waste", "served_qty"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
        if (df[col] < 0).any():
            raise ValueError(f"{col} cannot contain negative values")
    cutoff = pd.Timestamp(forecast_cutoff).normalize() if forecast_cutoff is not None else df["date"].max() + pd.DateOffset(days=1)
    hist = df.loc[df["date"] < cutoff].copy()
    if hist.empty:
        raise ValueError("No historical rows exist before forecast_cutoff")
    daily = (hist.groupby(["date", "meal_type", "dish_id"], as_index=False)
             .agg(demand_qty=("demand_qty", "sum"),
                  consumed_qty=("consumed_qty", "sum"),
                  plate_waste=("plate_waste", "sum"),
                  served_qty=("served_qty", "sum")))
    daily["weekday"] = daily["date"].dt.dayofweek
    daily["month"] = daily["date"].dt.month
    daily = daily.sort_values(["meal_type", "dish_id", "date"]).reset_index(drop=True)
    keys = ["meal_type", "dish_id"]
    grouped = daily.groupby(keys, sort=False)
    daily["demand_lag_1"] = grouped["demand_qty"].shift(1)
    daily["demand_rolling_7"] = grouped["demand_qty"].transform(
        lambda s: s.shift(1).rolling(window=7, min_periods=1).mean())
    daily["waste_rate"] = (daily["plate_waste"] / daily["served_qty"].where(daily["served_qty"] > 0)).fillna(0).clip(0, 1)
    daily["waste_rate_lag"] = daily.groupby(keys, sort=False)["waste_rate"].shift(1)
    return daily.dropna(subset=["demand_lag_1", "demand_rolling_7"]).reset_index(drop=True)
