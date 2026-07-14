from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from trace_iam.domain import InvestigationStatus
from trace_iam.persistence.repository import InvestigationRepository
from trace_iam.persistence.runtime import get_repository, get_timeline_repository
from trace_iam.persistence.timeline import (
    TimelineActorType,
    TimelineEvent,
    TimelineEventType,
    TimelineRepository,
)

router = APIRouter(prefix="/api/investigations", tags=["timeline"])


class TimelineEventResponse(BaseModel):
    event_id: int
    investigation_id: str
    created_at: datetime
    event_type: str
    actor_type: str
    actor_label: str
    summary: str
    details: dict[str, object]


class OperatorNoteRequest(BaseModel):
    author: str = Field(min_length=2, max_length=80)
    note: str = Field(min_length=3, max_length=1000)

    @field_validator("author", "note")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("Timeline values must not be blank")
        return stripped


class ReportExportEventRequest(BaseModel):
    run_number: int = Field(ge=1)
    report_format: str

    @field_validator("report_format")
    @classmethod
    def validate_report_format(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"json", "markdown"}:
            raise ValueError("Report format must be json or markdown")
        return normalized


def _response(event: TimelineEvent) -> TimelineEventResponse:
    return TimelineEventResponse(
        event_id=event.event_id,
        investigation_id=event.investigation_id,
        created_at=event.created_at,
        event_type=event.event_type.value,
        actor_type=event.actor_type.value,
        actor_label=event.actor_label,
        summary=event.summary,
        details=event.details,
    )


@router.get("/{investigation_id}/timeline", response_model=list[TimelineEventResponse])
def list_timeline(
    investigation_id: str,
    newest_first: bool = Query(default=False),
    repository: TimelineRepository = Depends(get_timeline_repository),
) -> list[TimelineEventResponse]:
    try:
        return [
            _response(event)
            for event in repository.list_events(investigation_id, newest_first=newest_first)
        ]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{investigation_id}/timeline/notes",
    response_model=TimelineEventResponse,
    status_code=201,
)
def add_operator_note(
    investigation_id: str,
    request: OperatorNoteRequest,
    repository: TimelineRepository = Depends(get_timeline_repository),
    investigation_repository: InvestigationRepository = Depends(get_repository),
) -> TimelineEventResponse:
    investigation = investigation_repository.get_investigation(investigation_id)
    if investigation is None:
        raise HTTPException(status_code=404, detail="Investigation not found")
    if investigation.status is InvestigationStatus.ARCHIVED:
        raise HTTPException(status_code=409, detail="Archived investigations cannot receive timeline notes")
    try:
        event = repository.append(
            investigation_id,
            event_type=TimelineEventType.OPERATOR_NOTE,
            actor_type=TimelineActorType.OPERATOR,
            actor_label=request.author,
            summary=request.note,
            details={"redacted": True},
        )
        return _response(event)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/{investigation_id}/timeline/report-exports",
    response_model=TimelineEventResponse,
    status_code=201,
)
def record_report_export(
    investigation_id: str,
    request: ReportExportEventRequest,
    repository: TimelineRepository = Depends(get_timeline_repository),
    investigation_repository: InvestigationRepository = Depends(get_repository),
) -> TimelineEventResponse:
    run = investigation_repository.get_analysis_run(investigation_id, request.run_number)
    if run is None:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    try:
        event = repository.append(
            investigation_id,
            event_type=TimelineEventType.REPORT_EXPORTED,
            actor_type=TimelineActorType.OPERATOR,
            actor_label="Local operator",
            summary=f"Run {request.run_number} {request.report_format} report exported.",
            details={
                "run_number": request.run_number,
                "report_format": request.report_format,
                "ruleset_version": run.ruleset_version,
            },
        )
        return _response(event)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
