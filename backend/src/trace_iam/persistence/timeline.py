from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, cast

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from .models import InvestigationRecord, TimelineEventRecord
from .serialization import dumps, loads

JsonObject = dict[str, Any]


class TimelineActorType(StrEnum):
    SYSTEM = "system"
    OPERATOR = "operator"


class TimelineEventType(StrEnum):
    CASE_CREATED = "case_created"
    EVIDENCE_ADDED = "evidence_added"
    EVIDENCE_VALIDATED = "evidence_validated"
    EVIDENCE_REMOVED = "evidence_removed"
    ANALYSIS_COMPLETED = "analysis_completed"
    STATUS_CHANGED = "status_changed"
    CASE_ARCHIVED = "case_archived"
    CASE_REOPENED = "case_reopened"
    REPORT_EXPORTED = "report_exported"
    OPERATOR_NOTE = "operator_note"


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    event_id: int
    investigation_id: str
    created_at: datetime
    event_type: TimelineEventType
    actor_type: TimelineActorType
    actor_label: str
    summary: str
    details: JsonObject


class TimelineRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def append(
        self,
        investigation_id: str,
        *,
        event_type: TimelineEventType,
        actor_type: TimelineActorType,
        actor_label: str,
        summary: str,
        details: JsonObject | None = None,
    ) -> TimelineEvent:
        if not actor_label.strip():
            raise ValueError("Timeline actor label must not be blank")
        if not summary.strip():
            raise ValueError("Timeline summary must not be blank")
        with Session(self._engine) as session:
            if session.get(InvestigationRecord, investigation_id) is None:
                raise KeyError(f"Investigation {investigation_id!r} does not exist")
            created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            record = TimelineEventRecord(
                investigation_id=investigation_id,
                created_at=created_at,
                event_type=event_type.value,
                actor_type=actor_type.value,
                actor_label=actor_label.strip(),
                summary=summary.strip(),
                details_json=dumps(details or {}),
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return self._event(record)

    def list_events(
        self,
        investigation_id: str,
        *,
        newest_first: bool = False,
    ) -> tuple[TimelineEvent, ...]:
        with Session(self._engine) as session:
            if session.get(InvestigationRecord, investigation_id) is None:
                raise KeyError(f"Investigation {investigation_id!r} does not exist")
            ordering = (
                (TimelineEventRecord.created_at.desc(), TimelineEventRecord.id.desc())
                if newest_first
                else (TimelineEventRecord.created_at, TimelineEventRecord.id)
            )
            records = session.scalars(
                select(TimelineEventRecord)
                .where(TimelineEventRecord.investigation_id == investigation_id)
                .order_by(*ordering)
            ).all()
            return tuple(self._event(record) for record in records)

    @staticmethod
    def _event(record: TimelineEventRecord) -> TimelineEvent:
        return TimelineEvent(
            event_id=record.id,
            investigation_id=record.investigation_id,
            created_at=record.created_at,
            event_type=TimelineEventType(record.event_type),
            actor_type=TimelineActorType(record.actor_type),
            actor_label=record.actor_label,
            summary=record.summary,
            details=cast(JsonObject, loads(record.details_json)),
        )
