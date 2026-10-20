from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.core.errors import DomainError
from backend.app.db.models import EvaluationRun
from backend.app.schemas.evaluation import (
    EvaluationCompareRequest,
    EvaluationCompareResponse,
    EvaluationOut,
)
from backend.app.services.evaluation import (
    compare_runs,
    evaluate_run,
    evaluation_to_schema,
    latest_evaluation,
)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/runs/{run_id}", response_model=EvaluationOut)
def evaluate(run_id: str, db: Session = Depends(get_db)) -> EvaluationOut:
    return EvaluationOut(**evaluate_run(db, run_id, persist=True))


@router.get("/runs/{run_id}/latest", response_model=EvaluationOut)
def read_latest_evaluation(run_id: str, db: Session = Depends(get_db)) -> EvaluationOut:
    row = latest_evaluation(db, run_id)
    if row is None:
        raise DomainError(
            "EVALUATION_NOT_FOUND",
            f"no persisted evaluation for run {run_id}; POST /evaluation/runs/{run_id} first",
            404,
        )
    return evaluation_to_schema(row)


@router.post("/compare", response_model=EvaluationCompareResponse)
def compare(payload: EvaluationCompareRequest, db: Session = Depends(get_db)) -> EvaluationCompareResponse:
    return EvaluationCompareResponse(
        **compare_runs(
            db,
            payload.baseline_run_id,
            payload.context_run_id,
            persist=payload.persist,
        )
    )


@router.get("/{evaluation_id}", response_model=EvaluationOut)
def get_evaluation(evaluation_id: str, db: Session = Depends(get_db)) -> EvaluationOut:
    row = db.get(EvaluationRun, evaluation_id)
    if row is None:
        raise DomainError(
            "EVALUATION_NOT_FOUND", f"evaluation not found: {evaluation_id}", 404
        )
    return evaluation_to_schema(row)
