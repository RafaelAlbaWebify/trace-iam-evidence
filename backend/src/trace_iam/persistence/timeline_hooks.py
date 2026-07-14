from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from .models import AnalysisRunRecord, InvestigationRecord, TimelineEventRecord
from .serialization import dumps, loads
from .timeline import TimelineActorType, TimelineEventType

JsonObject = dict[str, Any]
_installed = False


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _system_event(
    investigation_id: str,
    event_type: TimelineEventType,
    summary: str,
    details: JsonObject | None = None,
) -> TimelineEventRecord:
    return TimelineEventRecord(
        investigation_id=investigation_id,
        created_at=_now(),
        event_type=event_type.value,
        actor_type=TimelineActorType.SYSTEM.value,
        actor_label="TRACE",
        summary=summary,
        details_json=dumps(details or {}),
    )


def _snapshot(value: str | None) -> JsonObject:
    return cast(JsonObject, loads(value)) if value else {}


def _evidence_by_id(snapshot: JsonObject) -> dict[str, JsonObject]:
    raw_items = snapshot.get("evidence_items", [])
    if not isinstance(raw_items, list):
        return {}
    items: dict[str, JsonObject] = {}
    for raw in raw_items:
        if isinstance(raw, dict) and isinstance(raw.get("id"), str):
            items[cast(str, raw["id"])] = cast(JsonObject, raw)
    return items


def _investigation_events(record: InvestigationRecord) -> list[TimelineEventRecord]:
    state = inspect(record)
    if state.pending:
        return [
            _system_event(
                record.id,
                TimelineEventType.CASE_CREATED,
                "Investigation created.",
                {"title": record.title, "scenario_type": record.scenario_type, "status": record.status},
            )
        ]
    events: list[TimelineEventRecord] = []
    status_history = state.attrs.status.history
    if status_history.has_changes() and status_history.deleted:
        previous = cast(str, status_history.deleted[0])
        current = record.status
        event_type = (
            TimelineEventType.CASE_ARCHIVED
            if current == "archived"
            else TimelineEventType.CASE_REOPENED
            if previous == "archived"
            else TimelineEventType.STATUS_CHANGED
        )
        events.append(
            _system_event(
                record.id,
                event_type,
                f"Investigation status changed from {previous} to {current}.",
                {"from": previous, "to": current},
            )
        )
    snapshot_history = state.attrs.snapshot_json.history
    if snapshot_history.has_changes() and snapshot_history.deleted:
        previous_items = _evidence_by_id(_snapshot(cast(str, snapshot_history.deleted[0])))
        current_items = _evidence_by_id(_snapshot(record.snapshot_json))
        for evidence_id in sorted(current_items.keys() - previous_items.keys()):
            events.append(
                _system_event(
                    record.id,
                    TimelineEventType.EVIDENCE_ADDED,
                    f"Evidence {evidence_id} added.",
                    {"evidence_id": evidence_id, "source": current_items[evidence_id].get("source")},
                )
            )
        for evidence_id in sorted(previous_items.keys() - current_items.keys()):
            events.append(
                _system_event(
                    record.id,
                    TimelineEventType.EVIDENCE_REMOVED,
                    f"Evidence {evidence_id} removed before immutable analysis.",
                    {"evidence_id": evidence_id},
                )
            )
        for evidence_id in sorted(previous_items.keys() & current_items.keys()):
            before = previous_items[evidence_id].get("validated_at")
            after = current_items[evidence_id].get("validated_at")
            if not before and after:
                events.append(
                    _system_event(
                        record.id,
                        TimelineEventType.EVIDENCE_VALIDATED,
                        f"Evidence {evidence_id} validated.",
                        {"evidence_id": evidence_id, "validated_at": after},
                    )
                )
    return events


def _before_flush(session: Session, _flush_context: object, _instances: object) -> None:
    generated: list[TimelineEventRecord] = []
    for item in tuple(session.new):
        if isinstance(item, InvestigationRecord):
            generated.extend(_investigation_events(item))
        elif isinstance(item, AnalysisRunRecord):
            generated.append(
                _system_event(
                    item.investigation_id,
                    TimelineEventType.ANALYSIS_COMPLETED,
                    f"Analysis run {item.run_number} completed.",
                    {"run_number": item.run_number, "ruleset_version": item.ruleset_version},
                )
            )
    for item in tuple(session.dirty):
        if isinstance(item, InvestigationRecord):
            generated.extend(_investigation_events(item))
    if generated:
        session.add_all(generated)


def install_timeline_hooks() -> None:
    global _installed
    if _installed:
        return
    event.listen(Session, "before_flush", _before_flush)
    _installed = True
