from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DishOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: str
    name: str
    category: str | None = None
    meal_type: str
    vegetarian_flag: bool
    default_unit: str
    typical_portion_size: float | None = None
    prep_lead_minutes: int
    batch_min: float
    batch_max: float
    kitchen_capacity_per_interval: float
    menu_source: str | None = None
    source_date: date | None = None
    is_synthetic: bool


class MenuResponse(BaseModel):
    source: str
    count: int
    items: list[DishOut]
    caveat: str = "Starter vegetarian catalogue; verify dish names against supplied menu images."


class MenuSyncResponse(BaseModel):
    dishes_upserted: int
    source: str
    message: str
