import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from trace_iam.domain import (
    Confidence,
    EvidenceFact,
    EvidenceItem,
    EvidenceKind,
    Investigation,
    InvestigationStatus,
    ScenarioType,
)


def _default(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return str(value.value)
    raise TypeError(f"Unsupported JSON value: {type(value)!r}")


def dumps(value: object) -> str:
    return json.dumps(value, default=_default, sort_keys=True, separators=(",", ":"))


def loads(value: str) -> Any:
    return json.loads(value)


def investigation_to_json(investigation: Investigation) -> str:
    return dumps(asdict(investigation))


def investigation_from_json(payload: str) -> Investigation:
    data = loads(payload)
    evidence_items = tuple(
        EvidenceItem(
            id=item["id"],
            kind=EvidenceKind(item["kind"]),
            source=item["source"],
            captured_at=datetime.fromisoformat(item["captured_at"])
            if item["captured_at"]
            else None,
            subject=item["subject"],
            resource=item["resource"],
            redacted=item["redacted"],
            original_excerpt=item["original_excerpt"],
        )
        for item in data["evidence_items"]
    )
    return Investigation(
        id=data["id"],
        title=data["title"],
        scenario_type=ScenarioType(data["scenario_type"]),
        status=InvestigationStatus(data["status"]),
        affected_subject=data["affected_subject"],
        affected_resource=data["affected_resource"],
        evidence_items=evidence_items,
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def facts_to_json(facts: tuple[EvidenceFact, ...]) -> str:
    return dumps([asdict(fact) for fact in facts])


def facts_from_json(payload: str) -> tuple[EvidenceFact, ...]:
    return tuple(
        EvidenceFact(
            fact_type=item["fact_type"],
            value=item["value"],
            source_evidence_id=item["source_evidence_id"],
            certainty=Confidence(item["certainty"]),
            observed_at=datetime.fromisoformat(item["observed_at"])
            if item["observed_at"]
            else None,
        )
        for item in loads(payload)
    )
