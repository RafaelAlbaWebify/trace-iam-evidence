from dataclasses import replace
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from trace_iam.domain import (
    Confidence,
    EvidenceFact,
    EvidenceItem,
    EvidenceKind,
    EvidenceReliability,
    Investigation,
    InvestigationStatus,
    ScenarioType,
)
from trace_iam.persistence import InvestigationRepository, sqlite_engine


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def test_migration_creates_schema_on_empty_database(tmp_path: Path) -> None:
    database_path = tmp_path / "trace.db"
    migrate(database_path)

    tables = set(inspect(sqlite_engine(database_path)).get_table_names())
    assert {"alembic_version", "investigations", "analysis_runs"} <= tables


def test_investigation_and_evidence_round_trip_without_loss(tmp_path: Path) -> None:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    repository = InvestigationRepository(sqlite_engine(database_path))
    investigation = Investigation(
        id="investigation-persist-1",
        title="Persisted Conditional Access review",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.ANALYZED,
        affected_subject="redacted-user",
        evidence_items=(
            EvidenceItem(
                id="evidence-1",
                kind=EvidenceKind.ENTRA_SIGNIN_CSV,
                source="public-safe fixture",
                redacted=True,
            ),
        ),
    )

    repository.save_investigation(investigation)

    assert repository.get_investigation(investigation.id) == investigation


def test_archive_and_reopen_restore_the_prior_lifecycle_state(tmp_path: Path) -> None:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    repository = InvestigationRepository(sqlite_engine(database_path))
    reviewed = Investigation(
        id="investigation-reviewed-1",
        title="Reviewed access case",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.REVIEWED,
    )
    repository.save_investigation(reviewed)

    archived = repository.archive_investigation(reviewed.id)
    assert archived.status is InvestigationStatus.ARCHIVED
    assert archived.pre_archive_status is InvestigationStatus.REVIEWED

    reopened = repository.reopen_investigation(reviewed.id)
    assert reopened.status is InvestigationStatus.REVIEWED
    assert reopened.pre_archive_status is None
    assert repository.get_investigation(reviewed.id) == reopened


def test_analysis_runs_are_append_only_and_reports_reload(tmp_path: Path) -> None:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    repository = InvestigationRepository(sqlite_engine(database_path))
    validated_at = datetime(2026, 7, 14, 1, 30)
    evidence = EvidenceItem(
        id="evidence-1",
        kind=EvidenceKind.ENTRA_SIGNIN_CSV,
        source="public-safe fixture",
        reliability=EvidenceReliability.HIGH,
        validated_at=validated_at,
    )
    investigation = Investigation(
        id="investigation-history-1",
        title="Conditional Access history",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.EVIDENCE_VALIDATED,
        evidence_items=(evidence,),
    )
    fact = EvidenceFact(
        fact_type="conditional_access_failed",
        value=True,
        source_evidence_id="evidence-1",
        certainty=Confidence.HIGH,
    )
    repository.save_investigation(investigation)

    first = repository.append_analysis_run(
        investigation.id,
        ruleset_version="CA-001@1.0.0",
        facts=(fact,),
        findings=[{"rule_id": "CA-001", "confidence": "high"}],
        report_json={"investigation_id": investigation.id, "finding_count": 1},
        report_markdown="# First report",
    )
    second = repository.append_analysis_run(
        investigation.id,
        ruleset_version="CA-001@1.0.0",
        facts=(fact,),
        findings=[{"rule_id": "CA-001", "confidence": "medium"}],
        report_json={"investigation_id": investigation.id, "finding_count": 1},
        report_markdown="# Second report",
    )

    runs = repository.list_analysis_runs(investigation.id)
    assert (first.run_number, second.run_number) == (1, 2)
    assert [run.run_number for run in runs] == [1, 2]
    assert runs[0].findings[0]["confidence"] == "high"
    assert runs[0].report_markdown.startswith("# First report")
    assert "## Evidence snapshot" in runs[0].report_markdown
    assert runs[0].evidence_snapshot == (evidence,)
    assert runs[0].report_json["evidence_snapshot"][0]["id"] == "evidence-1"
    assert runs[1].findings[0]["confidence"] == "medium"
    assert runs[1].facts == (fact,)


def test_live_evidence_changes_do_not_mutate_earlier_run_snapshots(tmp_path: Path) -> None:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    repository = InvestigationRepository(sqlite_engine(database_path))
    validated_at = datetime(2026, 7, 14, 2, 0)
    original = EvidenceItem(
        id="evidence-original",
        kind=EvidenceKind.GENERIC_TEXT_EXCERPT,
        source="redacted sign-in log",
        original_excerpt="failure before policy evaluation",
        reliability=EvidenceReliability.HIGH,
        validated_at=validated_at,
    )
    investigation = Investigation(
        id="investigation-snapshot-1",
        title="Immutable evidence history",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.EVIDENCE_VALIDATED,
        evidence_items=(original,),
    )
    fact = EvidenceFact(
        fact_type="conditional_access_failed",
        value=True,
        source_evidence_id=original.id,
        certainty=Confidence.HIGH,
    )
    repository.save_investigation(investigation)
    repository.append_analysis_run(
        investigation.id,
        ruleset_version="CA-001@1.0.0",
        facts=(fact,),
        findings=[{"rule_id": "CA-001"}],
        report_json={"investigation_id": investigation.id},
        report_markdown="# Snapshot report",
    )

    changed = replace(
        original,
        source="later redacted export",
        original_excerpt="later observation",
        validated_at=None,
    )
    repository.save_investigation(
        replace(
            investigation,
            status=InvestigationStatus.DRAFT,
            evidence_items=(changed,),
        )
    )

    stored = repository.get_analysis_run(investigation.id, 1)
    assert stored is not None
    assert stored.evidence_snapshot == (original,)
    assert stored.report_json["evidence_snapshot"][0]["source"] == "redacted sign-in log"
    assert repository.get_investigation(investigation.id) is not None
    assert repository.get_investigation(investigation.id).evidence_items == (changed,)
