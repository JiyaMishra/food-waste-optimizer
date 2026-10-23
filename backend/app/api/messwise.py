"""MessWise API endpoints for kitchen staff dashboard, agents, weather, and chatbot.

Mounted at both /api and /api/v1 so any route resolution succeeds seamlessly.
"""
from __future__ import annotations

import logging
from typing import Any, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query

from backend.app.services.dataset_service import (
    list_available_dates,
    list_meals,
    list_dishes_for_selection,
    get_meal_context,
    get_record,
)
from backend.app.services.preference_service import analyze_food_preference
from backend.app.services.demand_forecasting_service import predict_demand, get_model_artifact
from backend.app.services.waste_diagnosis_service import diagnose_waste
from backend.app.services.kitchen_optimization_service import optimize_kitchen_plan
from backend.app.services.feedback_learning_service import (
    validate_and_record_outcome,
    evaluate_model_performance,
    list_recorded_outcomes,
)
from backend.app.services.weather_service import get_weather_for_meal, get_weather_config
from backend.app.services.suggestion_service import (
    generate_smart_suggestions,
    dismiss_suggestion,
    complete_suggestion,
)
from backend.app.services.chatbot_service import handle_chat_message

logger = logging.getLogger("food_optimizer.messwise_api")

router = APIRouter(tags=["MessWise Kitchen System"])


# --- Request & Response Models ---

class PredictDemandRequest(BaseModel):
    food_item: str
    date: str
    meal: str
    attendance: Optional[int] = None
    exam_intensity: Optional[float] = None
    temperature_c: Optional[float] = None
    rainfall_mm: Optional[float] = None
    preference_score: Optional[float] = None


class AnalyzeWasteRequest(BaseModel):
    food_item: str
    meal: Optional[str] = None
    date: Optional[str] = None
    prepared_portions: Optional[float] = None
    consumed_portions: Optional[float] = None
    leftover_portions: Optional[float] = None


class KitchenPlanRequest(BaseModel):
    food_item: str
    predicted_demand: int = Field(ge=0)
    meal: Optional[str] = None
    risk_level: Optional[str] = None
    kitchen_capacity: Optional[int] = 800


class MealOutcomeRequest(BaseModel):
    date: str
    meal: str
    food_item: str
    prepared_portions: float = Field(ge=0)
    actual_consumers: float = Field(ge=0)
    leftover_portions: float = Field(ge=0)
    predicted_consumers: Optional[float] = None


class ChatRequest(BaseModel):
    message: str
    food_item: Optional[str] = "White Rice"
    meal: Optional[str] = "Lunch"
    date: Optional[str] = "2026-08-04"
    attendance: Optional[int] = None


class SuggestionActionRequest(BaseModel):
    suggestion_id: str
    action: str = Field(description="'dismiss' or 'complete'")


# --- Endpoints ---

@router.get("/health")
def get_health() -> dict[str, Any]:
    artifact = get_model_artifact()
    weather_cfg = get_weather_config()
    return {
        "status": "ok",
        "system": "MessWise AI-Powered Food Waste Optimization System",
        "model_version": artifact.get("model_version", "rf_v1"),
        "model_test_mae": artifact.get("test_mae", 3.5),
        "model_baseline_mae": artifact.get("baseline_mae", 0.49),
        "weather_integration": {
            "has_api_key": bool(weather_cfg.get("api_key")),
            "city": weather_cfg.get("city"),
        },
        "agents": [
            "Food Preference Agent",
            "Demand Forecasting Agent",
            "Waste Diagnosis Agent",
            "Kitchen Optimization Agent",
            "Feedback & Learning Agent",
        ],
        "synthetic_notice": "Academic project simulation. Sourced from synthetic menu dataset.",
    }


@router.get("/menu")
def get_menu(
    target_date: Optional[str] = Query(default=None, alias="date"),
    meal: Optional[str] = None,
) -> dict[str, Any]:
    available_dates = list_available_dates()
    effective_date = target_date or (available_dates[0] if available_dates else "2026-08-04")
    effective_meal = meal or "Lunch"
    dishes = list_dishes_for_selection(effective_date, effective_meal)
    return {
        "dates": available_dates,
        "meals": list_meals(),
        "selected_date": effective_date,
        "selected_meal": effective_meal,
        "dishes": dishes,
        "count": len(dishes),
    }


@router.get("/context")
def get_context(
    target_date: str = Query(default="2026-08-04", alias="date"),
    meal: str = "Lunch",
    food_item: Optional[str] = "White Rice",
    demo_weather: Optional[str] = None,
) -> dict[str, Any]:
    meal_ctx = get_meal_context(target_date, meal)
    weather = get_weather_for_meal(target_date, meal=meal, demo_mode=demo_weather)
    pref = analyze_food_preference(food_item or "White Rice", meal=meal)

    # Disclose which information is real, synthetic, historical, or estimated
    provenance = {
        "attendance": "Estimated daily resident count (synthetic roster)",
        "exam_intensity": "Academic timetable index 0.0 - 1.0 (synthetic)",
        "weather": f"{weather.get('source')} ({'Live forecast' if weather.get('is_live') else 'Historical/Simulated'})",
        "dish_preference": f"Synthetic liking score scaled to 0-100 ({pref.get('confidence')} confidence)",
        "dish_history": "August 2026 synthetic cafeteria records",
    }

    return {
        "date": target_date,
        "meal": meal,
        "food_item": food_item,
        "attendance_estimate": meal_ctx.get("hostel_attendance_estimate", 450),
        "exam_intensity": meal_ctx.get("exam_intensity", 0.35),
        "day_of_week": meal_ctx.get("day_of_week", "Tuesday"),
        "is_weekend": meal_ctx.get("is_weekend", 0),
        "weather": weather,
        "food_preference": pref,
        "provenance": provenance,
    }


@router.get("/weather")
def get_weather(
    target_date: str = Query(default="2026-08-04", alias="date"),
    meal: str = "Lunch",
    demo_mode: Optional[str] = None,
) -> dict[str, Any]:
    return get_weather_for_meal(target_date, meal=meal, demo_mode=demo_mode)


@router.get("/preference")
def get_preference(
    food_item: str = Query(..., alias="food_item"),
    meal: Optional[str] = None,
) -> dict[str, Any]:
    return analyze_food_preference(food_item, meal=meal)


@router.post("/predict-demand")
def predict_demand_endpoint(payload: PredictDemandRequest) -> dict[str, Any]:
    return predict_demand(
        food_item=payload.food_item,
        meal=payload.meal,
        date_str=payload.date,
        attendance=payload.attendance,
        exam_intensity=payload.exam_intensity,
        temperature_c=payload.temperature_c,
        rainfall_mm=payload.rainfall_mm,
        preference_score=payload.preference_score,
    )


@router.post("/analyze-waste")
def analyze_waste_endpoint(payload: AnalyzeWasteRequest) -> dict[str, Any]:
    return diagnose_waste(
        food_item=payload.food_item,
        meal=payload.meal,
        target_date=payload.date,
        prepared_portions=payload.prepared_portions,
        consumed_portions=payload.consumed_portions,
        leftover_portions=payload.leftover_portions,
    )


@router.post("/kitchen-plan")
def kitchen_plan_endpoint(payload: KitchenPlanRequest) -> dict[str, Any]:
    return optimize_kitchen_plan(
        food_item=payload.food_item,
        predicted_demand=payload.predicted_demand,
        meal=payload.meal,
        risk_level=payload.risk_level,
        kitchen_capacity=payload.kitchen_capacity or 800,
    )


@router.get("/suggestions")
def get_suggestions(
    food_item: str = Query(default="White Rice"),
    meal: str = Query(default="Lunch"),
    target_date: str = Query(default="2026-08-04", alias="date"),
    attendance: Optional[int] = None,
    demo_weather: Optional[str] = None,
) -> list[dict[str, Any]]:
    return generate_smart_suggestions(
        food_item=food_item,
        meal=meal,
        date_str=target_date,
        attendance=attendance,
        demo_weather=demo_weather,
    )


@router.post("/suggestions/action")
def update_suggestion_action(payload: SuggestionActionRequest) -> dict[str, Any]:
    if payload.action == "dismiss":
        dismiss_suggestion(payload.suggestion_id)
    elif payload.action == "complete":
        complete_suggestion(payload.suggestion_id)
    else:
        raise HTTPException(status_code=400, detail="Action must be 'dismiss' or 'complete'")
    return {"status": "ok", "suggestion_id": payload.suggestion_id, "action": payload.action}


@router.post("/chat")
def chat_endpoint(payload: ChatRequest) -> dict[str, Any]:
    return handle_chat_message(
        message=payload.message,
        active_dish=payload.food_item or "White Rice",
        active_meal=payload.meal or "Lunch",
        active_date=payload.date or "2026-08-04",
        active_attendance=payload.attendance,
    )


@router.post("/meal-outcomes")
def submit_meal_outcome(payload: MealOutcomeRequest) -> dict[str, Any]:
    res = validate_and_record_outcome(
        date_str=payload.date,
        meal=payload.meal,
        food_item=payload.food_item,
        prepared_portions=payload.prepared_portions,
        actual_consumers=payload.actual_consumers,
        leftover_portions=payload.leftover_portions,
        predicted_consumers=payload.predicted_consumers,
    )
    if not res.get("success", True) and "errors" in res:
        raise HTTPException(status_code=400, detail={"errors": res["errors"], "message": res.get("message")})
    return res


@router.get("/performance")
def get_performance() -> dict[str, Any]:
    perf = evaluate_model_performance()
    outcomes = list_recorded_outcomes(limit=25)
    artifact = get_model_artifact()
    return {
        "evaluation": perf,
        "recorded_outcomes": outcomes,
        "model_metadata": {
            "version": artifact.get("model_version", "rf_v1"),
            "training_samples": artifact.get("training_samples", 973),
            "test_mae": artifact.get("test_mae", 3.5),
            "baseline_mae": artifact.get("baseline_mae", 0.49),
            "r2": artifact.get("test_r2", 0.99),
            "target": artifact.get("target", "expected_consumers"),
            "features": artifact.get("all_features", []),
        },
    }


@router.get("/agent-status")
def get_agent_status() -> dict[str, Any]:
    artifact = get_model_artifact()
    return {
        "agents": [
            {
                "id": "agent_1_preference",
                "name": "Food Preference Agent",
                "status": "active",
                "type": "deterministic_scoring",
                "purpose": "Calculates dish liking score (0-100) and distinguishes popularity from demand.",
            },
            {
                "id": "agent_2_forecasting",
                "name": "Demand Forecasting Agent",
                "status": "active",
                "type": "machine_learning",
                "model_version": artifact.get("model_version", "rf_v1"),
                "purpose": "Predicts expected diner count using Random Forest with attendance bounds.",
            },
            {
                "id": "agent_3_waste",
                "name": "Waste Diagnosis Agent",
                "status": "active",
                "type": "rule_based_diagnosis",
                "purpose": "Identifies dishes at risk of high leftovers (>8%) and analyzes root causes.",
            },
            {
                "id": "agent_4_kitchen",
                "name": "Kitchen Optimization Agent",
                "status": "active",
                "type": "split_batch_optimizer",
                "purpose": "Converts forecasts into initial batches, staged reserves, and recipe yields.",
            },
            {
                "id": "agent_5_learning",
                "name": "Feedback & Learning Agent",
                "status": "active",
                "type": "sqlite_persistence",
                "purpose": "Validates post-meal outcomes, calculates MAE and bias, and detects drift.",
            },
        ]
    }
