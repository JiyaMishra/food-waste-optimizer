"""Agent 1: Food Preference Agent.

Determines how much students appear to like each dish using deterministic
scoring from historical records, ratings, and demand rates.
Explains popularity vs demand clearly without fabricating data.
"""
from __future__ import annotations

import logging
from typing import Any
import numpy as np

from backend.app.services.dataset_service import get_dish_history, get_dataset

logger = logging.getLogger("food_optimizer.preference_agent")


def analyze_food_preference(
    food_item: str, meal: str | None = None
) -> dict[str, Any]:
    """Calculate an interpretable preference score between 0 and 100."""
    history = get_dish_history(food_item, meal=meal, limit=50)

    if not history:
        # Check if the dish exists across any meal
        history_any = get_dish_history(food_item, meal=None, limit=50)
        if not history_any:
            return {
                "agent": "food_preference",
                "food_item": food_item,
                "meal": meal or "All",
                "preference_score": 50,
                "evidence": ["No historical consumption or rating records found for this dish."],
                "confidence": "low",
                "warnings": [f"Insufficient data: '{food_item}' has no historical records in the menu dataset."],
                "explanation": f"No historical records exist for {food_item}. A neutral baseline score of 50/100 is assigned with low confidence.",
            }
        history = history_any

    # Extract historical liking scores and historical demand rates
    liking_scores = [
        float(r["synthetic_liking_score"])
        for r in history
        if "synthetic_liking_score" in r and not np.isnan(r["synthetic_liking_score"])
    ]
    demand_rates = [
        float(r["historical_demand_rate"])
        for r in history
        if "historical_demand_rate" in r and not np.isnan(r["historical_demand_rate"])
    ]

    record_count = len(history)

    if liking_scores:
        avg_liking = float(np.mean(liking_scores))
        # Scaled to 0 - 100
        raw_score = avg_liking * 100.0
    elif demand_rates:
        avg_demand_rate = float(np.mean(demand_rates))
        raw_score = avg_demand_rate * 100.0
    else:
        raw_score = 50.0

    # If demand rate is also available, blend slightly (75% student rating / liking, 25% take-up rate)
    if liking_scores and demand_rates:
        avg_demand_rate = float(np.mean(demand_rates))
        score = round(0.75 * (avg_liking * 100.0) + 0.25 * (avg_demand_rate * 100.0))
    else:
        score = round(raw_score)

    score = max(0, min(100, score))

    # Evidence items
    evidence = []
    if liking_scores:
        evidence.append(
            f"Average synthetic student liking score is {np.mean(liking_scores):.3f} / 1.0 based on {len(liking_scores)} recorded meals."
        )
    if demand_rates:
        evidence.append(
            f"Historical diner selection rate is {np.mean(demand_rates) * 100:.1f}% of attending students."
        )

    # Determine confidence based on sample size
    if record_count >= 15:
        confidence = "high"
    elif record_count >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    warnings = []
    if record_count < 5:
        warnings.append(
            f"Sample size is small ({record_count} meals). Scores should be treated as preliminary."
        )
    warnings.append(
        "Ratings in this dataset are simulated (synthetic) and do not represent verified student surveys."
    )

    # Build human explanation distinguishing popularity from demand
    if score >= 75:
        tier = "highly liked"
        advice = "Students usually show high interest in this dish. However, total quantity prepared must still be scaled to today's expected attendance."
    elif score >= 50:
        tier = "moderately liked"
        advice = "Demand is typical for a staple or regular accompaniment."
    else:
        tier = "lower preference"
        advice = "Historical engagement is below average; kitchen should avoid aggressive batch sizes to minimize plate and container waste."

    meal_str = f" during {meal}" if meal else ""
    explanation = (
        f"{food_item} has a preference score of {score}/100 ({tier}){meal_str}. "
        f"{advice}"
    )

    return {
        "agent": "food_preference",
        "food_item": food_item,
        "meal": meal or (history[0]["meal"] if history else "All"),
        "preference_score": score,
        "evidence": evidence,
        "confidence": confidence,
        "warnings": warnings,
        "explanation": explanation,
    }
