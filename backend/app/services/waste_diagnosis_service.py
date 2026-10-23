"""Agent 3: Waste Diagnosis Agent.

Identifies dishes at risk of producing avoidable waste, calculates historical
leftover and forecast error rates, and identifies evidence-based contributing factors.
"""
from __future__ import annotations

import logging
from typing import Any
import numpy as np

from backend.app.services.dataset_service import get_dish_history, get_record

logger = logging.getLogger("food_optimizer.waste_agent")


def diagnose_waste(
    food_item: str,
    meal: str | None = None,
    target_date: str | None = None,
    prepared_portions: float | None = None,
    consumed_portions: float | None = None,
    leftover_portions: float | None = None,
) -> dict[str, Any]:
    """Analyze waste history and calculate risk classification and actionable remedies."""
    history = get_dish_history(food_item, meal=meal, limit=30)
    record = get_record(target_date, meal, food_item) if target_date and meal else None

    evidence = []
    possible_factors = []
    recommended_actions = []
    warnings = []

    # 1. Determine current or historical observed waste rate
    if prepared_portions is not None and leftover_portions is not None:
        if prepared_portions > 0:
            observed_waste_rate = round((leftover_portions / prepared_portions) * 100.0, 2)
        else:
            observed_waste_rate = 0.0
        evidence.append(
            f"Specified meal outcome: {leftover_portions} portions leftover from {prepared_portions} prepared ({observed_waste_rate}% waste rate)."
        )
    elif record and "waste_rate_pct" in record:
        observed_waste_rate = float(record["waste_rate_pct"])
        leftover = record.get("leftover_portions", 0)
        prep = record.get("prepared_portions", 0)
        evidence.append(
            f"On {record.get('date')} ({record.get('meal')}): {leftover} portions leftover from {prep} prepared ({observed_waste_rate:.2f}% waste rate)."
        )
    elif history:
        rates = [
            float(r["waste_rate_pct"])
            for r in history
            if "waste_rate_pct" in r and not np.isnan(r["waste_rate_pct"])
        ]
        if rates:
            observed_waste_rate = round(float(np.mean(rates)), 2)
            evidence.append(
                f"Historical average leftover rate across {len(rates)} meals is {observed_waste_rate:.2f}%."
            )
        else:
            observed_waste_rate = 0.0
    else:
        observed_waste_rate = None
        warnings.append("No historical leftovers recorded for this dish.")

    # 2. Risk classification
    if observed_waste_rate is None:
        risk_level = "unknown"
    elif observed_waste_rate > 10.0:
        risk_level = "high"
    elif observed_waste_rate >= 5.0:
        risk_level = "medium"
    else:
        risk_level = "low"

    # 3. Factor Analysis from historical trends
    if history:
        # Check overpreparation bias
        preparations = [r["prepared_portions"] for r in history if "prepared_portions" in r]
        consumptions = [r["consumed_portions"] for r in history if "consumed_portions" in r]
        if preparations and consumptions:
            avg_prep = np.mean(preparations)
            avg_cons = np.mean(consumptions)
            if avg_prep > avg_cons * 1.08:
                possible_factors.append(
                    f"Consistently high preparation buffer: kitchen historically prepares an average of {avg_prep:.0f} portions versus {avg_cons:.0f} consumed."
                )

        # Check weather correlation
        rain_meals = [r for r in history if r.get("rainfall_mm", 0) > 5.0]
        if len(rain_meals) >= 2:
            rain_waste = np.mean([r.get("waste_rate_pct", 0) for r in rain_meals])
            if rain_waste > 7.0:
                possible_factors.append(
                    f"Weather sensitivity: on rainy days (>5mm), average waste rate rose to {rain_waste:.1f}%."
                )

        # Check exam periods
        exam_meals = [r for r in history if r.get("exam_intensity", 0) >= 0.7]
        if len(exam_meals) >= 2:
            exam_waste = np.mean([r.get("waste_rate_pct", 0) for r in exam_meals])
            if exam_waste > 7.0:
                possible_factors.append(
                    f"Exam schedule disruption: high exam days show attendance drop with an average waste rate of {exam_waste:.1f}%."
                )

    # 4. Actionable recommendations
    if risk_level == "high":
        recommended_actions.append(
            "Adopt conservative split-batching: prepare only 60% of forecast demand initially, and hold 40% as a staged reserve."
        )
        recommended_actions.append(
            "Conduct a serving audit after 50% of meal duration before committing ingredients for secondary preparation."
        )
    elif risk_level == "medium":
        recommended_actions.append(
            "Use standard 70/30 split-batching. Keep dry/chilled ingredients prepped without cooking the full batch upfront."
        )
        recommended_actions.append(
            "Check live counter queue length and dining hall arrivals before preparing the reserve batch."
        )
    else:
        recommended_actions.append(
            "Standard preparation schedule. Demand is predictable with low historical leftover risk (<5%)."
        )

    return {
        "agent": "waste_diagnosis",
        "food_item": food_item,
        "meal": meal or "All",
        "risk_level": risk_level,
        "observed_waste_rate": observed_waste_rate,
        "evidence": evidence,
        "possible_factors": possible_factors,
        "recommended_actions": recommended_actions,
        "warnings": warnings,
    }
