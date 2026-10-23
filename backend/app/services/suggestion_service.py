"""Proactive Smart Suggestion Engine for MessWise.

Generates actionable suggestions for mess workers based on live weather forecasts,
historical leftovers, attendance shifts, exam intensity, and dish preference.
Deduplicates suggestions and supports dismissal/completion tracking.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
import hashlib

from backend.app.services.dataset_service import get_meal_context, get_record, get_dish_history
from backend.app.services.preference_service import analyze_food_preference
from backend.app.services.waste_diagnosis_service import diagnose_waste
from backend.app.services.weather_service import get_weather_for_meal
from backend.app.services.feedback_learning_service import evaluate_model_performance

logger = logging.getLogger("food_optimizer.suggestion_service")

# In-memory storage for dismissed and completed suggestion IDs
_DISMISSED_IDS: set[str] = set()
_COMPLETED_IDS: set[str] = set()


def _make_id(category: str, food_item: str, date_str: str, meal: str) -> str:
    raw = f"{category}_{food_item}_{date_str}_{meal}".lower()
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def dismiss_suggestion(suggestion_id: str) -> None:
    _DISMISSED_IDS.add(suggestion_id)


def complete_suggestion(suggestion_id: str) -> None:
    _COMPLETED_IDS.add(suggestion_id)


def reset_suggestion_statuses() -> None:
    _DISMISSED_IDS.clear()
    _COMPLETED_IDS.clear()


def generate_smart_suggestions(
    food_item: str,
    meal: str,
    date_str: str,
    attendance: int | None = None,
    demo_weather: str | None = None,
) -> list[dict[str, Any]]:
    """Evaluate context and generate proactive, rule-based suggestions."""
    suggestions: list[dict[str, Any]] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. Weather Data & Rain Trigger
    weather = get_weather_for_meal(date_str, meal=meal, demo_mode=demo_weather)
    rain_mm = weather.get("rainfall_mm") or 0.0
    rain_expected = weather.get("rain_expected_during_meal", False)

    if rain_expected and rain_mm >= 2.0:
        s_id = _make_id("weather", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "weather",
                "severity": "warning",
                "title": f"Rain Forecast During {meal}",
                "message": f"Rain ({rain_mm:.1f} mm) is expected around {meal}. Check today's attendance before preparing the second batch of {food_item}.",
                "evidence": [
                    f"Weather source: {weather.get('source')} reporting {rain_mm:.1f}mm expected precipitation.",
                    f"Rain probability (PoP): {int(weather.get('pop', 0) * 100)}%.",
                ],
                "recommended_action": f"Stage dry/chilled ingredients for {food_item}, but do not cook the reserve batch until counter demand is confirmed.",
                "triggered_by": ["weather_rain_forecast >= 2.0mm"],
                "created_at": now_iso,
            }
        )

    # 2. Historical High-Waste Trigger
    waste_info = diagnose_waste(food_item, meal=meal, target_date=date_str)
    observed_waste = waste_info.get("observed_waste_rate")
    risk_level = waste_info.get("risk_level")

    if observed_waste is not None and observed_waste > 8.0:
        s_id = _make_id("waste", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "waste",
                "severity": "alert" if observed_waste > 12.0 else "warning",
                "title": f"High Leftover History for {food_item}",
                "message": f"{food_item} has had high leftovers recently (observed waste rate {observed_waste:.1f}%). Start with a smaller initial batch.",
                "evidence": waste_info.get("evidence", []) + waste_info.get("possible_factors", []),
                "recommended_action": f"Limit initial batch to 60% of forecast demand. Monitor tray depletion after 100 portions.",
                "triggered_by": [f"historical_waste_rate ({observed_waste:.1f}%) > 8.0% threshold"],
                "created_at": now_iso,
            }
        )

    # 3. Attendance Drop Trigger
    meal_ctx = get_meal_context(date_str, meal)
    current_attendance = (
        attendance
        if attendance is not None and attendance > 0
        else int(meal_ctx.get("hostel_attendance_estimate", 450))
    )
    baseline_attendance = 520  # Typical hostel baseline capacity

    if current_attendance < 450:
        s_id = _make_id("attendance", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "attendance",
                "severity": "info",
                "title": f"Lower Attendance Expected Today",
                "message": f"Today's attendance estimate ({current_attendance}) is lower than usual (baseline: ~{baseline_attendance}). Review the preparation plan before cooking the full quantity.",
                "evidence": [
                    f"Current estimate: {current_attendance} residents expected.",
                    f"Historical campus baseline: {baseline_attendance} residents.",
                    f"Reduction: {baseline_attendance - current_attendance} fewer potential diners.",
                ],
                "recommended_action": "Scale down initial batch size proportionally to avoid untouched leftover trays.",
                "triggered_by": [f"current_attendance ({current_attendance}) < 450 threshold"],
                "created_at": now_iso,
            }
        )

    # 4. Exam Intensity / Demand Uncertainty Trigger
    exam_intensity = float(meal_ctx.get("exam_intensity", 0.0))
    if exam_intensity >= 0.8:
        s_id = _make_id("demand_uncertain", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "demand",
                "severity": "warning",
                "title": f"High Exam Period — Dining Arrival Variance",
                "message": f"Demand is uncertain due to major examination period (exam intensity {exam_intensity:.1f}). Check the serving count before replenishing.",
                "evidence": [
                    f"Exam intensity index: {exam_intensity:.2f} / 1.0 (students often skip meals or eat at staggered hours).",
                ],
                "recommended_action": "Do not cook the reserve batch until counter staff confirm that lines are still forming 45 minutes into service.",
                "triggered_by": ["exam_intensity >= 0.8"],
                "created_at": now_iso,
            }
        )

    # 5. Popular Dish Trigger
    pref = analyze_food_preference(food_item, meal=meal)
    pref_score = pref.get("preference_score", 50)
    if pref_score >= 80:
        s_id = _make_id("popular", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "popularity",
                "severity": "info",
                "title": f"Popular Dish ({pref_score}/100 Rating)",
                "message": f"Students usually like {food_item}. Keep ingredients staged and ready for a possible second batch.",
                "evidence": pref.get("evidence", []),
                "recommended_action": "Ensure secondary batch ingredients are washed and chopped so kitchen turnaround takes less than 20 minutes if needed.",
                "triggered_by": [f"preference_score ({pref_score}) >= 80"],
                "created_at": now_iso,
            }
        )

    # 6. Forecast Mismatch Trigger (from Feedback & Learning Agent)
    perf = evaluate_model_performance()
    bias = perf.get("forecast_bias")
    if bias is not None and bias > 15.0:
        s_id = _make_id("bias", food_item, date_str, meal)
        suggestions.append(
            {
                "id": s_id,
                "category": "forecast_mismatch",
                "severity": "warning",
                "title": "Recent Model Overprediction Detected",
                "message": f"Recent actual consumption has been lower than predicted (avg bias +{bias:.1f} servings). Review the initial batch size before cooking.",
                "evidence": [
                    f"Verified feedback records indicate model is overpredicting demand by an average of {bias:.1f} servings.",
                ],
                "recommended_action": "Subtract 10-15 servings from the initial batch recommendation as a precaution.",
                "triggered_by": [f"historical_bias ({bias:.1f}) > 15.0"],
                "created_at": now_iso,
            }
        )

    # Decorate suggestions with user interaction status and filter dismissed if requested
    annotated = []
    for s in suggestions:
        sid = s["id"]
        is_dismissed = sid in _DISMISSED_IDS
        is_completed = sid in _COMPLETED_IDS
        annotated.append(
            {
                **s,
                "is_dismissed": is_dismissed,
                "is_completed": is_completed,
            }
        )

    return annotated
