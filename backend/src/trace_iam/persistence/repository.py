from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, cast

from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from trace_iam.domain import CasePriority, EvidenceFact, Investigation, InvestigationStatus

from .models import AnalysisRunRecord, InvestigationRecord
from .serialization import (
    dumps,
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

    def _retained_investigation(self, investigation: Investigation) -> Investigation:
        if self._retention_mode is EvidenceRetentionMode.FULL_REDACTED:
            return investigation
        retained_items = tuple(
            replace(item, original_excerpt=None) for item in investigation.evidence_items
        )
        return replace(investigation, evidence_items=retained_items)

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
            next_status = InvestigationStatus.ARCHIVED if archived else InvestigationStatus.ANALYZED
            updated = replace(investigation, status=next_status)
            record.status = next_status.value
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
        findings: list[JsonObject],
        report_json: JsonObject,
        report_markdown: str,
    ) -> StoredAnalysisRun:
        if not ruleset_version.strip():
            raise ValueError("Ruleset version must not be blank")
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
                report_json=dumps(report_json),
                report_markdown=report_markdown,
            )
            session.add(record)
            session.commit()
            return StoredAnalysisRun(
                run_number=next_number,
                created_at=created_at,
                ruleset_version=ruleset_version,
                facts=facts,
                findings=findings,
                report_json=report_json,
                report_markdown=report_markdown,
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
    def _stored_run(record: AnalysisRunRecord) -> StoredAnalysisRun:
        return StoredAnalysisRun(
            run_number=record.run_number,
            created_at=record.created_at,
            ruleset_version=record.ruleset_version,
            facts=facts_from_json(record.facts_json),
            findings=cast(list[JsonObject], loads(record.findings_json)),
            report_json=cast(JsonObject, loads(record.report_json)),
            report_markdown=record.report_markdown,
        )
