import pandas as pd

def build_features(operations, forecast_cutoff=None):
    """Build historical-only dish/meal/date features; outcomes from the target date are excluded."""
    df = operations.copy()
    df["date"] = pd.to_datetime(df["date"])
    cutoff = pd.Timestamp(forecast_cutoff) if forecast_cutoff else df.date.max()
    hist = df[df.date < cutoff].copy()
    if hist.empty: raise ValueError("No historical rows exist before forecast_cutoff")
    hist["weekday"] = hist.date.dt.dayofweek
    hist["month"] = hist.date.dt.month
    daily = hist.groupby(["date","meal_type","dish_id"],as_index=False).agg(
        demand_qty=("demand_qty","sum"), consumed_qty=("consumed_qty","sum"))
    daily["weekday"] = daily.date.dt.dayofweek
    daily["month"] = daily.date.dt.month
    daily = daily.sort_values("date")
    daily["demand_lag_1"] = daily.groupby(["meal_type","dish_id"]).demand_qty.shift(1)
    daily["demand_rolling_7"] = daily.groupby(["meal_type","dish_id"]).demand_qty.transform(
        lambda s: s.shift(1).rolling(7,min_periods=1).mean())
    daily["waste_rate_lag"] = daily.groupby(["meal_type","dish_id"]).apply(
        lambda g: (g.plate_waste if "plate_waste" in g else g.consumed_qty*0).shift(1),
        include_groups=False).reset_index(level=[0,1],drop=True) if "plate_waste" in daily else 0.0
    return daily.dropna(subset=["demand_lag_1"])
