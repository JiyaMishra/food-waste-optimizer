from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db, pagination
from backend.app.schemas.evaluation import FeedbackListResponse, FeedbackOut, FeedbackRequest
from backend.app.services.feedback import count_feedback, create_feedback, list_feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


def _feedback_out(row) -> FeedbackOut:
    return FeedbackOut(
        id=row.id,
        run_id=row.run_id,
        event_type=row.event_type,
        payload=row.payload or {},
        candidate_retraining=row.candidate_retraining or {},
        created_at=row.created_at,
    )


@router.post("", response_model=FeedbackOut)
def submit_feedback(
    payload: FeedbackRequest, db: Session = Depends(get_db)
) -> FeedbackOut:
    row = create_feedback(db, payload.event_type, payload.payload, payload.run_id)
    return _feedback_out(row)


@router.get("", response_model=FeedbackListResponse)
def read_feedback(
    run_id: str | None = None,
    event_type: str | None = None,
    page: tuple[int, int] = Depends(pagination),
    db: Session = Depends(get_db),
) -> FeedbackListResponse:
    limit, offset = page
    rows = list_feedback(db, run_id, event_type, limit, offset)
    total = count_feedback(db, run_id, event_type)
    return FeedbackListResponse(
        items=[_feedback_out(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )
