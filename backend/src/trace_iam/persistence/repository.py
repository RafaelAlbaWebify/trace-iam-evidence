from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Engine, Select, func, select
from sqlalchemy.orm import Session

from trace_iam.domain import EvidenceFact, Investigation

from .models import AnalysisRunRecord, InvestigationRecord
from .serialization import (
    dumps,
    facts_from_json,
    facts_to_json,
    investigation_from_json,
    investigation_to_json,
    loads,
)


@dataclass(frozen=True, slots=True)
class StoredAnalysisRun:
    run_number: int
    created_at: datetime
    ruleset_version: str
    facts: tuple[EvidenceFact, ...]
    findings: list[dict[str, Any]]
    report_json: dict[str, Any]
    report_markdown: str


class InvestigationRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def save_investigation(self, investigation: Investigation) -> None:
        with Session(self._engine) as session:
            record = session.get(InvestigationRecord, investigation.id)
            snapshot = investigation_to_json(investigation)
            if record is None:
                record = InvestigationRecord(
                    id=investigation.id,
                    title=investigation.title,
                    scenario_type=investigation.scenario_type.value,
                    status=investigation.status.value,
                    created_at=investigation.created_at,
                    archived_at=None,
                    snapshot_json=snapshot,
                )
                session.add(record)
            else:
                record.title = investigation.title
                record.scenario_type = investigation.scenario_type.value
                record.status = investigation.status.value
                record.snapshot_json = snapshot
            session.commit()

    def get_investigation(self, investigation_id: str) -> Investigation | None:
        with Session(self._engine) as session:
            record = session.get(InvestigationRecord, investigation_id)
            return None if record is None else investigation_from_json(record.snapshot_json)

    def append_analysis_run(
        self,
        investigation_id: str,
        *,
        ruleset_version: str,
        facts: tuple[EvidenceFact, ...],
        findings: list[dict[str, Any]],
        report_json: dict[str, Any],
        report_markdown: str,
    ) -> StoredAnalysisRun:
        if not ruleset_version.strip():
            raise ValueError("Ruleset version must not be blank")
        with Session(self._engine) as session:
            if session.get(InvestigationRecord, investigation_id) is None:
                raise KeyError(f"Investigation {investigation_id!r} does not exist")
            query: Select[tuple[int | None]] = select(func.max(AnalysisRunRecord.run_number)).where(
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
            return tuple(
                StoredAnalysisRun(
                    run_number=record.run_number,
                    created_at=record.created_at,
                    ruleset_version=record.ruleset_version,
                    facts=facts_from_json(record.facts_json),
                    findings=loads(record.findings_json),
                    report_json=loads(record.report_json),
                    report_markdown=record.report_markdown,
                )
                for record in records
            )
