from fastapi import APIRouter

from backend.app.api.v1 import (
    agents,
    context,
    data,
    diagnoses,
    evaluation,
    exports,
    feedback,
    forecasts,
    menu,
    plans,
    simulations,
)

router = APIRouter()
router.include_router(menu.router)
router.include_router(data.router)
router.include_router(context.router)
router.include_router(forecasts.router)
router.include_router(plans.router)
router.include_router(simulations.router)
router.include_router(diagnoses.router)
router.include_router(agents.router)
router.include_router(evaluation.router)
router.include_router(feedback.router)
router.include_router(exports.router)
