from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import get_settings
from backend.app.schemas.common import ReadinessCheck
from backend.app.schemas.data import (
    DataSyncResponse,
    GenerateDataRequest,
    GenerateDataResponse,
    ValidateDataResponse,
)
from backend.app.services.data_service import (
    generate_dataset,
    sync_generated_data,
    validate_generated_data,
)

router = APIRouter(prefix="/data", tags=["synthetic data"])


@router.post("/generate", response_model=GenerateDataResponse)
def generate_synthetic_dataset(payload: GenerateDataRequest | None = None) -> GenerateDataResponse:
    request = payload or GenerateDataRequest()
    result = generate_dataset(
        months=request.months,
        seed=request.seed,
        residents=request.residents,
        validate_after=request.validate_after,
    )
    return GenerateDataResponse(**result)


@router.post("/validate", response_model=ValidateDataResponse)
def validate_synthetic_dataset() -> ValidateDataResponse:
    report = validate_generated_data()
    checks = [
        ReadinessCheck(
            name="Person A validation",
            ok=report["ok"],
            detail=(
                "All structural, provenance and quantity checks passed."
                if report["ok"]
                else f"{len(report['errors'])} validation error(s)."
            ),
        )
    ]
    return ValidateDataResponse(
        ok=report["ok"],
        errors=report["errors"],
        files=report["files"],
        data_dir=str(get_settings().data_path),
        checks=checks,
    )


@router.post("/sync", response_model=DataSyncResponse)
def sync_synthetic_dataset(db: Session = Depends(get_db)) -> DataSyncResponse:
    return DataSyncResponse(**sync_generated_data(db))
