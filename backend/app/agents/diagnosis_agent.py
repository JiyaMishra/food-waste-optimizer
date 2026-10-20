"""Diagnosis agent exposing pre-meal risk and post-meal evidence-based diagnosis."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.agents.contracts import DiagnosisObservation
from backend.app.schemas.diagnosis import PreMealDiagnosisRequest
from backend.app.services.waste_diagnosis import diagnose_pre_meal, diagnose_run


def run_pre_meal(
    db: Session,
    request: PreMealDiagnosisRequest,
    forecasts: list[dict] | None = None,
) -> dict:
    results = diagnose_pre_meal(db, request, forecasts=forecasts)
    observation = DiagnosisObservation(
        diagnoses=results,
        diagnosis_ids=[item["id"] for item in results if item.get("id")],
        llm_used=False,
    )
    return observation.model_dump(mode="json")


def run_post_meal(
    db: Session,
    run_id: str,
    recent_menu_counts: dict[str, int] | None = None,
    context_baseline: dict | None = None,
) -> dict:
    result = diagnose_run(db, run_id, recent_menu_counts, context_baseline)
    observation = DiagnosisObservation(
        diagnoses=[result],
        diagnosis_ids=[result["id"]] if result.get("id") else [],
        llm_used=False,
    )
    return observation.model_dump(mode="json")
