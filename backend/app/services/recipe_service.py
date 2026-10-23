"""Recipe service for kitchen portion conversion and ingredient calculation.

Only converts portions into physical units (kg, litres, pieces) when a verified recipe
is registered. Otherwise, flags that recipe details are required.
"""
from __future__ import annotations

from typing import Any

# Verified recipes for standard Indian hostel mess dishes (per 100 servings)
RECIPE_DATABASE: dict[str, dict[str, Any]] = {
    "white rice": {
        "dish_name": "White Rice",
        "portion_description": "150g cooked rice per serving",
        "primary_unit": "kg cooked",
        "ingredients_per_100": [
            {"ingredient": "Raw Basmati / Ponni Rice", "quantity": 7.0, "unit": "kg"},
            {"ingredient": "Water", "quantity": 14.0, "unit": "litres"},
            {"ingredient": "Salt", "quantity": 0.15, "unit": "kg"},
        ],
        "safe_holding_temp_c": ">= 60°C (hot-holding bain-marie)",
        "max_holding_hours": 2,
    },
    "jeera rice": {
        "dish_name": "Jeera Rice",
        "portion_description": "150g cooked rice per serving",
        "primary_unit": "kg cooked",
        "ingredients_per_100": [
            {"ingredient": "Raw Rice", "quantity": 7.0, "unit": "kg"},
            {"ingredient": "Cumin Seeds (Jeera)", "quantity": 0.25, "unit": "kg"},
            {"ingredient": "Cooking Ghee / Oil", "quantity": 0.8, "unit": "litres"},
            {"ingredient": "Water", "quantity": 14.0, "unit": "litres"},
        ],
        "safe_holding_temp_c": ">= 60°C",
        "max_holding_hours": 2,
    },
    "khichadi": {
        "dish_name": "Khichadi",
        "portion_description": "200g per serving",
        "primary_unit": "kg cooked",
        "ingredients_per_100": [
            {"ingredient": "Rice", "quantity": 5.0, "unit": "kg"},
            {"ingredient": "Moong Dal", "quantity": 4.0, "unit": "kg"},
            {"ingredient": "Ghee / Oil", "quantity": 0.6, "unit": "litres"},
            {"ingredient": "Turmeric & Spices", "quantity": 0.2, "unit": "kg"},
            {"ingredient": "Water", "quantity": 18.0, "unit": "litres"},
        ],
        "safe_holding_temp_c": ">= 60°C",
        "max_holding_hours": 2,
    },
    "aloo paratha": {
        "dish_name": "Aloo Paratha",
        "portion_description": "2 pieces (approx 180g) per serving",
        "primary_unit": "pieces",
        "ingredients_per_100": [
            {"ingredient": "Whole Wheat Atta", "quantity": 12.0, "unit": "kg"},
            {"ingredient": "Boiled Potatoes", "quantity": 15.0, "unit": "kg"},
            {"ingredient": "Onions & Green Chillies", "quantity": 3.0, "unit": "kg"},
            {"ingredient": "Spices & Salt", "quantity": 0.5, "unit": "kg"},
            {"ingredient": "Oil / Butter", "quantity": 2.5, "unit": "litres"},
        ],
        "safe_holding_temp_c": "Freshly griddled, keep wrapped hot",
        "max_holding_hours": 1.5,
    },
    "curd": {
        "dish_name": "Curd",
        "portion_description": "100ml per serving",
        "primary_unit": "litres",
        "ingredients_per_100": [
            {"ingredient": "Pasteurized Milk", "quantity": 10.0, "unit": "litres"},
            {"ingredient": "Active Starter Culture", "quantity": 0.3, "unit": "litres"},
        ],
        "safe_holding_temp_c": "<= 5°C (refrigerated counter)",
        "max_holding_hours": 4,
    },
    "sambar": {
        "dish_name": "Sambar",
        "portion_description": "150ml per serving",
        "primary_unit": "litres",
        "ingredients_per_100": [
            {"ingredient": "Toor Dal", "quantity": 3.5, "unit": "kg"},
            {"ingredient": "Mixed Vegetables (Drumstick, Pumpkin, Carrot)", "quantity": 5.0, "unit": "kg"},
            {"ingredient": "Tamarind Pulp", "quantity": 0.8, "unit": "kg"},
            {"ingredient": "Sambar Powder & Spices", "quantity": 0.4, "unit": "kg"},
            {"ingredient": "Water", "quantity": 12.0, "unit": "litres"},
        ],
        "safe_holding_temp_c": ">= 65°C",
        "max_holding_hours": 3,
    },
    "dal tadka": {
        "dish_name": "Dal Tadka",
        "portion_description": "120ml per serving",
        "primary_unit": "litres",
        "ingredients_per_100": [
            {"ingredient": "Toor / Moong Dal", "quantity": 4.0, "unit": "kg"},
            {"ingredient": "Onion & Tomato", "quantity": 2.5, "unit": "kg"},
            {"ingredient": "Ghee / Oil for Tadka", "quantity": 0.7, "unit": "litres"},
            {"ingredient": "Garlic, Cumin & Spices", "quantity": 0.3, "unit": "kg"},
            {"ingredient": "Water", "quantity": 10.0, "unit": "litres"},
        ],
        "safe_holding_temp_c": ">= 65°C",
        "max_holding_hours": 3,
    },
    "tea": {
        "dish_name": "Tea",
        "portion_description": "100ml cup per serving",
        "primary_unit": "litres",
        "ingredients_per_100": [
            {"ingredient": "Milk", "quantity": 6.0, "unit": "litres"},
            {"ingredient": "Water", "quantity": 4.5, "unit": "litres"},
            {"ingredient": "Tea Dust", "quantity": 0.4, "unit": "kg"},
            {"ingredient": "Sugar", "quantity": 0.8, "unit": "kg"},
        ],
        "safe_holding_temp_c": ">= 70°C (insulated dispenser)",
        "max_holding_hours": 2,
    },
    "coffee": {
        "dish_name": "Coffee",
        "portion_description": "100ml cup per serving",
        "primary_unit": "litres",
        "ingredients_per_100": [
            {"ingredient": "Milk", "quantity": 7.0, "unit": "litres"},
            {"ingredient": "Water", "quantity": 3.5, "unit": "litres"},
            {"ingredient": "Filter Coffee Decoction", "quantity": 0.5, "unit": "litres"},
            {"ingredient": "Sugar", "quantity": 0.8, "unit": "kg"},
        ],
        "safe_holding_temp_c": ">= 70°C",
        "max_holding_hours": 2,
    },
}


def get_recipe_for_dish(food_item: str) -> dict[str, Any] | None:
    key = food_item.strip().lower()
    return RECIPE_DATABASE.get(key)


def calculate_ingredients(food_item: str, servings: int) -> dict[str, Any]:
    recipe = get_recipe_for_dish(food_item)
    if not recipe:
        return {
            "has_validated_recipe": False,
            "dish_name": food_item,
            "servings": servings,
            "ingredient_requirements": [],
            "assumptions": [
                f"No verified recipe yield definition is on file for '{food_item}'.",
                "Quantities are expressed in discrete dining portions/servings.",
                "To calculate raw ingredient weights in kg/litres, register a recipe specification.",
            ],
        }

    scale = servings / 100.0
    calculated_ingredients = []
    for ing in recipe["ingredients_per_100"]:
        total_qty = round(ing["quantity"] * scale, 2)
        calculated_ingredients.append(
            {
                "ingredient": ing["ingredient"],
                "quantity": total_qty,
                "unit": ing["unit"],
            }
        )

    return {
        "has_validated_recipe": True,
        "dish_name": recipe["dish_name"],
        "portion_description": recipe["portion_description"],
        "servings": servings,
        "ingredient_requirements": calculated_ingredients,
        "food_safety": {
            "safe_holding_temp": recipe["safe_holding_temp_c"],
            "max_holding_hours": recipe["max_holding_hours"],
            "guideline": "Hot food must remain above 60°C; cold food below 5°C. Never re-serve plate leftovers.",
        },
        "assumptions": [
            f"Calculated from verified standard recipe for {recipe['dish_name']}.",
            f"Yield assumes standard portion size: {recipe['portion_description']}.",
        ],
    }
