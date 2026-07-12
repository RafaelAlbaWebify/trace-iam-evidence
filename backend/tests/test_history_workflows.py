from pathlib import Path

from fastapi.testclient import TestClient

from trace_iam.domain import EvidenceItem, EvidenceKind, Investigation, ScenarioType
from trace_iam.main import app
from trace_iam.persistence import (
    EvidenceRetentionMode,
    InvestigationRepository,
    sqlite_engine,
)
from trace_iam.persistence.runtime import get_repository, migrate_database


def repository_for(tmp_path: Path) -> InvestigationRepository:
    database_path = tmp_path / "history.db"
    migrate_database(database_path)
    return InvestigationRepository(sqlite_engine(database_path))


def test_analysis_is_persisted_and_exportable(tmp_path: Path) -> None:
    repository = repository_for(tmp_path)
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    response = client.post(
        "/api/investigations/analyze-conditional-access",
        json={
            "investigation_id": "history-1",
            "title": "Persist this analysis",
            "evidence_id": "manual-1",
            "source": "public-safe test",
            "conditional_access_failed": True,
            "policy_name": "Require compliant device",
            "redacted": True,
        },
    )

    try:
        assert response.status_code == 200
        assert response.json()["run_number"] == 1

        listing = client.get("/api/investigations").json()
        assert listing[0]["investigation_id"] == "history-1"
        assert listing[0]["analysis_run_count"] == 1
        assert listing[0]["status"] == "analyzed"

        runs = client.get("/api/investigations/history-1/runs").json()
        assert runs == [
            {
                "run_number": 1,
                "created_at": runs[0]["created_at"],
                "ruleset_version": "CA-001@1.0.0",
                "finding_count": 1,
            }
        ]

        json_report = client.get(
            "/api/investigations/history-1/runs/1/report.json"
        )
        markdown_report = client.get(
            "/api/investigations/history-1/runs/1/report.md"
        )
        assert json_report.status_code == 200
        assert json_report.json()["investigation"]["id"] == "history-1"
        assert markdown_report.status_code == 200
        assert "Persist this analysis" in markdown_report.text
    finally:
        app.dependency_overrides.clear()


def test_archive_hides_history_and_reopen_restores_it(tmp_path: Path) -> None:
    repository = repository_for(tmp_path)
    repository.save_investigation(
        Investigation(
            id="archive-1",
            title="Archive test",
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        )
    )
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        archived = client.post("/api/investigations/archive-1/archive")
        assert archived.status_code == 200
        assert archived.json()["status"] == "archived"
        assert client.get("/api/investigations").json() == []
        assert client.get("/api/investigations?include_archived=true").json()[0][
            "status"
        ] == "archived"

        reopened = client.post("/api/investigations/archive-1/reopen")
        assert reopened.status_code == 200
        assert reopened.json()["status"] == "analyzed"
        assert client.get("/api/investigations").json()[0]["investigation_id"] == (
            "archive-1"
        )
    finally:
        app.dependency_overrides.clear()


def test_metadata_only_retention_removes_original_excerpt(tmp_path: Path) -> None:
    database_path = tmp_path / "retention.db"
    migrate_database(database_path)
    repository = InvestigationRepository(
        sqlite_engine(database_path),
        retention_mode=EvidenceRetentionMode.METADATA_ONLY,
    )
    repository.save_investigation(
        Investigation(
            id="retention-1",
            title="Retention test",
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
            evidence_items=(
                EvidenceItem(
                    id="evidence-retention-1",
                    kind=EvidenceKind.GENERIC_TEXT_EXCERPT,
                    source="public-safe test",
                    original_excerpt="This content must not be retained",
                ),
            ),
        )
    )

    restored = repository.get_investigation("retention-1")
    assert restored is not None
    assert restored.evidence_items[0].original_excerpt is None
    assert repository.retention_mode is EvidenceRetentionMode.METADATA_ONLY
