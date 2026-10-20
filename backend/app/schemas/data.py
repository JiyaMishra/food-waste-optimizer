from __future__ import annotations

from pydantic import BaseModel, Field

from backend.app.schemas.common import ReadinessCheck


class GenerateDataRequest(BaseModel):
    months: int = Field(default=6, ge=1, le=24, description="Months of synthetic history")
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    residents: int = Field(default=900, ge=10, le=10000)
    validate_after: bool = True


class ValidationReport(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    files: dict = Field(default_factory=dict)


class GenerateDataResponse(BaseModel):
    ok: bool
    output_dir: str
    months: int
    seed: int
    residents: int
    scenario_id: str
    dataset_version: str
    validation: ValidationReport | None = None
    caveat: str = "All generated records are synthetic and must not be presented as real VIT measurements."


class ValidateDataRequest(BaseModel):
    pass


class ValidateDataResponse(BaseModel):
    ok: bool
    errors: list[str] = Field(default_factory=list)
    files: dict = Field(default_factory=dict)
    data_dir: str
    checks: list[ReadinessCheck] = Field(default_factory=list)


class DataSyncResponse(BaseModel):
    data_dir: str
    scenario_id: str
    dataset_version: str
    dishes_upserted: int
    menu_items: int
    context_rows: int
    academic_slots: int
    message: str
