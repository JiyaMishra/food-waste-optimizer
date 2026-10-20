"""Feedback capture and candidate-retraining metadata without automatic retraining."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.errors import DomainError
from backend.app.db.models import FeedbackEvent, MealRun


def create_feedback(
    db: Session,
    event_type: str,
    payload: dict,
    run_id: str | None = None,
) -> FeedbackEvent:
    if not event_type.strip():
        raise DomainError("FEEDBACK_INVALID", "event_type must not be empty", 422)
    if run_id is not None:
        run = db.get(MealRun, run_id)
        if run is None:
            raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
        eligible = run.status == "finished"
        candidate = {
            "eligible_for_review": eligible,
            "auto_retrain": False,
            "reason": (
                "Run finished; candidate metadata can be reviewed by a human."
                if eligible
                else "Run is not finished; no retraining candidate is proposed."
            ),
            "run_id": run_id,
            "policy_id": run.policy_id,
            "scenario_id": run.scenario_id,
            "seed": run.seed,
            "recommended_action": "Review evaluation metrics before any manual retraining.",
        }
    else:
        candidate = {
            "eligible_for_review": False,
            "auto_retrain": False,
            "reason": "No run is linked; feedback is retained as an observation only.",
            "recommended_action": "Link feedback to a completed run for review.",
        }
    event = FeedbackEvent(
        run_id=run_id,
        event_type=event_type,
        payload=payload,
        candidate_retraining=candidate,
    )
    db.add(event)
    db.flush()
    return event


def list_feedback(
    db: Session,
    run_id: str | None = None,
    event_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[FeedbackEvent]:
    from sqlalchemy import func

    stmt = select(FeedbackEvent)
    if run_id:
        stmt = stmt.where(FeedbackEvent.run_id == run_id)
    if event_type:
        stmt = stmt.where(FeedbackEvent.event_type == event_type)
    return list(
        db.scalars(
            stmt.order_by(FeedbackEvent.created_at.desc()).limit(limit).offset(offset)
        ).all()
    )


def count_feedback(
    db: Session,
    run_id: str | None = None,
    event_type: str | None = None,
) -> int:
    from sqlalchemy import func

    stmt = select(func.count()).select_from(FeedbackEvent)
    if run_id:
        stmt = stmt.where(FeedbackEvent.run_id == run_id)
    if event_type:
        stmt = stmt.where(FeedbackEvent.event_type == event_type)
    return int(db.scalar(stmt) or 0)
