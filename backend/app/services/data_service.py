"""Thin integration layer around Person A's synthetic data and validation modules."""
from __future__ import annotations

import os
import threading
from contextlib import contextmanager
from datetime import date, time
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import PROJECT_ROOT, get_settings
from backend.app.core.errors import DomainError
from backend.app.db.models import AcademicSlot, Dish, MenuItem, SyntheticContext
from backend.app.services.menu_service import load_menu_catalogue
from src.data.synthetic_data import generate_synthetic_data
from src.data.validation import validate_dataset

_GENERATOR_LOCK = threading.Lock()


@contextmanager
def _person_a_working_directory():
    """Person A's generator resolves its menu seed relative to the repo root."""
    with _GENERATOR_LOCK:
        previous = os.getcwd()
        os.chdir(PROJECT_ROOT)
        try:
            yield
        finally:
            os.chdir(previous)


def generate_dataset(months: int, seed: int, residents: int, validate_after: bool = True) -> dict:
    settings = get_settings()
    settings.ensure_directories()
    try:
        with _person_a_working_directory():
            output = generate_synthetic_data(
                output_dir=str(settings.data_path),
                months=months,
                seed=seed,
                residents=residents,
            )
    except Exception as exc:  # Person A's validation/IO errors must be visible to the client
        raise DomainError(
            "SYNTHETIC_DATA_GENERATION_FAILED",
            f"Person A synthetic data generation failed: {exc}",
            500,
        ) from exc
    report = validate_dataset(str(output)) if validate_after else None
    if report is not None and not report["ok"]:
        raise DomainError(
            "SYNTHETIC_DATA_INVALID",
            "Generated data failed Person A validation",
            500,
            report,
        )
    return {
        "ok": report["ok"] if report is not None else True,
        "output_dir": str(Path(output).resolve()),
        "months": months,
        "seed": seed,
        "residents": residents,
        "scenario_id": "synthetic_baseline_v1",
        "dataset_version": "1.0.0",
        "validation": report,
    }


def validate_generated_data() -> dict:
    settings = get_settings()
    if not settings.data_path.exists():
        raise DomainError(
            "DATA_DIRECTORY_MISSING",
            f"generated data directory does not exist: {settings.data_path}",
            404,
            {"path": str(settings.data_path)},
        )
    try:
        report = validate_dataset(str(settings.data_path))
    except Exception as exc:
        raise DomainError("DATA_VALIDATION_FAILED", f"Validation failed: {exc}", 500) from exc
    return report


def _to_time(value) -> time:
    parsed = pd.to_datetime(str(value), format="%H:%M", errors="raise")
    return parsed.time()


def _upsert_dish_from_menu(db: Session, row: dict, seed_by_id: dict[str, dict]) -> Dish:
    external_id = str(row["dish_id"])
    seed = seed_by_id.get(external_id)
    dish = db.scalar(select(Dish).where(Dish.external_id == external_id))
    values = {
        "external_id": external_id,
        "name": str(row["dish_name"]),
        "category": str(seed.get("category", "uncategorised")) if seed else "uncategorised",
        "meal_type": str(row["meal_type"]),
        "vegetarian_flag": bool(row.get("vegetarian_flag", True)),
        "default_unit": str(seed.get("default_unit", "portions")) if seed else "portions",
        "typical_portion_size": seed.get("typical_portion_size") if seed else None,
        "prep_lead_minutes": int(seed.get("prep_lead_minutes", 30)) if seed else 30,
        "batch_min": float(seed.get("batch_min", 20)) if seed else 20.0,
        "batch_max": float(seed.get("batch_max", 500)) if seed else 500.0,
        "kitchen_capacity_per_interval": (
            float(seed.get("kitchen_capacity_per_interval", 200)) if seed else 200.0
        ),
        "menu_source": str(seed.get("menu_source", "generated_menu")) if seed else "generated_menu",
        "source_date": seed.get("source_date") if seed else None,
        "is_synthetic": True,
    }
    if dish is None:
        dish = Dish(**values)
        db.add(dish)
        db.flush()
    else:
        for key, value in values.items():
            setattr(dish, key, value)
    return dish


def sync_generated_data(db: Session) -> dict:
    settings = get_settings()
    report = validate_generated_data()
    if not report["ok"]:
        raise DomainError(
            "SYNTHETIC_DATA_INVALID",
            "Generated data failed Person A validation; sync aborted",
            422,
            report,
        )
    data_dir = settings.data_path
    seed_items = {
        str(item["external_id"]): item for item in load_menu_catalogue()
    }

    state = pd.read_csv(data_dir / "hostel_daily_state.csv", parse_dates=["date"])
    weather = pd.read_csv(data_dir / "weather_daily.csv", parse_dates=["date"])
    events = pd.read_csv(data_dir / "campus_events.csv")
    menu = pd.read_csv(data_dir / "menu_calendar.csv", parse_dates=["date"])
    slots = pd.read_csv(data_dir / "academic_slots.csv")

    scenario_id = str(state["scenario_id"].iloc[0]) if len(state) else "synthetic_baseline_v1"
    dataset_version = str(state["dataset_version"].iloc[0]) if len(state) else "1.0.0"

    event_by_date: dict[date, dict] = {}
    for row in events.to_dict("records"):
        event_by_date[pd.Timestamp(row["date"]).date()] = row
    weather_by_date = {
        pd.Timestamp(row["date"]).date(): row for row in weather.to_dict("records")
    }

    existing_context = {
        (row.date, row.hostel_id, row.mess_id, row.scenario_id): row
        for row in db.scalars(select(SyntheticContext)).all()
    }
    context_count = 0
    for row in state.to_dict("records"):
        day = pd.Timestamp(row["date"]).date()
        weather_row = weather_by_date.get(day, {})
        event = event_by_date.get(day)
        values = {
            "date": day,
            "hostel_id": str(row["hostel_id"]),
            "mess_id": str(row["mess_id"]),
            "capacity": int(row["capacity"]),
            "occupied_count": int(row["occupied_count"]),
            "occupancy_rate": float(row["occupancy_rate"]),
            "rain_mm": float(weather_row.get("rain_mm", 0) or 0),
            "temperature_c": float(weather_row.get("temperature_c", 0) or 0),
            "weather_label": str(weather_row.get("weather_label", "normal")),
            "event_id": str(event["event_id"]) if event is not None else None,
            "event_expected_participants": (
                int(event["expected_participants"]) if event is not None else None
            ),
            "scenario_id": scenario_id,
            "dataset_version": dataset_version,
            "is_synthetic": True,
        }
        key = (values["date"], values["hostel_id"], values["mess_id"], values["scenario_id"])
        existing = existing_context.get(key)
        if existing is None:
            db.add(SyntheticContext(**values))
        else:
            for field, value in values.items():
                setattr(existing, field, value)
        context_count += 1

    existing_slots = {
        (row.date, row.cohort_id, row.activity_type, row.start_time, row.end_time): row
        for row in db.scalars(select(AcademicSlot)).all()
    }
    slot_count = 0
    for row in slots.to_dict("records"):
        values = {
            "date": pd.Timestamp(row["date"]).date(),
            "cohort_id": str(row["cohort_id"]),
            "activity_type": str(row["activity_type"]),
            "start_time": _to_time(row["start_time"]),
            "end_time": _to_time(row["end_time"]),
            "location_id": str(row.get("location_id")) if pd.notna(row.get("location_id")) else None,
            "unavailable_share": None,
            "scenario_id": scenario_id,
            "is_synthetic": True,
        }
        key = (
            values["date"], values["cohort_id"], values["activity_type"],
            values["start_time"], values["end_time"],
        )
        existing = existing_slots.get(key)
        if existing is None:
            db.add(AcademicSlot(**values))
        else:
            existing.location_id = values["location_id"]
            existing.scenario_id = values["scenario_id"]
        slot_count += 1

    dish_by_external: dict[str, Dish] = {}
    for row in menu.to_dict("records"):
        external_id = str(row["dish_id"])
        if external_id not in dish_by_external:
            dish_by_external[external_id] = _upsert_dish_from_menu(db, row, seed_items)

    existing_menu = {(row.meal_id, row.dish_id) for row in db.scalars(select(MenuItem)).all()}
    menu_count = 0
    for row in menu.to_dict("records"):
        dish = dish_by_external[str(row["dish_id"])]
        key = (str(row["meal_id"]), dish.id)
        if key in existing_menu:
            continue
        db.add(
            MenuItem(
                dish_id=dish.id,
                date=pd.Timestamp(row["date"]).date(),
                meal_id=str(row["meal_id"]),
                meal_type=str(row["meal_type"]),
                is_synthetic=True,
            )
        )
        existing_menu.add(key)
        menu_count += 1
    db.flush()
    return {
        "data_dir": str(data_dir),
        "scenario_id": scenario_id,
        "dataset_version": dataset_version,
        "dishes_upserted": len(dish_by_external),
        "menu_items": menu_count,
        "context_rows": context_count,
        "academic_slots": slot_count,
        "message": "Synthetic data synced. No records were regenerated during startup.",
    }
