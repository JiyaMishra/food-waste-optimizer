"""Dataset service for MessWise.

Loads and queries the canonical menu dataset:
data/messwise_full_august_2026_menu_dataset.csv
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import pandas as pd

logger = logging.getLogger("food_optimizer.dataset_service")

DATASET_PATH = Path("data/messwise_full_august_2026_menu_dataset.csv")
ALT_DATASET_PATH = Path("data/messwise_full_august_2026_menu_dataset(1).csv")

_cached_df: pd.DataFrame | None = None


def get_dataset() -> pd.DataFrame:
    global _cached_df
    if _cached_df is not None:
        return _cached_df

    path = DATASET_PATH if DATASET_PATH.exists() else ALT_DATASET_PATH
    if not path.exists():
        raise FileNotFoundError(f"MessWise dataset not found at {DATASET_PATH} or {ALT_DATASET_PATH}")

    df = pd.read_csv(path)
    df["date"] = df["date"].astype(str)
    _cached_df = df
    return _cached_df


def list_available_dates() -> list[str]:
    df = get_dataset()
    return sorted(df["date"].unique().tolist())


def list_meals() -> list[str]:
    return ["Breakfast", "Lunch", "Snacks", "Dinner"]


def list_dishes_for_selection(target_date: str | None = None, meal: str | None = None) -> list[str]:
    df = get_dataset()
    filtered = df
    if target_date:
        filtered = filtered[filtered["date"] == target_date]
    if meal:
        filtered = filtered[filtered["meal"].str.lower() == meal.lower()]
    
    if filtered.empty:
        # Fall back to all dishes for that meal
        if meal:
            return sorted(df[df["meal"].str.lower() == meal.lower()]["food_item"].unique().tolist())
        return sorted(df["food_item"].unique().tolist())

    return sorted(filtered["food_item"].unique().tolist())


def get_record(target_date: str, meal: str, food_item: str) -> dict[str, Any] | None:
    df = get_dataset()
    match = df[
        (df["date"] == target_date)
        & (df["meal"].str.lower() == meal.lower())
        & (df["food_item"].str.lower() == food_item.lower())
    ]
    if not match.empty:
        return match.iloc[0].to_dict()
    return None


def get_meal_context(target_date: str, meal: str) -> dict[str, Any]:
    df = get_dataset()
    match = df[(df["date"] == target_date) & (df["meal"].str.lower() == meal.lower())]
    if match.empty:
        # Use average or default context
        return {
            "date": target_date,
            "meal": meal,
            "hostel_attendance_estimate": 450,
            "exam_intensity": 0.5,
            "temperature_c": 28.0,
            "rainfall_mm": 0.0,
            "is_weekend": 0,
            "day_of_week": "Monday",
            "source": "simulated_default",
            "items_count": 0,
        }
    first = match.iloc[0]
    return {
        "date": target_date,
        "meal": first["meal"],
        "hostel_attendance_estimate": int(first["hostel_attendance_estimate"]),
        "exam_intensity": float(first["exam_intensity"]),
        "temperature_c": float(first["temperature_c"]),
        "rainfall_mm": float(first["rainfall_mm"]),
        "is_weekend": int(first["is_weekend"]),
        "day_of_week": str(first["day_of_week"]),
        "source": "dataset_historical",
        "items_count": len(match),
        "available_items": match["food_item"].tolist(),
    }


def get_dish_history(food_item: str, meal: str | None = None, limit: int = 30) -> list[dict[str, Any]]:
    df = get_dataset()
    match = df[df["food_item"].str.lower() == food_item.lower()]
    if meal:
        match = match[match["meal"].str.lower() == meal.lower()]
    match = match.sort_values("date", ascending=False).head(limit)
    return match.to_dict(orient="records")
