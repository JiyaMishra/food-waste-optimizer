"""Agent 4: Kitchen Optimization Agent.

Translates forecasted demand into practical batch instructions for mess staff:
- Initial preparation batch
- Staged reserve quantity
- Explicit replenishment checkpoints
- Ingredient calculations when validated recipes exist
"""
from __future__ import annotations

import logging
from typing import Any

from backend.app.services.recipe_service import calculate_ingredients
from backend.app.services.waste_diagnosis_service import diagnose_waste

logger = logging.getLogger("food_optimizer.kitchen_agent")


def optimize_kitchen_plan(
    food_item: str,
    predicted_demand: int,
    meal: str | None = None,
    risk_level: str | None = None,
    kitchen_capacity: int = 800,
) -> dict[str, Any]:
    """Generate a split-batch operational plan that kitchen staff can execute immediately."""
    demand = max(0, int(predicted_demand))

    # Determine batching split ratio based on waste risk
    if not risk_level:
        waste_diag = diagnose_waste(food_item, meal=meal)
        risk_level = waste_diag.get("risk_level", "medium")

    # High risk -> conservative initial batch (60% initial, 40% reserve)
    # Medium risk -> standard split (70% initial, 30% reserve)
    # Low risk -> higher initial batch (80% initial, 20% reserve)
    if risk_level == "high":
        initial_ratio = 0.60
    elif risk_level == "low":
        initial_ratio = 0.80
    else:
        initial_ratio = 0.70

    if demand <= 20:
        # Very small quantity: prepare in single batch
        initial_batch = demand
        reserve = 0
    else:
        initial_batch = int(round(demand * initial_ratio))
        reserve = demand - initial_batch

    # Replenishment check trigger: check when 70% of initial batch has been served
    replenishment_threshold = int(round(initial_batch * 0.70))

    if reserve > 0:
        replenishment_check = (
            f"Start with {initial_batch} servings. Check counter consumption once {replenishment_threshold} "
            f"servings are served. If queues remain active, trigger cooking the reserve batch of {reserve} servings."
        )
    else:
        replenishment_check = (
            f"Prepare full quantity of {initial_batch} servings upfront. Dish demand is small; no secondary batch needed."
        )

    # Ingredient breakdown via recipe service
    recipe_info = calculate_ingredients(food_item, demand)

    assumptions = list(recipe_info.get("assumptions", []))
    if initial_batch + reserve > kitchen_capacity:
        assumptions.append(
            f"Warning: Planned preparation ({initial_batch + reserve}) exceeds nominal cooking vessel capacity ({kitchen_capacity}). Cook in serial stages."
        )

    return {
        "agent": "kitchen_optimization",
        "food_item": food_item,
        "meal": meal or "Meal",
        "predicted_demand": demand,
        "initial_batch_servings": initial_batch,
        "reserve_servings": reserve,
        "replenishment_threshold": replenishment_threshold,
        "replenishment_check": replenishment_check,
        "risk_level": risk_level,
        "batch_ratio": f"{int(initial_ratio * 100)}% / {100 - int(initial_ratio * 100)}%",
        "has_validated_recipe": recipe_info.get("has_validated_recipe", False),
        "ingredient_requirements": recipe_info.get("ingredient_requirements", []),
        "food_safety": recipe_info.get("food_safety"),
        "assumptions": assumptions,
    }
