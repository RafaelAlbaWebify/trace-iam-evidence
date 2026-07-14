from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, cast

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from trace_iam.domain import (
    CasePriority,
    EvidenceFact,
    EvidenceItem,
    Investigation,
    InvestigationStatus,
)

from .models import AnalysisRunRecord, InvestigationRecord
from .serialization import (
    dumps,
    evidence_items_from_data,
    evidence_items_to_data,
    facts_from_json,
    facts_to_json,
    investigation_from_json,
    investigation_to_json,
    loads,
)

JsonObject = dict[str, Any]


class EvidenceRetentionMode(StrEnum):
    FULL_REDACTED = "full_redacted"
    METADATA_ONLY = "metadata_only"


@dataclass(frozen=True, slots=True)
class InvestigationSummary:
    investigation_id: str
    title: str
    scenario_type: str
    status: InvestigationStatus
    priority: CasePriority
    external_reference: str | None
    summary: str | None
    created_at: datetime
    archived_at: datetime | None
    analysis_run_count: int


@dataclass(frozen=True, slots=True)
class StoredAnalysisRun:
    run_number: int
    created_at: datetime
    ruleset_version: str
    facts: tuple[EvidenceFact, ...]
    evidence_snapshot: tuple[EvidenceItem, ...]
    findings: list[JsonObject]
    report_json: JsonObject
    report_markdown: str


class InvestigationRepository:
    def __init__(
        self,
        engine: Engine,
        retention_mode: EvidenceRetentionMode = EvidenceRetentionMode.FULL_REDACTED,
    ) -> None:
        self._engine = engine
        self._retention_mode = retention_mode

    @property
    def retention_mode(self) -> EvidenceRetentionMode:
        return self._retention_mode

    def _retained_evidence(self, evidence_items: tuple[EvidenceItem, ...]) -> tuple[EvidenceItem, ...]:
        if self._retention_mode is EvidenceRetentionMode.FULL_REDACTED:
            return evidence_items
        return tuple(replace(item, original_excerpt=None) for item in evidence_items)

    def _retained_investigation(self, investigation: Investigation) -> Investigation:
        return replace(
            investigation,
            evidence_items=self._retained_evidence(investigation.evidence_items),
        )

    def save_investigation(self, investigation: Investigation) -> None:
        retained = self._retained_investigation(investigation)
        with Session(self._engine) as session:
            record = session.get(InvestigationRecord, retained.id)
            snapshot = investigation_to_json(retained)
            if record is None:
                record = InvestigationRecord(
                    id=retained.id,
                    title=retained.title,
                    scenario_type=retained.scenario_type.value,
                    status=retained.status.value,
                    created_at=retained.created_at,
                    archived_at=None,
                    snapshot_json=snapshot,
                )
                session.add(record)
            else:
                record.title = retained.title
                record.scenario_type = retained.scenario_type.value
                record.status = retained.status.value
                record.snapshot_json = snapshot
            session.commit()

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        with Session(self._engine) as session:
            record = session.get(InvestigationRecord, investigation_id)
            return None if record is None else investigation_from_json(record.snapshot_json)

    def list_investigations(self, *, include_archived: bool = False) -> tuple[InvestigationSummary, ...]:
        with Session(self._engine) as session:
            run_counts = (
                select(
                    AnalysisRunRecord.investigation_id,
                    func.count(AnalysisRunRecord.id).label("run_count"),
                )
                .group_by(AnalysisRunRecord.investigation_id)
                .subquery()
            )
            query = (
                select(InvestigationRecord, func.coalesce(run_counts.c.run_count, 0))
                .outerjoin(run_counts, run_counts.c.investigation_id == InvestigationRecord.id)
                .order_by(InvestigationRecord.created_at.desc(), InvestigationRecord.id)
            )
            if not include_archived:
                query = query.where(InvestigationRecord.archived_at.is_(None))
            rows = session.execute(query).all()
            summaries: list[InvestigationSummary] = []
            for record, run_count in rows:
                investigation = investigation_from_json(record.snapshot_json)
                summaries.append(
                    InvestigationSummary(
                        investigation_id=record.id,
                        title=record.title,
                        scenario_type=record.scenario_type,
                        status=InvestigationStatus(record.status),
                        priority=investigation.priority,
                        external_reference=investigation.external_reference,
                        summary=investigation.summary,
                        created_at=record.created_at,
                        archived_at=record.archived_at,
                        analysis_run_count=int(run_count),
                    )
                )
            return tuple(summaries)

    def archive_investigation(self, investigation_id: str) -> Investigation:
        return self._set_archive_state(investigation_id, archived=True)

    def reopen_investigation(self, investigation_id: str) -> Investigation:
        return self._set_archive_state(investigation_id, archived=False)

    def _set_archive_state(self, investigation_id: str, *, archived: bool) -> Investigation:
        with Session(self._engine) as session:
            record = session.get(InvestigationRecord, investigation_id)
            if record is None:
                raise KeyError(f"Investigation {investigation_id!r} does not exist")
            investigation = investigation_from_json(record.snapshot_json)
            if archived:
                if investigation.status is InvestigationStatus.ARCHIVED:
                    return investigation
                updated = replace(
                    investigation,
                    status=InvestigationStatus.ARCHIVED,
                    pre_archive_status=investigation.status,
                )
            else:
                if investigation.status is not InvestigationStatus.ARCHIVED:
                    return investigation
                restored_status = investigation.pre_archive_status or InvestigationStatus.ANALYZED
                updated = replace(
                    investigation,
                    status=restored_status,
                    pre_archive_status=None,
                )
            record.status = updated.status.value
            record.archived_at = (
                datetime.now(timezone.utc).replace(tzinfo=None) if archived else None
            )
            record.snapshot_json = investigation_to_json(updated)
            session.commit()
            return updated

    def append_analysis_run(
        self,
        investigation_id: str,
        *,
        ruleset_version: str,
        facts: tuple[EvidenceFact, ...],
        evidence_snapshot: tuple[EvidenceItem, ...],
        findings: list[JsonObject],
        report_json: JsonObject,
        report_markdown: str,
    ) -> StoredAnalysisRun:
        if not ruleset_version.strip():
            raise ValueError("Ruleset version must not be blank")
        if not evidence_snapshot:
            raise ValueError("Analysis runs require an evidence snapshot")
        if any(item.validated_at is None for item in evidence_snapshot):
            raise ValueError("Analysis runs accept only validated case evidence")
        retained_snapshot = self._retained_evidence(evidence_snapshot)
        snapshot_data = evidence_items_to_data(retained_snapshot)
        stored_report_json = {**report_json, "evidence_snapshot": snapshot_data}
        stored_report_markdown = self._with_evidence_snapshot(report_markdown, retained_snapshot)
        with Session(self._engine) as session:
            if session.get(InvestigationRecord, investigation_id) is None:
                raise KeyError(f"Investigation {investigation_id!r} does not exist")
            query = select(func.max(AnalysisRunRecord.run_number)).where(
                AnalysisRunRecord.investigation_id == investigation_id
            )
            next_number = (session.scalar(query) or 0) + 1
            created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            record = AnalysisRunRecord(
                investigation_id=investigation_id,
                run_number=next_number,
                created_at=created_at,
                ruleset_version=ruleset_version,
                facts_json=facts_to_json(facts),
                findings_json=dumps(findings),
                report_json=dumps(stored_report_json),
                report_markdown=stored_report_markdown,
            )
            session.add(record)
            session.commit()
            return StoredAnalysisRun(
                run_number=next_number,
                created_at=created_at,
                ruleset_version=ruleset_version,
                facts=facts,
                evidence_snapshot=retained_snapshot,
                findings=findings,
                report_json=stored_report_json,
                report_markdown=stored_report_markdown,
            )

    def list_analysis_runs(self, investigation_id: str) -> tuple[StoredAnalysisRun, ...]:
        with Session(self._engine) as session:
            records = session.scalars(
                select(AnalysisRunRecord)
                .where(AnalysisRunRecord.investigation_id == investigation_id)
                .order_by(AnalysisRunRecord.run_number)
            ).all()
            return tuple(self._stored_run(record) for record in records)

    def get_analysis_run(self, investigation_id: str, run_number: int) -> StoredAnalysisRun | None:
        with Session(self._engine) as session:
            record = session.scalar(
                select(AnalysisRunRecord).where(
                    AnalysisRunRecord.investigation_id == investigation_id,
                    AnalysisRunRecord.run_number == run_number,
                )
            )
            return None if record is None else self._stored_run(record)

    @staticmethod
    def _with_evidence_snapshot(
        report_markdown: str,
        evidence_snapshot: tuple[EvidenceItem, ...],
    ) -> str:
        lines = [report_markdown.rstrip(), "", "## Evidence snapshot", ""]
        for item in evidence_snapshot:
            captured = item.captured_at.isoformat() if item.captured_at else "not recorded"
            validated = item.validated_at.isoformat() if item.validated_at else "not validated"
            lines.append(
                f"- `{item.id}` — {item.kind.value}; source: {item.source}; "
                f"reliability: {item.reliability.value}; captured: {captured}; validated: {validated}"
            )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _stored_run(record: AnalysisRunRecord) -> StoredAnalysisRun:
        report_json = cast(JsonObject, loads(record.report_json))
        raw_snapshot = cast(list[JsonObject], report_json.get("evidence_snapshot", []))
        return StoredAnalysisRun(
            run_number=record.run_number,
            created_at=record.created_at,
            ruleset_version=record.ruleset_version,
            facts=facts_from_json(record.facts_json),
            evidence_snapshot=evidence_items_from_data(raw_snapshot),
            findings=cast(list[JsonObject], loads(record.findings_json)),
            report_json=report_json,
            report_markdown=record.report_markdown,
        )
