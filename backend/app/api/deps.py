from __future__ import annotations

from fastapi import Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db

__all__ = ["get_db", "pagination"]


def pagination(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> tuple[int, int]:
    return limit, offset
