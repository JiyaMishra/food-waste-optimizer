from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.core.errors import DomainError
from backend.app.db.models import Diagnosis
from backend.app.schemas.diagnosis import (
    CauseOut,
    DiagnosisListResponse,
    DiagnosisOut,
    EvidenceOut,
    PostMealDiagnosisRequest,
    PreMealDiagnosisRequest,
)
from backend.app.services.waste_diagnosis import diagnose_pre_meal, diagnose_run

router = APIRouter(prefix="/diagnoses", tags=["waste risk and diagnosis"])


def _diagnosis_out(row: Diagnosis) -> DiagnosisOut:
    return DiagnosisOut(
        id=row.id,
        diagnosis_type=row.diagnosis_type,
        target_date=row.target_date,
        meal_type=row.meal_type,
        dish_external_id=row.dish_external_id,
        risk_score=row.risk_score,
        confidence=row.confidence,
        causes=[CauseOut(**item) for item in (row.causes or [])],
        evidence=[EvidenceOut(**item) for item in (row.evidence or [])],
        caveats=row.caveats or [],
        data_sources=row.data_sources or [],
        llm_used=row.llm_used,
        is_synthetic=row.is_synthetic,
    )


@router.post("/pre-meal", response_model=list[DiagnosisOut])
def pre_meal(
    payload: PreMealDiagnosisRequest, db: Session = Depends(get_db)
) -> list[DiagnosisOut]:
    results = diagnose_pre_meal(db, payload)
    return [DiagnosisOut(**item) for item in results]


@router.post("/post-meal", response_model=DiagnosisOut)
def post_meal(
    payload: PostMealDiagnosisRequest, db: Session = Depends(get_db)
) -> DiagnosisOut:
    result = diagnose_run(
        db,
        payload.run_id,
        recent_menu_counts=payload.recent_menu_counts,
        context_baseline=payload.context_baseline,
        persist=payload.persist,
    )
    return DiagnosisOut(**result)


@router.get("", response_model=DiagnosisListResponse)
def list_diagnoses(
    diagnosis_type: str | None = None,
    day: date | None = Query(default=None, alias="date"),
    meal_type: str | None = None,
    run_id: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> DiagnosisListResponse:
    limit, offset = page
    stmt = select(Diagnosis)
    count_stmt = select(func.count()).select_from(Diagnosis)
    if diagnosis_type:
        stmt = stmt.where(Diagnosis.diagnosis_type == diagnosis_type)
        count_stmt = count_stmt.where(Diagnosis.diagnosis_type == diagnosis_type)
    if day:
        stmt = stmt.where(Diagnosis.target_date == day)
        count_stmt = count_stmt.where(Diagnosis.target_date == day)
    if meal_type:
        stmt = stmt.where(Diagnosis.meal_type == meal_type)
        count_stmt = count_stmt.where(Diagnosis.meal_type == meal_type)
    if run_id:
        stmt = stmt.where(Diagnosis.run_id == run_id)
        count_stmt = count_stmt.where(Diagnosis.run_id == run_id)
    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(Diagnosis.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )
    return DiagnosisListResponse(
        items=[_diagnosis_out(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{diagnosis_id}", response_model=DiagnosisOut)
def get_diagnosis(diagnosis_id: str, db: Session = Depends(get_db)) -> DiagnosisOut:
    row = db.get(Diagnosis, diagnosis_id)
    if row is None:
        raise DomainError(
            "DIAGNOSIS_NOT_FOUND", f"diagnosis not found: {diagnosis_id}", 404
        )
    return _diagnosis_out(row)
