"""Outcome/learning agent: evaluation and candidate-retraining metadata only."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.agents.contracts import LearningObservation
from backend.app.services.evaluation import evaluate_run


def run(db: Session, run_id: str, persist: bool = True) -> dict:
    evaluation = evaluate_run(db, run_id, persist=persist)
    observation = LearningObservation(
        evaluation_id=evaluation.get("id") or None,
        metrics=evaluation["metrics"],
        model_metrics=evaluation.get("model_metrics"),
        candidate_retraining={
            "auto_retrain": False,
            "requires_manual_review": True,
            "run_id": run_id,
            "recommended_action": (
                "Review operational metrics before any manual model retraining; "
                "no production model is replaced automatically."
            ),
        },
    )
    return observation.model_dump(mode="json")
