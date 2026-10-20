"""Kitchen planning agent wrapping the deterministic constrained optimizer."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.agents.contracts import PlanObservation
from backend.app.schemas.plan import OptimizerRequest
from backend.app.services.optimizer import optimize


def run(db: Session, request: OptimizerRequest) -> dict:
    plan = optimize(request, db=db)
    observation = PlanObservation.model_validate(plan)
    return observation.model_dump(mode="json")
