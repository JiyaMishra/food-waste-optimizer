"""Agent 5: Feedback & Learning Agent.

Collects and validates post-meal operational records, calculates MAE and forecast bias,
persists records in SQLite, and determines when model retraining is warranted.
"""
from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import numpy as np

logger = logging.getLogger("food_optimizer.feedback_agent")

DB_PATH = Path("backend/data/food_optimizer.db")


def _init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messwise_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                meal TEXT NOT NULL,
                food_item TEXT NOT NULL,
                predicted_consumers REAL NOT NULL,
                actual_consumers REAL NOT NULL,
                prepared_portions REAL NOT NULL,
                leftover_portions REAL NOT NULL,
                waste_rate_pct REAL NOT NULL,
                absolute_error REAL NOT NULL,
                bias REAL NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


_init_db()


def validate_and_record_outcome(
    date_str: str,
    meal: str,
    food_item: str,
    prepared_portions: float,
    actual_consumers: float,
    leftover_portions: float,
    predicted_consumers: float | None = None,
) -> dict[str, Any]:
    """Validate submitted meal records and persist to SQLite database."""
    _init_db()

    # 1. Validation checks
    errors = []
    if prepared_portions < 0:
        errors.append("prepared_portions cannot be negative.")
    if actual_consumers < 0:
        errors.append("actual_consumers cannot be negative.")
    if leftover_portions < 0:
        errors.append("leftover_portions cannot be negative.")
    if leftover_portions > prepared_portions:
        errors.append(
            f"leftover_portions ({leftover_portions}) cannot exceed prepared_portions ({prepared_portions})."
        )

    if errors:
        return {
            "success": False,
            "agent": "feedback_learning",
            "errors": errors,
            "message": "Validation failed: invalid outcome record rejected.",
        }

    # If predicted_consumers wasn't provided, estimate from demand service or default
    if predicted_consumers is None:
        predicted_consumers = float(actual_consumers)

    # 2. Computations
    waste_rate = (
        round((leftover_portions / prepared_portions) * 100.0, 2)
        if prepared_portions > 0
        else 0.0
    )
    # Absolute error = |actual - predicted|
    abs_error = round(abs(actual_consumers - predicted_consumers), 2)
    # Bias = predicted - actual (positive = overprediction)
    bias = round(predicted_consumers - actual_consumers, 2)

    created_at = datetime.now(timezone.utc).isoformat()

    # 3. Persist to SQLite
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messwise_outcomes (
                date, meal, food_item, predicted_consumers, actual_consumers,
                prepared_portions, leftover_portions, waste_rate_pct, absolute_error, bias, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                date_str,
                meal,
                food_item,
                predicted_consumers,
                actual_consumers,
                prepared_portions,
                leftover_portions,
                waste_rate,
                abs_error,
                bias,
                created_at,
            ),
        )
        conn.commit()

    # 4. Compute updated learning summary
    return evaluate_model_performance()


def evaluate_model_performance() -> dict[str, Any]:
    """Calculate MAE, forecast bias, and waste-rate trend across all validated outcomes."""
    _init_db()
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT absolute_error, bias, waste_rate_pct, date, created_at
            FROM messwise_outcomes
            ORDER BY id ASC
            """
        )
        rows = cursor.fetchall()

    if not rows:
        return {
            "agent": "feedback_learning",
            "records_validated": 0,
            "mae": None,
            "forecast_bias": None,
            "waste_rate_trend": None,
            "retraining_recommended": False,
            "message": "No post-meal outcome records registered yet.",
            "warnings": ["Feedback database has zero records. Record meal outcomes to begin tracking."],
        }

    abs_errors = [r[0] for r in rows]
    biases = [r[1] for r in rows]
    waste_rates = [r[2] for r in rows]

    mae = round(float(np.mean(abs_errors)), 2)
    mean_bias = round(float(np.mean(biases)), 2)
    avg_waste = round(float(np.mean(waste_rates)), 2)

    # Waste rate trend: compare last 5 vs first 5 if enough data
    if len(waste_rates) >= 6:
        first_half = np.mean(waste_rates[: len(waste_rates) // 2])
        second_half = np.mean(waste_rates[len(waste_rates) // 2 :])
        trend = round(float(second_half - first_half), 2)
    else:
        trend = 0.0

    # Recommend retraining if >= 10 records and MAE is notably high (> 15) or bias is large (|bias| > 10)
    retraining_recommended = len(rows) >= 10 and (mae > 15.0 or abs(mean_bias) > 10.0)

    bias_description = (
        f"Overpredicting by an average of {mean_bias} servings"
        if mean_bias > 0
        else f"Underpredicting by an average of {abs(mean_bias)} servings"
    )

    return {
        "agent": "feedback_learning",
        "records_validated": len(rows),
        "mae": mae,
        "forecast_bias": mean_bias,
        "bias_direction": bias_description,
        "average_waste_rate": avg_waste,
        "waste_rate_trend": trend,
        "retraining_recommended": retraining_recommended,
        "recent_outcomes_sample": len(rows),
        "warnings": [],
        "explanation": (
            f"Across {len(rows)} recorded meals, the system achieved a Mean Absolute Error (MAE) of {mae} portions "
            f"with a mean bias of {mean_bias:+.1f} portions. "
            + ("Retraining is recommended due to accumulated drift." if retraining_recommended else "Model accuracy remains stable within acceptable bounds.")
        ),
    }


def list_recorded_outcomes(limit: int = 50) -> list[dict[str, Any]]:
    _init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, date, meal, food_item, predicted_consumers, actual_consumers,
                   prepared_portions, leftover_portions, waste_rate_pct, absolute_error, bias, created_at
            FROM messwise_outcomes
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
