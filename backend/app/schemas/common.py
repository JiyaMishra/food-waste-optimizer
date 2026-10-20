from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None
    request_id: str = "-"


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    synthetic_only: bool = True


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class ReadinessResponse(BaseModel):
    status: str
    checks: list[ReadinessCheck]


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class PaginatedResponse(BaseModel):
    items: list[Any]
    page: PageMeta = Field(description="Pagination metadata")
