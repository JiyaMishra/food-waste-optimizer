from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.schemas.menu import DishOut, MenuResponse, MenuSyncResponse
from backend.app.services.menu_service import list_dishes, load_menu_catalogue, upsert_menu

router = APIRouter(prefix="/menu", tags=["menu"])


@router.get("", response_model=MenuResponse)
def get_menu(
    meal_type: str | None = None,
    category: str | None = None,
) -> MenuResponse:
    items = load_menu_catalogue()
    if meal_type:
        items = [item for item in items if item["meal_type"] == meal_type]
    if category:
        items = [item for item in items if item["category"] == category]
    return MenuResponse(
        source="data/menu_seed/vegetarian_menu.csv",
        count=len(items),
        items=[DishOut(**item) for item in items],
    )


@router.post("/sync", response_model=MenuSyncResponse)
def sync_menu(db: Session = Depends(get_db)) -> MenuSyncResponse:
    count = upsert_menu(db)
    return MenuSyncResponse(
        dishes_upserted=count,
        source="data/menu_seed/vegetarian_menu.csv",
        message="Starter menu synced to the database; no general data was regenerated.",
    )


@router.get("/database", response_model=list[DishOut])
def get_persisted_menu(
    meal_type: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
) -> list[DishOut]:
    return [DishOut.model_validate(item) for item in list_dishes(db, meal_type, category)]
