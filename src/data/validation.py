"""Structural, provenance, quantity and cross-table validation for generated CSV data."""
from pathlib import Path
import pandas as pd

PROVENANCE = {"is_synthetic", "generation_seed", "generated_at", "scenario_id", "dataset_version"}
REQUIRED_FILES = {
    "residents_synthetic.csv", "hostel_daily_state.csv", "academic_slots.csv",
    "campus_events.csv", "weather_daily.csv", "menu_calendar.csv",
    "preference_survey_synthetic.csv", "meal_attendance.csv", "food_operations.csv",
}
REQUIRED_COLUMNS = {
    "residents_synthetic.csv": {"resident_key", "hostel_id", "mess_id"},
    "hostel_daily_state.csv": {"date", "hostel_id", "mess_id", "capacity", "occupied_count", "occupancy_rate"},
    "academic_slots.csv": {"date", "cohort_id", "activity_type", "start_time", "end_time"},
    "campus_events.csv": {"event_id", "date", "start_time", "end_time", "expected_participants"},
    "weather_daily.csv": {"date", "rain_mm", "temperature_c"},
    "menu_calendar.csv": {"date", "meal_id", "meal_type", "dish_id", "dish_name", "vegetarian_flag"},
    "preference_survey_synthetic.csv": {"respondent_key", "dish_id", "rating"},
    "meal_attendance.csv": {"meal_id", "date", "meal_type", "interval_start", "arrivals", "cumulative_attendance"},
    "food_operations.csv": {"meal_id", "date", "meal_type", "dish_id", "prepared_qty", "served_qty",
                            "consumed_qty", "untouched_leftover", "plate_waste", "demand_qty"},
}

def _keys(df, cols):
    return set(map(tuple, df[list(cols)].drop_duplicates().to_numpy()))

def validate_dataset(data_dir="data/generated"):
    root = Path(data_dir)
    errors, report = [], {}
    if not root.exists():
        return {"ok": False, "errors": [f"data directory does not exist: {root}"], "files": {}}
    existing = {p.name for p in root.glob("*.csv")}
    missing_files = REQUIRED_FILES - existing
    if missing_files:
        errors.append(f"missing required CSV files: {sorted(missing_files)}")
    frames = {}
    for path in sorted(root.glob("*.csv")):
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            errors.append(f"{path.name}: could not read CSV ({exc})")
            continue
        frames[path.name] = df
        report[path.name] = {"rows": len(df), "missing_cells": int(df.isna().sum().sum())}
        if df.empty and path.name != "campus_events.csv":
            errors.append(f"{path.name}: dataset is unexpectedly empty")
        required_cols = REQUIRED_COLUMNS.get(path.name, set())
        if required_cols - set(df.columns):
            errors.append(f"{path.name}: missing required columns {sorted(required_cols - set(df.columns))}")
        missing_meta = PROVENANCE - set(df.columns)
        if missing_meta:
            errors.append(f"{path.name}: missing provenance columns {sorted(missing_meta)}")
        if "is_synthetic" in df and not df["is_synthetic"].astype(str).str.lower().eq("true").all():
            errors.append(f"{path.name}: non-synthetic or missing provenance flag")
        if len(df):
            for col in ["generation_seed", "generated_at", "scenario_id", "dataset_version"]:
                if col in df and df[col].isna().any():
                    errors.append(f"{path.name}: missing provenance values in {col}")
            # All data except optional event rows must be complete.
            if path.name != "campus_events.csv" and df.isna().any().any():
                errors.append(f"{path.name}: contains missing cell values")
        quantity_cols = [c for c in df.columns if c.endswith("_qty") or c in {
            "arrivals", "cumulative_attendance", "prepared_qty", "served_qty", "consumed_qty",
            "untouched_leftover", "plate_waste", "capacity", "occupied_count", "expected_participants",
            "rating", "rain_mm"}]
        for col in quantity_cols:
            values = pd.to_numeric(df[col], errors="coerce")
            if values.isna().any():
                errors.append(f"{path.name}: non-numeric or missing values in {col}")
            elif (values < 0).any():
                errors.append(f"{path.name}: negative values in {col}")

    ops = frames.get("food_operations.csv")
    if ops is not None and not ops.empty:
        if {"consumed_qty", "served_qty", "prepared_qty"}.issubset(ops):
            if not (ops["consumed_qty"] <= ops["served_qty"]).all(): errors.append("consumed_qty exceeds served_qty")
            if not (ops["served_qty"] <= ops["prepared_qty"]).all(): errors.append("served_qty exceeds prepared_qty")
        if {"untouched_leftover", "prepared_qty", "served_qty"}.issubset(ops):
            if not (ops["untouched_leftover"] == ops["prepared_qty"] - ops["served_qty"]).all():
                errors.append("leftover accounting mismatch")
        if {"plate_waste", "served_qty", "consumed_qty"}.issubset(ops):
            if not (ops["plate_waste"] == ops["served_qty"] - ops["consumed_qty"]).all():
                errors.append("plate-waste accounting mismatch")
        if {"meal_id", "dish_id"}.issubset(ops) and ops.duplicated(["meal_id", "dish_id"]).any():
            errors.append("food_operations.csv: duplicate meal_id/dish_id records")

    state = frames.get("hostel_daily_state.csv")
    if state is not None and not state.empty and {"capacity", "occupied_count", "occupancy_rate"}.issubset(state):
        if not (state["occupied_count"] <= state["capacity"]).all():
            errors.append("hostel_daily_state.csv: occupied_count exceeds capacity")
        expected = state["occupied_count"] / state["capacity"]
        if not (expected.sub(state["occupancy_rate"]).abs() <= 0.001).all():
            errors.append("hostel_daily_state.csv: occupancy_rate does not match occupied_count/capacity")
        if state.duplicated(["date", "hostel_id", "mess_id"]).any():
            errors.append("hostel_daily_state.csv: duplicate date/hostel_id/mess_id rows")

    att = frames.get("meal_attendance.csv")
    if att is not None and not att.empty:
        if att.duplicated(["meal_id", "interval_start"]).any():
            errors.append("meal_attendance.csv: duplicate meal_id/interval_start rows")
        for meal_id, group in att.groupby("meal_id"):
            group = group.sort_values("interval_start")
            arrivals = pd.to_numeric(group["arrivals"], errors="coerce")
            cumulative = pd.to_numeric(group["cumulative_attendance"], errors="coerce")
            if arrivals.isna().any() or cumulative.isna().any():
                errors.append(f"meal_attendance.csv: non-numeric attendance for {meal_id}")
            elif (cumulative.diff().fillna(cumulative.iloc[0]) != arrivals).any() or int(arrivals.sum()) != int(cumulative.iloc[-1]):
                errors.append(f"meal_attendance.csv: interval/cumulative mismatch for {meal_id}")
            if len(group) != 4:
                errors.append(f"meal_attendance.csv: expected 4 intervals for {meal_id}, found {len(group)}")

    menu = frames.get("menu_calendar.csv")
    if menu is not None and ops is not None and not menu.empty and not ops.empty:
        key_cols = ["meal_id", "dish_id"]
        if _keys(menu, key_cols) != _keys(ops, key_cols):
            errors.append("menu_calendar.csv and food_operations.csv meal_id/dish_id keys do not match")
        if menu.duplicated(key_cols).any():
            errors.append("menu_calendar.csv: duplicate meal_id/dish_id rows")
    if menu is not None and att is not None and not menu.empty and not att.empty:
        if set(menu["meal_id"]) != set(att["meal_id"]):
            errors.append("meal_attendance.csv and menu_calendar.csv meal_id sets do not match")

    residents = frames.get("residents_synthetic.csv")
    if residents is not None and not residents.empty:
        if residents["resident_key"].duplicated().any():
            errors.append("residents_synthetic.csv: duplicate resident_key")
        state = frames.get("hostel_daily_state.csv")
        if state is not None and not state.empty:
            if not set(residents["hostel_id"]).issubset(set(state["hostel_id"])):
                errors.append("resident hostel_id references missing from hostel_daily_state.csv")
            if not set(residents["mess_id"]).issubset(set(state["mess_id"])):
                errors.append("resident mess_id references missing from hostel_daily_state.csv")
    pref = frames.get("preference_survey_synthetic.csv")
    if pref is not None and menu is not None and not pref.empty and not menu.empty:
        if not set(pref["dish_id"]).issubset(set(menu["dish_id"])):
            errors.append("preference_survey_synthetic.csv contains dish_id values absent from menu_calendar.csv")
    weather = frames.get("weather_daily.csv")
    state = frames.get("hostel_daily_state.csv")
    if weather is not None and state is not None and not weather.empty and not state.empty:
        if set(state["date"]) - set(weather["date"]):
            errors.append("hostel_daily_state.csv contains dates absent from weather_daily.csv")

    return {"ok": not errors, "errors": errors, "files": report}
