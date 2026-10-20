"""Evidence-based waste risk and retrospective diagnosis.

Only deterministic rules are used. No LLM is asked to invent evidence, and
correlation is never described as proven causation.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.errors import DomainError
from backend.app.db.models import Diagnosis, Dish, MealRun, MenuItem, Outcome, Prediction, SimulationEvent
from backend.app.schemas.diagnosis import (
    CauseOut,
    DiagnosisOut,
    EvidenceOut,
    PostMealDiagnosisRequest,
    PreMealDiagnosisRequest,
)


def _risk_level(score: float) -> str:
    if score >= 0.66:
        return "high"
    if score >= 0.33:
        return "medium"
    return "low"


def estimate_pre_meal_risk(
    request: PreMealDiagnosisRequest,
    forecasts: list[dict] | None = None,
) -> list[dict]:
    forecast_rows = forecasts or [item.model_dump() for item in request.forecasts]
    planned = {item.dish_id: item.prepared_qty for item in request.planned_quantities}
    results: list[dict] = []
    if not forecast_rows:
        raise DomainError(
            "DIAGNOSIS_EVIDENCE_MISSING",
            "pre-meal diagnosis requires forecasts (or a valid forecast_run_id)",
            422,
        )

    for row in forecast_rows:
        dish_id = str(row.get("dish_id"))
        prediction = float(row.get("prediction", 0))
        lower = float(row.get("lower_bound", prediction))
        upper = float(row.get("upper_bound", prediction))
        sources = ["predictions", "forecast_bounds"]
        caveats = [
            "Pre-meal risk is an estimate from synthetic forecasts; it is not a measured outcome.",
            "Rule-based risk scores do not establish causation.",
        ]
        evidence: list[EvidenceOut] = [
            EvidenceOut(field="forecast_prediction", value=round(prediction, 2), source="predictions"),
            EvidenceOut(field="forecast_lower_bound", value=round(lower, 2), source="predictions"),
            EvidenceOut(field="forecast_upper_bound", value=round(upper, 2), source="predictions"),
        ]
        causes: list[CauseOut] = []
        if dish_id not in planned:
            caveats.append(f"No planned prepared quantity supplied for {dish_id}; leftover risk unknown.")
            results.append(
                {
                    "dish_external_id": dish_id,
                    "risk_score": 0.0,
                    "risk_level": "unknown",
                    "confidence": 0.2,
                    "causes": [],
                    "evidence": [item.model_dump() for item in evidence],
                    "caveats": caveats,
                    "data_sources": sources,
                }
            )
            continue

        prepared = float(planned[dish_id])
        evidence.append(
            EvidenceOut(field="planned_prepared_qty", value=prepared, source="planned_quantities")
        )
        leftover_exposure = max(0.0, prepared - prediction)
        leftover_risk = leftover_exposure / prepared if prepared else 0.0
        shortage_exposure = max(0.0, upper - prepared)
        shortage_risk = shortage_exposure / upper if upper else 0.0
        history_risk = float(request.historical_waste_rate or 0.0)
        if request.historical_waste_rate is not None:
            evidence.append(
                EvidenceOut(
                    field="historical_waste_rate",
                    value=round(history_risk, 3),
                    source="food_operations history",
                )
            )
            sources.append("food_operations")
        risk_score = min(1.0, 0.45 * leftover_risk + 0.35 * shortage_risk + 0.20 * history_risk)

        if prepared > prediction * 1.10 and leftover_exposure > 0:
            causes.append(
                CauseOut(
                    code="over_preparation_risk",
                    title="Planned quantity materially exceeds forecast demand",
                    confidence=min(0.85, 0.5 + leftover_risk * 0.3),
                    evidence=[
                        EvidenceOut(field="planned_prepared_qty", value=prepared, source="plan"),
                        EvidenceOut(field="forecast_prediction", value=round(prediction, 2), source="forecast"),
                        EvidenceOut(
                            field="excess_over_forecast",
                            value=round(leftover_exposure, 2),
                            comparison="planned - prediction",
                            source="derived",
                        ),
                    ],
                    explanation=(
                        "Prepared quantity exceeds forecast demand by more than 10%, which is "
                        "associated with higher untouched-leftover exposure."
                    ),
                )
            )
        if prepared < lower:
            causes.append(
                CauseOut(
                    code="shortage_risk",
                    title="Planned quantity is below the lower forecast bound",
                    confidence=0.7,
                    evidence=[
                        EvidenceOut(field="planned_prepared_qty", value=prepared, source="plan"),
                        EvidenceOut(field="forecast_lower_bound", value=round(lower, 2), source="forecast"),
                    ],
                    explanation=(
                        "The plan is below the lower demand bound, so even the low-demand "
                        "scenario could exceed available portions."
                    ),
                )
            )
        interval_width = max(0.0, upper - lower)
        if prediction > 0 and interval_width / prediction > 0.4:
            causes.append(
                CauseOut(
                    code="forecast_uncertainty",
                    title="Wide empirical forecast interval",
                    confidence=0.45,
                    evidence=[
                        EvidenceOut(field="interval_width", value=round(interval_width, 2), source="forecast"),
                        EvidenceOut(field="prediction", value=round(prediction, 2), source="forecast"),
                    ],
                    explanation=(
                        "The forecast interval is wide relative to the point forecast; "
                        "the interval is empirical, not statistically calibrated."
                    ),
                )
            )
        if history_risk >= 0.20:
            causes.append(
                CauseOut(
                    code="historical_waste_pattern",
                    title="Historically elevated waste rate",
                    confidence=0.4,
                    evidence=[
                        EvidenceOut(
                            field="historical_waste_rate",
                            value=round(history_risk, 3),
                            comparison=">= 0.20",
                            source="food_operations",
                        )
                    ],
                    explanation=(
                        "Historical synthetic outcomes show an elevated waste rate. This is a "
                        "correlational signal, not a causal claim."
                    ),
                )
            )

        results.append(
            {
                "dish_external_id": dish_id,
                "risk_score": round(risk_score, 4),
                "risk_level": _risk_level(risk_score),
                "confidence": round(min(0.85, 0.35 + 0.1 * len(causes)), 4),
                "causes": [cause.model_dump() for cause in causes],
                "evidence": [item.model_dump() for item in evidence],
                "caveats": caveats,
                "data_sources": sources,
            }
        )
    return results


def _persist_pre_meal(db: Session, request: PreMealDiagnosisRequest, results: list[dict]) -> str | None:
    last_id = None
    for result in results:
        diagnosis = Diagnosis(
            diagnosis_type="pre_meal",
            target_date=request.service_date,
            meal_type=request.meal_type,
            dish_external_id=result["dish_external_id"],
            risk_score=result["risk_score"],
            confidence=result["confidence"],
            causes=result["causes"],
            evidence=result["evidence"],
            caveats=result["caveats"],
            data_sources=result["data_sources"],
            llm_used=False,
            is_synthetic=True,
        )
        db.add(diagnosis)
        db.flush()
        last_id = diagnosis.id
    return last_id


def diagnose_pre_meal(
    db: Session | None, request: PreMealDiagnosisRequest, forecasts: list[dict] | None = None
) -> list[dict]:
    rows = forecasts
    if rows is None and request.forecast_run_id:
        if db is None:
            raise DomainError("DIAGNOSIS_EVIDENCE_MISSING", "database session required", 500)
        predictions = list(
            db.scalars(
                select(Prediction).where(Prediction.forecast_run_id == request.forecast_run_id)
            ).all()
        )
        if not predictions:
            raise DomainError(
                "FORECAST_RUN_NOT_FOUND",
                f"no persisted predictions for forecast_run_id {request.forecast_run_id}",
                404,
            )
        rows = [
            {
                "dish_id": item.dish_external_id,
                "prediction": item.prediction,
                "lower_bound": item.lower_bound,
                "upper_bound": item.upper_bound,
            }
            for item in predictions
            if request.meal_type is None or item.meal_type == request.meal_type
        ]
    results = estimate_pre_meal_risk(request, rows)
    for result in results:
        result.setdefault("diagnosis_type", "pre_meal")
        result.setdefault("target_date", request.service_date)
        result.setdefault("meal_type", request.meal_type)
        result.setdefault("llm_used", False)
        result.setdefault("is_synthetic", True)
    if request.persist and db is not None:
        for result in results:
            result["id"] = _persist_pre_meal(
                db,
                request,
                [result],
            )
    return results


def _recent_menu_count(db: Session, dish_external_id: str, service_date: date) -> int:
    window_start = service_date - timedelta(days=7)
    return int(
        db.scalar(
            select(func.count())
            .select_from(MenuItem)
            .join(Dish, MenuItem.dish_id == Dish.id)
            .where(
                Dish.external_id == dish_external_id,
                MenuItem.date >= window_start,
                MenuItem.date < service_date,
            )
        )
        or 0
    )


def diagnose_run(
    db: Session,
    run_id: str,
    recent_menu_counts: dict[str, int] | None = None,
    context_baseline: dict | None = None,
    persist: bool = True,
) -> dict:
    run = db.get(MealRun, run_id)
    if run is None:
        raise DomainError("RUN_NOT_FOUND", f"simulation run not found: {run_id}", 404)
    outcome = db.scalar(select(Outcome).where(Outcome.run_id == run_id))
    if run.status != "finished" or outcome is None:
        raise DomainError(
            "RUN_NOT_FINISHED",
            "post-meal diagnosis requires a finished simulation with persisted outcomes",
            409,
            {"run_id": run_id, "status": run.status},
        )
    events = list(
        db.scalars(
            select(SimulationEvent)
            .where(SimulationEvent.run_id == run_id)
            .order_by(SimulationEvent.interval_index)
        ).all()
    )
    forecast_expected = None
    if run.forecast_run_id:
        predictions = list(
            db.scalars(
                select(Prediction).where(
                    Prediction.forecast_run_id == run.forecast_run_id,
                    Prediction.meal_type == run.meal_type,
                )
            ).all()
        )
        if run.dish_external_id:
            predictions = [
                item for item in predictions if item.dish_external_id == run.dish_external_id
            ]
        if predictions:
            forecast_expected = float(sum(item.prediction for item in predictions))
    if forecast_expected is None:
        config_forecast = (run.config or {}).get("forecast_expected")
        forecast_expected = float(config_forecast) if config_forecast is not None else None

    actual_demand = float(outcome.served_total + outcome.shortage)
    caveats = [
        "Post-meal diagnosis is retrospective and rule-based; correlation is not causation.",
        "All outcomes come from a simulated service, not a real VIT kitchen.",
        "No LLM was used to invent or explain evidence.",
    ]
    sources = ["outcomes", "simulation_events", "predictions", "menu_items"]
    evidence: list[EvidenceOut] = [
        EvidenceOut(field="prepared_total", value=outcome.prepared_total, source="outcomes"),
        EvidenceOut(field="served_total", value=outcome.served_total, source="outcomes"),
        EvidenceOut(field="actual_demand", value=round(actual_demand, 2), source="derived"),
        EvidenceOut(field="untouched_leftover", value=outcome.untouched_leftover, source="outcomes"),
        EvidenceOut(field="plate_waste", value=outcome.plate_waste, source="outcomes"),
        EvidenceOut(field="shortage", value=outcome.shortage, source="outcomes"),
    ]
    causes: list[CauseOut] = []

    over_ratio = (outcome.prepared_total / actual_demand) if actual_demand > 0 else 0.0
    if (
        actual_demand > 0
        and outcome.prepared_total > actual_demand * 1.10
        and outcome.untouched_leftover > 0
    ):
        causes.append(
            CauseOut(
                code="over_preparation",
                title="Prepared quantity exceeded realized demand",
                confidence=min(0.9, 0.55 + min(0.3, (over_ratio - 1.10) * 0.5)),
                evidence=[
                    EvidenceOut(field="prepared_total", value=outcome.prepared_total, source="outcomes"),
                    EvidenceOut(field="actual_demand", value=round(actual_demand, 2), source="derived"),
                    EvidenceOut(
                        field="prepared_to_demand_ratio",
                        value=round(over_ratio, 3),
                        comparison="> 1.10",
                        source="derived",
                    ),
                    EvidenceOut(
                        field="untouched_leftover",
                        value=outcome.untouched_leftover,
                        source="outcomes",
                    ),
                ],
                explanation=(
                    "More portions were prepared than were demanded, and untouched leftovers "
                    "remain. Timing/consumption explanations should be checked before assigning cause."
                ),
            )
        )

    if forecast_expected is not None and actual_demand > 0:
        abs_error = abs(forecast_expected - actual_demand)
        pct_error = abs_error / actual_demand
        evidence.append(
            EvidenceOut(
                field="forecast_error_pct",
                value=round(pct_error, 3),
                source="predictions vs outcomes",
            )
        )
        if pct_error >= 0.15:
            causes.append(
                CauseOut(
                    code="demand_forecast_error",
                    title="Demand forecast error contributed to imbalance",
                    confidence=min(0.8, 0.45 + pct_error * 0.5),
                    evidence=[
                        EvidenceOut(
                            field="forecast_expected", value=round(forecast_expected, 2), source="predictions"
                        ),
                        EvidenceOut(
                            field="actual_demand", value=round(actual_demand, 2), source="outcomes"
                        ),
                        EvidenceOut(
                            field="absolute_error", value=round(abs_error, 2), source="derived"
                        ),
                        EvidenceOut(
                            field="percentage_error", value=round(pct_error, 3), source="derived"
                        ),
                    ],
                    explanation=(
                        "Forecast and realized demand differ materially. This describes forecast "
                        "error, not proof that the model caused the waste."
                    ),
                )
            )

    menu_count = None
    if recent_menu_counts and run.dish_external_id in recent_menu_counts:
        menu_count = int(recent_menu_counts[run.dish_external_id])
    elif run.dish_external_id:
        menu_count = _recent_menu_count(db, run.dish_external_id, run.service_date)
    if menu_count is not None and menu_count >= 3:
        evidence.append(
            EvidenceOut(
                field="menu_appearances_last_7_days",
                value=menu_count,
                comparison=">= 3",
                source="menu_items",
            )
        )
        causes.append(
            CauseOut(
                code="menu_repetition",
                title="Dish repeated frequently in the preceding week",
                confidence=0.4,
                evidence=[
                    EvidenceOut(
                        field="menu_appearances_last_7_days",
                        value=menu_count,
                        comparison=">= 3",
                        source="menu_items",
                    )
                ],
                explanation=(
                    "Menu repetition is associated with lower variety. It is only a candidate "
                    "explanation when waste or a demand shortfall is also observed."
                ),
            )
        )

    if context_baseline:
        current_occupancy = float(context_baseline.get("current_occupancy_rate", 0))
        baseline_occupancy = float(context_baseline.get("baseline_occupancy_rate", 0))
        current_rain = float(context_baseline.get("current_rain_mm", 0))
        occupancy_delta = current_occupancy - baseline_occupancy
        if abs(occupancy_delta) >= 0.10 or current_rain >= 5:
            evidence.extend(
                [
                    EvidenceOut(
                        field="occupancy_rate_delta",
                        value=round(occupancy_delta, 4),
                        source="synthetic_context",
                    ),
                    EvidenceOut(field="rain_mm", value=current_rain, source="synthetic_context"),
                ]
            )
            causes.append(
                CauseOut(
                    code="availability_context_shift",
                    title="Occupancy or weather context differed from the baseline",
                    confidence=0.35,
                    evidence=[
                        EvidenceOut(
                            field="occupancy_rate_delta",
                            value=round(occupancy_delta, 4),
                            comparison="|delta| >= 0.10",
                            source="synthetic_context",
                        ),
                        EvidenceOut(
                            field="rain_mm",
                            value=current_rain,
                            comparison=">= 5 mm",
                            source="synthetic_context",
                        ),
                    ],
                    explanation=(
                        "Context differed from the comparison baseline. This is a correlational "
                        "signal, not evidence of a specific causal mechanism."
                    ),
                )
            )

    total_arrivals = sum(event.arrivals for event in events)
    if events and total_arrivals > 0:
        final_window = max(1, len(events) // 4)
        late_arrivals = sum(event.arrivals for event in events[-final_window:])
        late_share = late_arrivals / total_arrivals
        if late_share >= 0.40:
            evidence.append(
                EvidenceOut(
                    field="late_arrival_share",
                    value=round(late_share, 3),
                    comparison=">= 0.40",
                    source="simulation_events",
                )
            )
            causes.append(
                CauseOut(
                    code="timing_mismatch",
                    title="Late arrival concentration overlapped with service timing",
                    confidence=0.4,
                    evidence=[
                        EvidenceOut(
                            field="late_arrival_share",
                            value=round(late_share, 3),
                            comparison=">= 0.40",
                            source="simulation_events",
                        )
                    ],
                    explanation=(
                        "A large share of arrivals occurred near the end of service. This can "
                        "relate to batch timing, but the simulator does not prove causality."
                    ),
                )
            )

    causes.sort(key=lambda item: item.confidence, reverse=True)
    if not causes:
        caveats.append(
            "No candidate cause exceeded the evidence thresholds; no cause is asserted."
        )
    risk_score = 0.0
    if outcome.prepared_total > 0:
        risk_score = min(
            1.0,
            (outcome.untouched_leftover + outcome.plate_waste) / outcome.prepared_total,
        )
    overall_confidence = min(0.9, max([cause.confidence for cause in causes], default=0.2))

    diagnosis = Diagnosis(
        run_id=run_id,
        diagnosis_type="post_meal",
        target_date=run.service_date,
        meal_type=run.meal_type,
        dish_external_id=run.dish_external_id,
        risk_score=round(risk_score, 4),
        confidence=round(overall_confidence, 4),
        causes=[cause.model_dump() for cause in causes],
        evidence=[item.model_dump() for item in evidence],
        caveats=caveats,
        data_sources=sources,
        llm_used=False,
        is_synthetic=True,
    )
    diagnosis_id = None
    if persist:
        db.add(diagnosis)
        db.flush()
        diagnosis_id = diagnosis.id
    return {
        "id": diagnosis_id,
        "diagnosis_type": "post_meal",
        "target_date": run.service_date,
        "meal_type": run.meal_type,
        "dish_external_id": run.dish_external_id,
        "risk_score": diagnosis.risk_score,
        "confidence": diagnosis.confidence,
        "causes": [cause.model_dump() for cause in causes],
        "evidence": [item.model_dump() for item in evidence],
        "caveats": caveats,
        "data_sources": sources,
        "llm_used": False,
        "is_synthetic": True,
    }
