from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.app.api.deps import get_db
from backend.app.services.exports import run_export, run_export_csv, traces_export_csv, traces_export_json

router = APIRouter(prefix="/exports", tags=["exports"])


@router.get("/runs/{run_id}")
def export_run(
    run_id: str,
    format: Literal["json", "csv"] = Query(default="json"),
    db: Session = Depends(get_db),
):
    if format == "csv":
        content = run_export_csv(db, run_id)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="run-{run_id}.csv"'},
        )
    return run_export(db, run_id)


@router.get("/agent-traces")
def export_agent_traces(
    format: Literal["json", "csv"] = Query(default="json"),
    trace_id: str | None = None,
    db: Session = Depends(get_db),
):
    if format == "csv":
        content = traces_export_csv(db, trace_id)
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="agent-traces.csv"'},
        )
    return traces_export_json(db, trace_id)
