from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from backend.app.db.models import Dish, MenuItem
from backend.app.db.session import SessionLocal

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fresh_database_migrates_from_zero(tmp_path):
    database = tmp_path / "fresh.db"
    environment = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{database.as_posix()}",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    connection = sqlite3.connect(database)
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    expected = {
        "dishes", "menu_items", "synthetic_context", "academic_slots",
        "availability_snapshots", "meal_runs", "simulation_events", "outcomes",
        "predictions", "batch_plans", "agent_traces", "diagnoses", "interventions",
        "evaluation_runs", "feedback_events",
    }
    assert expected <= tables
    version = list(connection.execute("SELECT version_num FROM alembic_version"))
    assert version
    connection.close()


def test_check_constraint_rejects_negative_prep_lead():
    session = SessionLocal()
    try:
        session.add(
            Dish(
                external_id="BAD1",
                name="Bad dish",
                meal_type="breakfast",
                prep_lead_minutes=-1,
                batch_min=10,
                batch_max=20,
                kitchen_capacity_per_interval=100,
                is_synthetic=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_foreign_key_rejects_unknown_dish():
    session = SessionLocal()
    try:
        session.add(
            MenuItem(
                dish_id="missing-dish-id",
                date=date(2026, 9, 1),
                meal_id="MEALBAD",
                meal_type="breakfast",
                is_synthetic=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_menu_item_uniqueness_and_availability_check():
    session = SessionLocal()
    try:
        dish = Dish(
            external_id="OK1",
            name="Ok dish",
            meal_type="breakfast",
            prep_lead_minutes=10,
            batch_min=10,
            batch_max=20,
            kitchen_capacity_per_interval=100,
            is_synthetic=True,
        )
        session.add(dish)
        session.flush()
        session.add(
            MenuItem(
                dish_id=dish.id,
                date=date(2026, 9, 1),
                meal_id="MEAL1",
                meal_type="breakfast",
                is_synthetic=True,
            )
        )
        session.flush()
        session.add(
            MenuItem(
                dish_id=dish.id,
                date=date(2026, 9, 1),
                meal_id="MEAL1",
                meal_type="breakfast",
                is_synthetic=True,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_database_session_enforces_foreign_keys():
    session = SessionLocal()
    try:
        assert session.execute(text("PRAGMA foreign_keys")).scalar() == 1
    finally:
        session.close()
