from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from trace_iam.comparison import compare_runs
from trace_iam.persistence.repository import InvestigationRepository
from trace_iam.persistence.runtime import get_repository

router = APIRouter(prefix="/api/investigations", tags=["comparison"])


@router.get("/{investigation_id}/compare-runs")
def compare_analysis_runs(
    investigation_id: str,
    base_run: int = Query(ge=1),
    target_run: int = Query(ge=1),
    repository: InvestigationRepository = Depends(get_repository),
) -> dict[str, Any]:
    if base_run == target_run:
        raise HTTPException(status_code=422, detail="Select two different runs")
    base = repository.get_analysis_run(investigation_id, base_run)
    target = repository.get_analysis_run(investigation_id, target_run)
    if base is None or target is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    try:
        return asdict(compare_runs(base, target))
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
