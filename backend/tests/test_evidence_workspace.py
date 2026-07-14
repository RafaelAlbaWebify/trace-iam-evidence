from pathlib import Path

from fastapi.testclient import TestClient

from trace_iam.domain import Investigation, InvestigationStatus, ScenarioType
from trace_iam.main import app
from trace_iam.persistence import InvestigationRepository, sqlite_engine
from trace_iam.persistence.runtime import get_repository, migrate_database


def repository_for(tmp_path: Path) -> InvestigationRepository:
    database_path = tmp_path / "evidence-workspace.db"
    migrate_database(database_path)
    return InvestigationRepository(sqlite_engine(database_path))


def test_multiple_evidence_items_are_persisted_and_validated(tmp_path: Path) -> None:
    repository = repository_for(tmp_path)
    repository.save_investigation(
        Investigation(
            id="evidence-case-1",
            title="Evidence workspace",
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        )
    )
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        first = client.post(
            "/api/investigations/evidence-case-1/evidence",
            json={
                "evidence_id": "signin-export-1",
                "kind": "entra_signin_csv",
                "source": "Redacted Entra export",
                "captured_at": "2026-07-14T00:00:00",
                "reliability": "high",
                "notes": "Export collected during the incident window.",
                "redacted": True,
            },
        )
        second = client.post(
            "/api/investigations/evidence-case-1/evidence",
            json={
                "evidence_id": "operator-note-1",
                "kind": "generic_text_excerpt",
                "source": "Redacted operator note",
                "excerpt": "Application access failed after device replacement.",
                "reliability": "medium",
                "redacted": True,
            },
        )

        assert first.status_code == 201
        assert second.status_code == 201
        assert [item["evidence_id"] for item in client.get(
            "/api/investigations/evidence-case-1/evidence"
        ).json()] == ["signin-export-1", "operator-note-1"]

        validated_first = client.post(
            "/api/investigations/evidence-case-1/evidence/signin-export-1/validate"
        )
        assert validated_first.status_code == 200
        assert repository.get_investigation("evidence-case-1").status is InvestigationStatus.DRAFT

        validated_second = client.post(
            "/api/investigations/evidence-case-1/evidence/operator-note-1/validate"
        )
        assert validated_second.status_code == 200
        restored = repository.get_investigation("evidence-case-1")
        assert restored is not None
        assert restored.status is InvestigationStatus.EVIDENCE_VALIDATED
        assert all(item.validated_at is not None for item in restored.evidence_items)
        assert restored.evidence_items[0].reliability.value == "high"
    finally:
        app.dependency_overrides.clear()


def test_evidence_changes_reset_validation_and_reject_duplicates(tmp_path: Path) -> None:
    repository = repository_for(tmp_path)
    repository.save_investigation(
        Investigation(
            id="evidence-case-2",
            title="Evidence validation reset",
            scenario_type=ScenarioType.GUEST_B2B,
        )
    )
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        payload = {
            "evidence_id": "guest-note-1",
            "kind": "generic_text_excerpt",
            "source": "Redacted guest support note",
            "excerpt": "Invitation redemption failed.",
            "redacted": True,
        }
        assert client.post(
            "/api/investigations/evidence-case-2/evidence", json=payload
        ).status_code == 201
        assert client.post(
            "/api/investigations/evidence-case-2/evidence", json=payload
        ).status_code == 409
        assert client.post(
            "/api/investigations/evidence-case-2/evidence/guest-note-1/validate"
        ).status_code == 200

        updated = client.patch(
            "/api/investigations/evidence-case-2/evidence/guest-note-1",
            json={"reliability": "low", "notes": "Needs corroboration."},
        )
        assert updated.status_code == 200
        assert updated.json()["validated_at"] is None
        restored = repository.get_investigation("evidence-case-2")
        assert restored is not None
        assert restored.status is InvestigationStatus.DRAFT
    finally:
        app.dependency_overrides.clear()


def test_archived_or_analyzed_evidence_is_protected(tmp_path: Path) -> None:
    repository = repository_for(tmp_path)
    repository.save_investigation(
        Investigation(
            id="evidence-case-3",
            title="Protected evidence",
            scenario_type=ScenarioType.CONDITIONAL_ACCESS,
        )
    )
    app.dependency_overrides[get_repository] = lambda: repository
    client = TestClient(app)

    try:
        assert client.post(
            "/api/investigations/evidence-case-3/evidence",
            json={
                "evidence_id": "protected-1",
                "kind": "manual_structured",
                "source": "Redacted structured evidence",
                "redacted": True,
            },
        ).status_code == 201

        assert client.post("/api/investigations/evidence-case-3/archive").status_code == 200
        assert client.patch(
            "/api/investigations/evidence-case-3/evidence/protected-1",
            json={"notes": "Attempted archived edit."},
        ).status_code == 409
    finally:
        app.dependency_overrides.clear()
