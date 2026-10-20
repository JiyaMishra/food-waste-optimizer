from __future__ import annotations

import importlib

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.config import get_settings
from backend.app.db.session import check_database
from backend.app.schemas.common import HealthResponse, ReadinessCheck, ReadinessResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
        synthetic_only=True,
    )


@router.get("/ready", response_model=ReadinessResponse)
def readiness(db: Session = Depends(get_db)):
    settings = get_settings()
    checks: list[ReadinessCheck] = []

    db_ok = True
    try:
        check_database(db)
        db_detail = "Database connection succeeded."
    except Exception as exc:
        db_ok = False
        db_detail = f"Database connection failed: {exc}"
    checks.append(ReadinessCheck(name="database", ok=db_ok, detail=db_detail))

    person_a_ok = True
    try:
        for module in (
            "src.data.synthetic_data",
            "src.data.validation",
            "src.availability.availability",
            "src.features.feature_builder",
            "src.ml.forecasting",
        ):
            importlib.import_module(module)
        person_a_detail = "Person A documented modules are importable."
    except Exception as exc:
        person_a_ok = False
        person_a_detail = f"Person A module import failed: {exc}"
    checks.append(
        ReadinessCheck(name="person_a_modules", ok=person_a_ok, detail=person_a_detail)
    )

    menu_ok = settings.menu_seed_file.exists()
    checks.append(
        ReadinessCheck(
            name="menu_seed",
            ok=menu_ok,
            detail=(
                f"Menu seed found: {settings.menu_seed_file}"
                if menu_ok
                else f"Menu seed missing: {settings.menu_seed_file}"
            ),
        )
    )

    data_ok = (settings.data_path / "food_operations.csv").exists()
    checks.append(
        ReadinessCheck(
            name="synthetic_dataset",
            ok=data_ok,
            detail=(
                "Generated operations file is present."
                if data_ok
                else "No generated food_operations.csv; POST /api/v1/data/generate."
            ),
        )
    )

    artifact_ok = settings.artifact_file.exists()
    checks.append(
        ReadinessCheck(
            name="model_artifact",
            ok=artifact_ok,
            detail=(
                f"Model artifact found: {settings.artifact_file}"
                if artifact_ok
                else "No model artifact; POST /api/v1/forecasts/model/train."
            ),
        )
    )

    critical_ok = db_ok and person_a_ok and menu_ok
    status = "ready" if all(check.ok for check in checks) else ("degraded" if critical_ok else "not_ready")
    payload = ReadinessResponse(status=status, checks=checks)
    if not critical_ok:
        return JSONResponse(status_code=503, content=payload.model_dump(mode="json"))
    return payload
