from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, inspect

from trace_iam.domain import (
    Confidence,
    EvidenceFact,
    EvidenceItem,
    EvidenceKind,
    Investigation,
    InvestigationStatus,
    ScenarioType,
)
from trace_iam.main import app
from trace_iam.persistence import InvestigationRepository, sqlite_engine
from trace_iam.persistence.runtime import get_repository, get_timeline_repository
from trace_iam.persistence.timeline import (
    TimelineActorType,
    TimelineEventType,
    TimelineRepository,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def repositories(tmp_path: Path) -> tuple[Engine, InvestigationRepository, TimelineRepository]:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    engine = sqlite_engine(database_path)
    return engine, InvestigationRepository(engine), TimelineRepository(engine)


def test_migration_adds_append_only_timeline_table(tmp_path: Path) -> None:
    engine, _, _ = repositories(tmp_path)
    assert "timeline_events" in set(inspect(engine).get_table_names())


def test_timeline_preserves_order_and_attribution(tmp_path: Path) -> None:
    _, investigation_repository, timeline_repository = repositories(tmp_path)
    case = Investigation(
        id="trace-timeline-001",
        title="Timeline proof",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
    )
    investigation_repository.save_investigation(case)
    note = timeline_repository.append(
        case.id,
        event_type=TimelineEventType.OPERATOR_NOTE,
        actor_type=TimelineActorType.OPERATOR,
        actor_label="Rafael",
        summary="Redacted note added for escalation context.",
        details={"redacted": True},
    )

    chronological = timeline_repository.list_events(case.id)
    newest_first = timeline_repository.list_events(case.id, newest_first=True)
    assert chronological[0].event_type is TimelineEventType.CASE_CREATED
    assert chronological[0].actor_type is TimelineActorType.SYSTEM
    assert chronological[1].event_id == note.event_id
    assert [event.event_id for event in newest_first] == [note.event_id, chronological[0].event_id]
    assert chronological[1].actor_label == "Rafael"
    assert chronological[1].details == {"redacted": True}


def test_operator_note_api_is_attributed_and_redacted(tmp_path: Path) -> None:
    _, investigation_repository, timeline_repository = repositories(tmp_path)
    case = Investigation(
        id="trace-timeline-api-001",
        title="Timeline API proof",
        scenario_type=ScenarioType.GUEST_B2B,
    )
    investigation_repository.save_investigation(case)
    app.dependency_overrides[get_repository] = lambda: investigation_repository
    app.dependency_overrides[get_timeline_repository] = lambda: timeline_repository
    client = TestClient(app)
    try:
        response = client.post(
            f"/api/investigations/{case.id}/timeline/notes",
            json={"author": "Rafael", "note": "Redacted follow-up requested from the application owner."},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["event_type"] == "operator_note"
        assert payload["actor_type"] == "operator"
        assert payload["actor_label"] == "Rafael"
        assert payload["details"] == {"redacted": True}

        listed = client.get(f"/api/investigations/{case.id}/timeline?newest_first=true")
        assert listed.status_code == 200
        assert listed.json()[0]["summary"].startswith("Redacted follow-up")
    finally:
        app.dependency_overrides.clear()


def test_archived_case_rejects_operator_notes(tmp_path: Path) -> None:
    _, investigation_repository, timeline_repository = repositories(tmp_path)
    case = Investigation(
        id="trace-timeline-archived-001",
        title="Archived timeline proof",
        scenario_type=ScenarioType.RESOURCE_ASSIGNMENT,
    )
    investigation_repository.save_investigation(case)
    investigation_repository.archive_investigation(case.id)
    app.dependency_overrides[get_repository] = lambda: investigation_repository
    app.dependency_overrides[get_timeline_repository] = lambda: timeline_repository
    client = TestClient(app)
    try:
        response = client.post(
            f"/api/investigations/{case.id}/timeline/notes",
            json={"author": "Rafael", "note": "This note must not be accepted while archived."},
        )
        assert response.status_code == 409
        assert response.json()["detail"].startswith("Archived investigations")
    finally:
        app.dependency_overrides.clear()


def test_report_export_is_recorded_as_operator_timeline_event(tmp_path: Path) -> None:
    _, investigation_repository, timeline_repository = repositories(tmp_path)
    validated_at = datetime(2026, 7, 14, 10, 0)
    evidence = EvidenceItem(
        id="timeline-export-evidence",
        kind=EvidenceKind.GENERIC_TEXT_EXCERPT,
        source="Redacted export proof",
        validated_at=validated_at,
    )
    case = Investigation(
        id="trace-timeline-export-001",
        title="Timeline export proof",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        status=InvestigationStatus.EVIDENCE_VALIDATED,
        evidence_items=(evidence,),
    )
    fact = EvidenceFact(
        fact_type="conditional_access_failed",
        value=True,
        source_evidence_id=evidence.id,
        certainty=Confidence.HIGH,
    )
    investigation_repository.save_investigation(case)
    investigation_repository.append_analysis_run(
        case.id,
        ruleset_version="CA-001@1.0.0",
        facts=(fact,),
        findings=[{"rule_id": "CA-001"}],
        report_json={"investigation_id": case.id},
        report_markdown="# Export proof",
    )
    app.dependency_overrides[get_repository] = lambda: investigation_repository
    app.dependency_overrides[get_timeline_repository] = lambda: timeline_repository
    client = TestClient(app)
    try:
        response = client.post(
            f"/api/investigations/{case.id}/timeline/report-exports",
            json={"run_number": 1, "report_format": "json"},
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload["event_type"] == "report_exported"
        assert payload["actor_type"] == "operator"
        assert payload["details"] == {
            "run_number": 1,
            "report_format": "json",
            "ruleset_version": "CA-001@1.0.0",
        }
    finally:
        app.dependency_overrides.clear()
