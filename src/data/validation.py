"""Structural, provenance, quantity and cross-table validation for generated CSV data."""
from pathlib import Path
import pandas as pd

PROVENANCE = {"is_synthetic", "generation_seed", "generated_at", "scenario_id", "dataset_version"}
REQUIRED_FILES = {
    "residents_synthetic.csv", "hostel_daily_state.csv", "academic_slots.csv",
    "campus_events.csv", "weather_daily.csv", "menu_calendar.csv",
    "preference_survey_synthetic.csv", "meal_attendance.csv", "food_operations.csv",
}

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
        if df.empty and path.name not in {"campus_events.csv"}:
            errors.append(f"{path.name}: dataset is unexpectedly empty")
        missing = PROVENANCE - set(df.columns)
        if missing:
            errors.append(f"{path.name}: missing provenance columns {sorted(missing)}")
        if "is_synthetic" in df and not df["is_synthetic"].astype(str).str.lower().eq("true").all():
            errors.append(f"{path.name}: non-synthetic or missing provenance flag")
        quantity_cols = [c for c in df.columns if c.endswith("_qty") or c in {"arrivals", "consumed_qty", "prepared_qty", "served_qty"}]
        for col in quantity_cols:
            values = pd.to_numeric(df[col], errors="coerce")
            if values.isna().any():
                errors.append(f"{path.name}: non-numeric or missing values in {col}")
            elif (values < 0).any():
                errors.append(f"{path.name}: negative values in {col}")

    ops = frames.get("food_operations.csv")
    if ops is not None and not ops.empty:
        for col in ["prepared_qty", "served_qty", "consumed_qty", "untouched_leftover", "plate_waste", "demand_qty"]:
            if col not in ops: errors.append(f"food_operations.csv: missing {col}")
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

    att = frames.get("meal_attendance.csv")
    if att is not None and not att.empty:
        required = {"meal_id", "arrivals", "cumulative_attendance"}
        if not required.issubset(att.columns):
            errors.append(f"meal_attendance.csv: missing columns {sorted(required - set(att.columns))}")
        else:
            for meal_id, group in att.groupby("meal_id"):
                group = group.sort_values("interval_start" if "interval_start" in group else group.index.name or "meal_id")
                arrivals = pd.to_numeric(group["arrivals"], errors="coerce")
                cumulative = pd.to_numeric(group["cumulative_attendance"], errors="coerce")
                if arrivals.isna().any() or cumulative.isna().any():
                    errors.append(f"meal_attendance.csv: non-numeric attendance for {meal_id}")
                elif not cumulative.is_monotonic_increasing or int(arrivals.sum()) != int(cumulative.iloc[-1]):
                    errors.append(f"meal_attendance.csv: interval/cumulative mismatch for {meal_id}")

    menu = frames.get("menu_calendar.csv")
    if menu is not None and ops is not None and {"meal_id", "dish_id"}.issubset(menu.columns) and {"meal_id", "dish_id"}.issubset(ops.columns):
        menu_keys = set(map(tuple, menu[["meal_id", "dish_id"]].drop_duplicates().to_numpy()))
        op_keys = set(map(tuple, ops[["meal_id", "dish_id"]].drop_duplicates().to_numpy()))
        if menu_keys != op_keys:
            errors.append("menu_calendar.csv and food_operations.csv meal_id/dish_id keys do not match")

    return {"ok": not errors, "errors": errors, "files": report}
