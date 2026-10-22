"""Menu catalogue retrieval and persistence.

The CSV in ``data/menu_seed`` is Person A's canonical starter catalogue. The
database copy is populated only by an explicit sync/generate call; application
startup never regenerates data.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.errors import DomainError
from backend.app.db.models import Dish

REQUIRED_COLUMNS = {
    "dish_id", "dish_name", "category", "meal_type", "vegetarian_flag",
    "default_unit", "prep_lead_minutes", "batch_min", "batch_max",
    "kitchen_capacity_per_interval",
}


def _bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _validate_menu_frame(df: pd.DataFrame, source: str) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise DomainError(
            "MENU_SCHEMA_INVALID",
            f"{source} is missing required dishes columns",
            503,
            {"missing": sorted(missing)},
        )
    for col in ("prep_lead_minutes", "batch_min", "batch_max", "kitchen_capacity_per_interval"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            raise DomainError("MENU_SCHEMA_INVALID", f"{col} must be numeric", 503)
    if (df["batch_min"] <= 0).any() or (df["batch_max"] < df["batch_min"]).any():
        raise DomainError("MENU_CONSTRAINT_INVALID", "batch_min/batch_max bounds are invalid", 503)
    if (df["prep_lead_minutes"] < 0).any() or (df["kitchen_capacity_per_interval"] < 0).any():
        raise DomainError("MENU_CONSTRAINT_INVALID", "quantities cannot be negative", 503)
    if df["dish_id"].duplicated().any():
        raise DomainError("MENU_SCHEMA_INVALID", "duplicate dish_id values", 503)
    return df


def load_menu_catalogue(path: str | Path | None = None) -> list[dict]:
    settings = get_settings()
    source = Path(path) if path else settings.menu_seed_file
    if not source.exists():
        raise DomainError(
            "MENU_SEED_MISSING",
            f"menu seed file not found: {source}",
            503,
            {"path": str(source)},
        )
    df = pd.read_csv(source)
    df = _validate_menu_frame(df, source.name)
    items = []
    for row in df.to_dict("records"):
        items.append(
            {
                "id": str(row["dish_id"]),
                "external_id": str(row["dish_id"]),
                "name": str(row["dish_name"]),
                "category": str(row["category"]),
                "meal_type": str(row["meal_type"]),
                "vegetarian_flag": _bool(row["vegetarian_flag"]),
                "default_unit": str(row["default_unit"]),
                "typical_portion_size": (
                    None if pd.isna(row.get("typical_portion_size")) else float(row["typical_portion_size"])
                ),
                "prep_lead_minutes": int(row["prep_lead_minutes"]),
                "batch_min": float(row["batch_min"]),
                "batch_max": float(row["batch_max"]),
                "kitchen_capacity_per_interval": float(row["kitchen_capacity_per_interval"]),
                "menu_source": str(row.get("menu_source") or "starter_seed"),
                "source_date": None if pd.isna(row.get("source_date")) else pd.Timestamp(row["source_date"]).date(),
                "is_synthetic": _bool(row.get("is_synthetic", True)),
            }
        )
    return items


def upsert_menu(db: Session) -> int:
    count = 0
    for item in load_menu_catalogue():
        existing = db.scalar(select(Dish).where(Dish.external_id == item["external_id"]))
        if existing is None:
            db.add(Dish(**item))
        else:
            for key, value in item.items():
                if key != "id":
                    setattr(existing, key, value)
        count += 1
    db.flush()
    return count


def list_dishes(
    db: Session,
    meal_type: str | None = None,
    category: str | None = None,
    vegetarian_flag: bool | None = None,
) -> list[Dish]:
    stmt = select(Dish).order_by(Dish.external_id)
    if meal_type:
        stmt = stmt.where(Dish.meal_type == meal_type)
    if category:
        stmt = stmt.where(Dish.category == category)
    if vegetarian_flag is not None:
        stmt = stmt.where(Dish.vegetarian_flag == vegetarian_flag)
    return list(db.scalars(stmt).all())
