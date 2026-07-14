from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query

from trace_iam.domain import CasePriority, InvestigationStatus, ScenarioType
from trace_iam.operational import build_operational_dashboard
from trace_iam.persistence.repository import InvestigationRepository
from trace_iam.persistence.runtime import get_repository, get_timeline_repository
from trace_iam.persistence.timeline import TimelineRepository

router = APIRouter(prefix="/api/operations", tags=["operations"])


@router.get("/dashboard")
def operational_dashboard(
    query: str | None = Query(default=None, max_length=120),
    status: InvestigationStatus | None = Query(default=None),
    scenario: ScenarioType | None = Query(default=None),
    priority: CasePriority | None = Query(default=None),
    include_archived: bool = Query(default=False),
    repository: InvestigationRepository = Depends(get_repository),
    timeline_repository: TimelineRepository = Depends(get_timeline_repository),
) -> dict[str, Any]:
    summaries = repository.list_investigations(include_archived=True)
    latest_activity = {}
    for item in summaries:
        events = timeline_repository.list_events(item.investigation_id, newest_first=True)
        if events:
            latest_activity[item.investigation_id] = events[0].created_at
    return asdict(
        build_operational_dashboard(
            summaries,
            latest_activity=latest_activity,
            query=query,
            status=status,
            scenario=scenario,
            priority=priority,
            include_archived=include_archived,
        )
    )
