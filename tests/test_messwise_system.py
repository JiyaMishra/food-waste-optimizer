"""Comprehensive tests for the MessWise Food Waste Optimization System.

Tests all five agents, model safety, recipe yields, weather fallback,
smart suggestions, chatbot, edge cases, and post-meal validations.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.dataset_service import (
    get_dataset,
    get_dish_history,
    list_available_dates,
    list_dishes_for_selection,
)
from backend.app.services.demand_forecasting_service import (
    get_model_artifact,
    predict_demand,
)
from backend.app.services.feedback_learning_service import (
    evaluate_model_performance,
    validate_and_record_outcome,
)
from backend.app.services.kitchen_optimization_service import optimize_kitchen_plan
from backend.app.services.preference_service import analyze_food_preference
from backend.app.services.recipe_service import calculate_ingredients, get_recipe_for_dish
from backend.app.services.suggestion_service import (
    dismiss_suggestion,
    generate_smart_suggestions,
    reset_suggestion_statuses,
)
from backend.app.services.waste_diagnosis_service import diagnose_waste
from backend.app.services.weather_service import get_weather_for_meal
from backend.app.services.chatbot_service import handle_chat_message

client = TestClient(app)


# 1. Dataset & Schema Tests
def test_dataset_loading_and_columns():
    df = get_dataset()
    assert not df.empty
    assert len(df) >= 900
    expected_cols = {
        "date",
        "meal",
        "food_item",
        "synthetic_liking_score",
        "exam_intensity",
        "temperature_c",
        "rainfall_mm",
        "is_weekend",
        "hostel_attendance_estimate",
        "historical_demand_rate",
        "expected_consumers",
        "prepared_portions",
        "consumed_portions",
        "leftover_portions",
        "waste_rate_pct",
    }
    assert expected_cols.issubset(set(df.columns))


# 2. Target Leakage Prevention Test
def test_prevention_of_target_leakage():
    artifact = get_model_artifact()
    features_used = set(artifact["all_features"])
    forbidden = {
        "expected_consumers",
        "consumed_portions",
        "leftover_portions",
        "waste_rate_pct",
        "prepared_portions",
    }
    leakage = features_used.intersection(forbidden)
    assert not leakage, f"Target leakage detected in model features: {leakage}"


# 3. Agent 1: Food Preference Scoring
def test_preference_agent_known_dish():
    res = analyze_food_preference("Aloo Paratha", meal="Breakfast")
    assert res["agent"] == "food_preference"
    assert 0 <= res["preference_score"] <= 100
    assert len(res["evidence"]) > 0
    assert res["confidence"] in ["low", "medium", "high"]
    assert "ratings in this dataset are simulated" in res["warnings"][-1].lower()


def test_preference_agent_unknown_dish():
    res = analyze_food_preference("Nonexistent Dragon Dish", meal="Lunch")
    assert res["agent"] == "food_preference"
    assert res["preference_score"] == 50
    assert res["confidence"] == "low"
    assert len(res["warnings"]) > 0


# 4. Agent 2: Demand Prediction & Bounds
def test_demand_prediction_bounds_and_attendance_cap():
    # Model prediction cannot exceed attendance estimate
    low_attendance = 150
    res = predict_demand(
        food_item="White Rice",
        meal="Lunch",
        date_str="2026-08-04",
        attendance=low_attendance,
        exam_intensity=0.9,
    )
    assert res["agent"] == "demand_forecasting"
    assert res["model_version"] == "rf_v1"
    assert res["predicted_consumers"] <= low_attendance
    assert res["predicted_consumers"] >= 0
    assert "uncertainty" in res


def test_demand_prediction_zero_attendance():
    res = predict_demand(
        food_item="White Rice",
        meal="Lunch",
        date_str="2026-08-04",
        attendance=0,
    )
    assert res["predicted_consumers"] >= 0


# 5. Agent 3: Waste Diagnosis Calculation & Zero Handling
def test_waste_diagnosis_calculation():
    # Test valid calculation
    res = diagnose_waste(
        food_item="Curd",
        meal="Breakfast",
        prepared_portions=300,
        leftover_portions=30,
    )
    assert res["observed_waste_rate"] == 10.0
    assert res["risk_level"] == "medium"
    assert len(res["recommended_actions"]) > 0


def test_waste_diagnosis_zero_prepared_portions():
    # Zero prepared portions should not raise ZeroDivisionError
    res = diagnose_waste(
        food_item="Curd",
        meal="Breakfast",
        prepared_portions=0,
        leftover_portions=0,
    )
    assert res["observed_waste_rate"] == 0.0
    assert res["risk_level"] == "low"


# 6. Agent 4: Kitchen Optimization & Batch Splitting
def test_kitchen_optimization_split_batch():
    res = optimize_kitchen_plan("White Rice", predicted_demand=300, meal="Lunch")
    assert res["agent"] == "kitchen_optimization"
    assert res["initial_batch_servings"] > 0
    assert res["reserve_servings"] > 0
    assert res["initial_batch_servings"] + res["reserve_servings"] == 300
    assert res["replenishment_threshold"] > 0
    assert "check" in res["replenishment_check"].lower()


def test_kitchen_optimization_small_demand():
    res = optimize_kitchen_plan("White Rice", predicted_demand=15, meal="Lunch")
    assert res["initial_batch_servings"] == 15
    assert res["reserve_servings"] == 0


# 7. Recipe Conversion & Missing Recipe Yields
def test_recipe_conversion_verified_dish():
    res = calculate_ingredients("White Rice", servings=200)
    assert res["has_validated_recipe"] is True
    assert len(res["ingredient_requirements"]) > 0
    # Raw rice for 100 servings is 7.0kg -> for 200 is 14.0kg
    rice_ing = next(i for i in res["ingredient_requirements"] if "rice" in i["ingredient"].lower())
    assert rice_ing["quantity"] == 14.0


def test_recipe_conversion_missing_dish():
    res = calculate_ingredients("Unknown Exotic Salad", servings=100)
    assert res["has_validated_recipe"] is False
    assert res["ingredient_requirements"] == []
    assert any("no verified recipe yield" in a.lower() for a in res["assumptions"])


# 8. Weather Service: Live, Fallback, Demo, Unavailable
def test_weather_demo_mode():
    weather = get_weather_for_meal("2026-08-04", meal="Lunch", demo_mode="rain_storm")
    assert weather["source"] == "demo_simulation"
    assert weather["rain_expected_during_meal"] is True
    assert weather["rainfall_mm"] == 18.5


def test_weather_historical_csv_lookup():
    # August 2026 dates exist in CSV
    weather = get_weather_for_meal("2026-08-04", meal="Lunch")
    assert weather["source"] in ["dataset_historical", "live_openweathermap"]
    assert weather["temperature_c"] is not None


def test_weather_unavailable_date():
    # Year 2099 date with no API key should be cleanly unavailable
    weather = get_weather_for_meal("2099-12-31", meal="Lunch")
    if not weather["is_live"]:
        assert weather["source"] == "unavailable"
        assert weather["temperature_c"] is None


# 9. Smart Suggestions & Rain Trigger
def test_smart_suggestions_rain_trigger():
    reset_suggestion_statuses()
    suggestions = generate_smart_suggestions(
        food_item="White Rice",
        meal="Lunch",
        date_str="2026-08-04",
        demo_weather="rain_storm",
    )
    categories = [s["category"] for s in suggestions]
    assert "weather" in categories
    rain_s = next(s for s in suggestions if s["category"] == "weather")
    assert "rain" in rain_s["title"].lower()
    assert "reserve" in rain_s["recommended_action"].lower() or "stage" in rain_s["recommended_action"].lower()


def test_smart_suggestions_deduplication_and_dismissal():
    reset_suggestion_statuses()
    suggs = generate_smart_suggestions("White Rice", "Lunch", "2026-08-04", demo_weather="rain_storm")
    first_id = suggs[0]["id"]
    dismiss_suggestion(first_id)
    suggs_after = generate_smart_suggestions("White Rice", "Lunch", "2026-08-04", demo_weather="rain_storm")
    dismissed_item = next(s for s in suggs_after if s["id"] == first_id)
    assert dismissed_item["is_dismissed"] is True


# 10. Agent 5: Feedback & Learning Validation & Edge Cases
def test_feedback_learning_validation_errors():
    # Negative prepared portions
    res = validate_and_record_outcome(
        date_str="2026-08-04",
        meal="Lunch",
        food_item="White Rice",
        prepared_portions=-10,
        actual_consumers=50,
        leftover_portions=5,
    )
    assert res["success"] is False
    assert any("negative" in err for err in res["errors"])

    # Leftover greater than prepared
    res2 = validate_and_record_outcome(
        date_str="2026-08-04",
        meal="Lunch",
        food_item="White Rice",
        prepared_portions=100,
        actual_consumers=50,
        leftover_portions=150,
    )
    assert res2["success"] is False
    assert any("cannot exceed" in err for err in res2["errors"])


def test_feedback_learning_valid_record():
    res = validate_and_record_outcome(
        date_str="2026-08-04",
        meal="Lunch",
        food_item="White Rice",
        prepared_portions=350,
        actual_consumers=330,
        leftover_portions=20,
        predicted_consumers=340,
    )
    assert res["agent"] == "feedback_learning"
    assert res["records_validated"] >= 1
    assert res["mae"] is not None
    assert res["forecast_bias"] is not None


# 11. Chatbot Tool Calling & Queries
def test_chatbot_demand_query():
    resp = handle_chat_message("How much rice should we prepare for lunch?", active_dish="White Rice")
    assert "servings" in resp["reply"].lower()
    assert "predict_demand" in resp["tools_called"]
    assert "generate_kitchen_plan" in resp["tools_called"]


def test_chatbot_rain_query():
    resp = handle_chat_message("Is rain expected during lunch?", active_dish="White Rice", active_meal="Lunch")
    assert "get_weather_forecast" in resp["tools_called"]
    assert "rain" in resp["reply"].lower() or "weather" in resp["reply"].lower()


def test_chatbot_attendance_override_query():
    resp = handle_chat_message(
        "How much rice should we prepare if only 400 students attend?",
        active_dish="White Rice",
        active_meal="Lunch",
    )
    assert "predict_demand" in resp["tools_called"]
    assert resp["data"]["prediction"]["input_summary"]["attendance_estimate"] == 400


def test_chatbot_why_prepare_query():
    resp = handle_chat_message(
        "Why are we preparing this quantity?",
        active_dish="White Rice",
        active_meal="Lunch",
    )
    assert "predict_demand" in resp["tools_called"]
    assert "diagnose_waste" in resp["tools_called"]
    assert "why" in resp["reply"].lower() or "attendance" in resp["reply"].lower()


# 12. Full FastAPI End-to-End Route Tests
def test_fastapi_endpoints():
    # 1. Health
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["system"].startswith("MessWise")

    # 2. Menu
    r = client.get("/api/menu?date=2026-08-04&meal=Lunch")
    assert r.status_code == 200
    assert "White Rice" in r.json()["dishes"]

    # 3. Context
    r = client.get("/api/context?date=2026-08-04&meal=Lunch&food_item=White Rice")
    assert r.status_code == 200
    assert r.json()["attendance_estimate"] > 0

    # 4. Predict Demand
    r = client.post(
        "/api/predict-demand",
        json={"food_item": "White Rice", "date": "2026-08-04", "meal": "Lunch", "attendance": 530, "exam_intensity": 0.9},
    )
    assert r.status_code == 200
    assert r.json()["predicted_consumers"] > 0

    # 5. Kitchen Plan
    r = client.post(
        "/api/kitchen-plan",
        json={"food_item": "White Rice", "predicted_demand": 320, "meal": "Lunch"},
    )
    assert r.status_code == 200
    assert r.json()["initial_batch_servings"] == 224

    # 6. Suggestions
    r = client.get("/api/suggestions?food_item=White Rice&meal=Lunch&date=2026-08-04")
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    # 7. Chat
    r = client.post(
        "/api/chat",
        json={"message": "Why are we preparing this quantity?", "food_item": "White Rice", "meal": "Lunch", "date": "2026-08-04"},
    )
    assert r.status_code == 200
    assert "reply" in r.json()

    # 8. Performance
    r = client.get("/api/performance")
    assert r.status_code == 200
    assert "evaluation" in r.json()

    # 9. Agent Status
    r = client.get("/api/agent-status")
    assert r.status_code == 200
    assert len(r.json()["agents"]) == 5
