import json
from dataclasses import asdict
from datetime import datetime
from enum import StrEnum
from typing import Any, cast

from trace_iam.domain import (
    CasePriority,
    Confidence,
    EvidenceFact,
    EvidenceItem,
    EvidenceKind,
    EvidenceReliability,
    Investigation,
    InvestigationStatus,
    ScenarioType,
)

JsonObject = dict[str, Any]


def _default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def dumps(value: object) -> str:
    return json.dumps(value, default=_default, sort_keys=True, separators=(",", ":"))


def loads(value: str) -> Any:
    return json.loads(value)


def evidence_items_to_data(evidence_items: tuple[EvidenceItem, ...]) -> list[JsonObject]:
    return cast(list[JsonObject], loads(dumps([asdict(item) for item in evidence_items])))


def evidence_items_from_data(items: list[JsonObject]) -> tuple[EvidenceItem, ...]:
    return tuple(
        EvidenceItem(
            id=cast(str, item["id"]),
            kind=EvidenceKind(cast(str, item["kind"])),
            source=cast(str, item["source"]),
            captured_at=(
                datetime.fromisoformat(cast(str, item["captured_at"]))
                if item.get("captured_at")
                else None
            ),
            subject=cast(str | None, item.get("subject")),
            resource=cast(str | None, item.get("resource")),
            redacted=cast(bool, item.get("redacted", True)),
            original_excerpt=cast(str | None, item.get("original_excerpt")),
            reliability=EvidenceReliability(
                cast(str, item.get("reliability", EvidenceReliability.UNKNOWN.value))
            ),
            notes=cast(str | None, item.get("notes")),
            validated_at=(
                datetime.fromisoformat(cast(str, item["validated_at"]))
                if item.get("validated_at")
                else None
            ),
        )
        for item in items
    )


def investigation_to_json(investigation: Investigation) -> str:
    return dumps(asdict(investigation))


def investigation_from_json(payload: str) -> Investigation:
    data = cast(JsonObject, loads(payload))
    raw_items = cast(list[JsonObject], data["evidence_items"])
    evidence_items = evidence_items_from_data(raw_items)
    raw_pre_archive_status = cast(str | None, data.get("pre_archive_status"))
    return Investigation(
        id=cast(str, data["id"]),
        title=cast(str, data["title"]),
        scenario_type=ScenarioType(cast(str, data["scenario_type"])),
        status=InvestigationStatus(cast(str, data["status"])),
        priority=CasePriority(cast(str, data.get("priority", CasePriority.NORMAL.value))),
        external_reference=cast(str | None, data.get("external_reference")),
        summary=cast(str | None, data.get("summary")),
        affected_subject=cast(str | None, data.get("affected_subject")),
        affected_resource=cast(str | None, data.get("affected_resource")),
        evidence_items=evidence_items,
        created_at=datetime.fromisoformat(cast(str, data["created_at"])),
        pre_archive_status=(
            InvestigationStatus(raw_pre_archive_status) if raw_pre_archive_status else None
        ),
    )


def facts_to_json(facts: tuple[EvidenceFact, ...]) -> str:
    return dumps([asdict(fact) for fact in facts])


def facts_from_json(payload: str) -> tuple[EvidenceFact, ...]:
    items = cast(list[JsonObject], loads(payload))
    return tuple(
        EvidenceFact(
            fact_type=cast(str, item["fact_type"]),
            value=cast(str | int | bool, item["value"]),
            source_evidence_id=cast(str, item["source_evidence_id"]),
            certainty=Confidence(cast(str, item["certainty"])),
            observed_at=(
                datetime.fromisoformat(cast(str, item["observed_at"]))
                if item["observed_at"]
                else None
            ),
        )
        for item in items
    )
