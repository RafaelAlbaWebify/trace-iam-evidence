from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from trace_iam.domain import Investigation, ScenarioType
from trace_iam.main import app
from trace_iam.persistence import InvestigationRepository, sqlite_engine
from trace_iam.persistence.runtime import get_timeline_repository
from trace_iam.persistence.timeline import (
    TimelineActorType,
    TimelineEventType,
    TimelineRepository,
)


def migrate(database_path: Path) -> None:
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path}")
    command.upgrade(config, "head")


def repositories(tmp_path: Path) -> tuple[InvestigationRepository, TimelineRepository]:
    database_path = tmp_path / "trace.db"
    migrate(database_path)
    engine = sqlite_engine(database_path)
    return InvestigationRepository(engine), TimelineRepository(engine)


def test_migration_adds_append_only_timeline_table(tmp_path: Path) -> None:
    investigation_repository, _ = repositories(tmp_path)
    tables = set(inspect(investigation_repository._engine).get_table_names())
    assert "timeline_events" in tables


def test_timeline_preserves_order_and_attribution(tmp_path: Path) -> None:
    investigation_repository, timeline_repository = repositories(tmp_path)
    case = Investigation(
        id="trace-timeline-001",
        title="Timeline proof",
        scenario_type=ScenarioType.CONDITIONAL_ACCESS,
    )
    investigation_repository.save_investigation(case)

    created = timeline_repository.append(
        case.id,
        event_type=TimelineEventType.CASE_CREATED,
        actor_type=TimelineActorType.SYSTEM,
        actor_label="TRACE",
        summary="Investigation created.",
        details={"scenario_type": case.scenario_type.value},
    )
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
    assert [event.event_id for event in chronological] == [created.event_id, note.event_id]
    assert [event.event_id for event in newest_first] == [note.event_id, created.event_id]
    assert chronological[0].actor_type is TimelineActorType.SYSTEM
    assert chronological[1].actor_label == "Rafael"
    assert chronological[1].details == {"redacted": True}


def test_operator_note_api_is_attributed_and_redacted(tmp_path: Path) -> None:
    investigation_repository, timeline_repository = repositories(tmp_path)
    case = Investigation(
        id="trace-timeline-api-001",
        title="Timeline API proof",
        scenario_type=ScenarioType.GUEST_B2B,
    )
    investigation_repository.save_investigation(case)
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
