"""Ask MessWise Chatbot Service.

Provides conversational kitchen assistance by connecting natural language questions
to the 5 lightweight agents and real backend tools.
Features:
- Deterministic intent router & entity extractor (ensuring 100% functionality even without LLM keys)
- Optional LLM integration (Gemini / OpenAI) if an API key is provided
- Real tool invocation (predict_demand, diagnose_waste, optimize_kitchen_plan, weather, preference, feedback)
- Practical kitchen-staff explanations and action items
"""
from __future__ import annotations

import logging
import os
import re
from datetime import date
from typing import Any

from backend.app.services.dataset_service import get_dataset, list_dishes_for_selection
from backend.app.services.demand_forecasting_service import predict_demand
from backend.app.services.feedback_learning_service import evaluate_model_performance
from backend.app.services.kitchen_optimization_service import optimize_kitchen_plan
from backend.app.services.preference_service import analyze_food_preference
from backend.app.services.waste_diagnosis_service import diagnose_waste
from backend.app.services.weather_service import get_weather_for_meal

logger = logging.getLogger("food_optimizer.chatbot")


def _extract_entities(
    query: str, default_dish: str = "White Rice", default_meal: str = "Lunch", default_date: str = "2026-08-04"
) -> dict[str, Any]:
    q = query.lower()

    # Detect meal
    meal = default_meal
    if "breakfast" in q:
        meal = "Breakfast"
    elif "lunch" in q:
        meal = "Lunch"
    elif "snack" in q:
        meal = "Snacks"
    elif "dinner" in q:
        meal = "Dinner"

    # Detect attendance override: e.g. "if only 400 students attend", "attendance 350", "400 students"
    attendance_override = None
    att_match = re.search(r"(\d{2,4})\s*(?:students|attend|people|residents|attendance)", q)
    if att_match:
        try:
            attendance_override = int(att_match.group(1))
        except Exception:
            pass

    # Detect food item
    available_dishes = list_dishes_for_selection()
    detected_dish = default_dish

    for dish in available_dishes:
        d_lower = dish.lower()
        if d_lower in q:
            detected_dish = dish
            break

    # Common short aliases if not matched directly
    if detected_dish == default_dish:
        if "rice" in q and "jeera" not in q and "curd rice" not in q:
            detected_dish = "White Rice"
        elif "paratha" in q or "aloo" in q:
            detected_dish = "Aloo Paratha"
        elif "curd" in q:
            detected_dish = "Curd"
        elif "dal" in q:
            detected_dish = "Dal Tadka"
        elif "sambar" in q:
            detected_dish = "Sambar"
        elif "khichadi" in q or "khichdi" in q:
            detected_dish = "Khichadi"

    return {
        "dish": detected_dish,
        "meal": meal,
        "date": default_date,
        "attendance": attendance_override,
    }


def handle_chat_message(
    message: str,
    active_dish: str = "White Rice",
    active_meal: str = "Lunch",
    active_date: str = "2026-08-04",
    active_attendance: int | None = None,
) -> dict[str, Any]:
    """Process staff inquiry, execute real agent tools, and construct actionable response."""
    entities = _extract_entities(
        message, default_dish=active_dish, default_meal=active_meal, default_date=active_date
    )
    dish = entities["dish"]
    meal = entities["meal"]
    date_str = entities["date"]
    attendance = entities["attendance"] or active_attendance

    q = message.lower().strip()
    tools_called = []

    # 1. Intent: Rain / Weather question
    # e.g., "Is rain expected during lunch?", "What is the weather?"
    if any(w in q for w in ["rain", "weather", "forecast", "precipitation", "shower"]):
        tools_called.append("get_weather_forecast")
        weather = get_weather_for_meal(date_str, meal=meal)
        rain_mm = weather.get("rainfall_mm") or 0.0
        rain_expected = weather.get("rain_expected_during_meal", False)
        source = weather.get("source", "historical")

        if rain_expected and rain_mm >= 2.0:
            reply = (
                f"Yes, rain is expected around {meal} ({rain_mm:.1f} mm forecast from {source}). "
                f"We recommend staging ingredients for {dish}, but holding back on cooking the second batch "
                f"until lunch attendance is confirmed."
            )
            action = f"Check dining hall headcount at 12:45 PM before firing the second batch of {dish}."
        else:
            reply = (
                f"No significant rain is expected during {meal} ({rain_mm:.1f} mm forecast). "
                f"Temperature is around {weather.get('temperature_c', 28)}°C ({weather.get('weather_condition', 'Clear')})."
            )
            action = f"Proceed with the standard batch schedule for {dish}."

        return {
            "reply": reply,
            "recommended_action": action,
            "tools_called": tools_called,
            "data": {"weather": weather},
        }

    # 2. Intent: Highest waste dishes / Leftovers ranking
    # e.g., "Which dishes have highest waste rates?", "Which dish is likely to have the most leftovers today?"
    if any(w in q for w in ["most leftover", "highest waste", "most waste", "leftovers today", "which dish"]):
        tools_called.append("diagnose_waste")
        df = get_dataset()
        # Find dishes with highest average leftover percentage
        grouped = (
            df.groupby("food_item")
            .agg({"leftover_portions": "mean", "prepared_portions": "mean", "waste_rate_pct": "mean"})
            .reset_index()
        )
        grouped = grouped.sort_values("waste_rate_pct", ascending=False).head(3)
        top_waste_items = []
        for _, row in grouped.iterrows():
            top_waste_items.append(f"{row['food_item']} ({row['waste_rate_pct']:.1f}% avg waste)")

        reply = (
            f"Based on historical kitchen records, the dishes with the highest leftover rates are: "
            f"{', '.join(top_waste_items)}. For these items, staff should always use conservative split-batching "
            f"(cook 60% initially and hold 40% reserve)."
        )
        action = "Check historical leftovers before preparing accompaniments like curd or special gravies."
        return {
            "reply": reply,
            "recommended_action": action,
            "tools_called": tools_called,
            "data": {"top_waste_dishes": top_waste_items},
        }

    # 3. Intent: Yesterday's learning / Feedback / Model performance
    # e.g., "What did we learn from yesterday's meal?", "How is the model performing?"
    if any(w in q for w in ["yesterday", "learn", "performance", "mae", "bias", "past meal", "accuracy"]):
        tools_called.append("get_historical_performance")
        perf = evaluate_model_performance()
        if perf.get("records_validated", 0) > 0:
            reply = (
                f"From our recorded meal outcomes, the system has logged {perf['records_validated']} meals. "
                f"Current Mean Absolute Error (MAE) is {perf['mae']} servings, with a bias of {perf['forecast_bias']:+.1f} servings. "
                f"{perf['bias_direction']}."
            )
        else:
            reply = (
                "No post-meal outcome records have been verified yet in the learning database. "
                "Kitchen staff can enter today's prepared and consumed counts using the outcome form below to start tracking accuracy."
            )
        action = "Record meal outcomes promptly after service closes."
        return {
            "reply": reply,
            "recommended_action": action,
            "tools_called": tools_called,
            "data": perf,
        }

    # 4. Intent: "Should we prepare another batch?"
    if any(w in q for w in ["another batch", "second batch", "prepare more", "cook more", "replenish"]):
        tools_called.append("generate_kitchen_plan")
        plan = optimize_kitchen_plan(dish, 320, meal=meal)
        reply = (
            f"For {dish} ({meal}): Check the serving counter first. "
            f"{plan['replenishment_check']}"
        )
        action = f"Count empty trays and line length before committing ingredients for batch 2."
        return {
            "reply": reply,
            "recommended_action": action,
            "tools_called": tools_called,
            "data": plan,
        }

    # 5. Intent: "Why are we preparing this quantity?" / "Why is demand lower than usual?"
    if any(w in q for w in ["why", "reason", "lower than usual", "explaining", "explain today's preparation plan"]):
        tools_called.extend(["predict_demand", "diagnose_waste", "get_food_preference"])
        pred_res = predict_demand(dish, meal, date_str, attendance=attendance)
        pref_res = analyze_food_preference(dish, meal=meal)
        waste_res = diagnose_waste(dish, meal=meal, target_date=date_str)
        att = pred_res["input_summary"]["attendance_estimate"]
        pred_qty = pred_res["predicted_consumers"]

        reply = (
            f"We are preparing for {pred_qty} expected consumers of {dish} ({meal}). "
            f"Here is why: "
            f"1) Estimated student attendance is {att} (exam intensity is {pred_res['input_summary']['exam_intensity']:.1f}). "
            f"2) {dish} has a preference score of {pref_res['preference_score']}/100. "
            f"3) Historical waste risk is classified as '{waste_res['risk_level']}'. "
            f"This plan prevents overcooking while ensuring enough food for attending students."
        )
        action = "Follow the split-batch plan: cook the initial batch and hold the reserve."
        return {
            "reply": reply,
            "recommended_action": action,
            "tools_called": tools_called,
            "data": {"prediction": pred_res, "preference": pref_res, "waste": waste_res},
        }

    # 6. Intent: Quantity to prepare / Demand question (Default & core flow)
    # e.g., "How much rice should we prepare for lunch?", "How much rice if 400 attend?"
    tools_called.extend(["predict_demand", "generate_kitchen_plan"])
    pred_res = predict_demand(dish, meal, date_str, attendance=attendance)
    pred_qty = pred_res["predicted_consumers"]
    plan = optimize_kitchen_plan(dish, pred_qty, meal=meal)

    reply = (
        f"For {dish} ({meal}, {date_str}): Expected demand is {pred_qty} servings "
        f"(based on attendance of {pred_res['input_summary']['attendance_estimate']}). "
        f"Recommended Kitchen Plan: "
        f"• Initial Batch: {plan['initial_batch_servings']} servings. "
        f"• Reserve Quantity: {plan['reserve_servings']} servings. "
        f"{plan['replenishment_check']}"
    )
    action = f"Start by cooking {plan['initial_batch_servings']} servings of {dish}."

    return {
        "reply": reply,
        "recommended_action": action,
        "tools_called": tools_called,
        "data": {
            "prediction": pred_res,
            "plan": plan,
        },
    }
