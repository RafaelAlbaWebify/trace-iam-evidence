from fastapi.testclient import TestClient

from trace_iam.api.app import app


client = TestClient(app)


def test_case_metadata_and_controlled_lifecycle() -> None:
    created = client.post(
        "/api/investigations",
        json={
            "title": "Priority access review",
            "scenario_type": "conditional_access",
            "priority": "high",
            "external_reference": "INC-REDACTED-42",
            "summary": "Redacted authentication failure under investigation.",
        },
    )
    assert created.status_code == 201
    case = created.json()
    investigation_id = case["investigation_id"]
    assert case["priority"] == "high"
    assert case["external_reference"] == "INC-REDACTED-42"

    updated = client.patch(
        f"/api/investigations/{investigation_id}",
        json={"priority": "critical", "summary": "Escalated redacted access-impact review."},
    )
    assert updated.status_code == 200
    assert updated.json()["priority"] == "critical"

    invalid = client.post(
        f"/api/investigations/{investigation_id}/transition",
        json={"status": "reviewed"},
    )
    assert invalid.status_code == 409

    validated = client.post(
        f"/api/investigations/{investigation_id}/transition",
        json={"status": "evidence_validated"},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "evidence_validated"

    listed = client.get("/api/investigations")
    assert listed.status_code == 200
    matching = next(item for item in listed.json() if item["investigation_id"] == investigation_id)
    assert matching["priority"] == "critical"
    assert matching["external_reference"] == "INC-REDACTED-42"
