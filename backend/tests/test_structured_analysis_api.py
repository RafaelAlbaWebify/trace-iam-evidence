from fastapi.testclient import TestClient

from trace_iam.main import app


client = TestClient(app)


def test_structured_conditional_access_evidence_generates_reports() -> None:
    response = client.post(
        "/api/investigations/analyze-conditional-access",
        json={
            "investigation_id": "investigation-ca-api-1",
            "title": "Conditional Access sign-in review",
            "evidence_id": "evidence-ca-api-1",
            "source": "redacted operator form",
            "conditional_access_failed": True,
            "conditional_access_succeeded": False,
            "policy_name": "Require compliant device",
            "redacted": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation_id"] == "investigation-ca-api-1"
    assert payload["evaluated_rule_ids"] == ["CA-001"]
    assert payload["finding_count"] == 1
    assert payload["json_report"]["findings"][0]["rule_id"] == "CA-001"
    assert "Do not disable Conditional Access globally" in payload["markdown_report"]


def test_successful_evaluation_does_not_create_block_finding() -> None:
    response = client.post(
        "/api/investigations/analyze-conditional-access",
        json={
            "investigation_id": "investigation-ca-api-2",
            "title": "Successful Conditional Access review",
            "evidence_id": "evidence-ca-api-2",
            "source": "redacted operator form",
            "conditional_access_failed": False,
            "conditional_access_succeeded": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["finding_count"] == 0
    assert payload["json_report"]["findings"] == []
    assert "No supported finding" in payload["markdown_report"]


def test_unredacted_manual_evidence_is_rejected() -> None:
    response = client.post(
        "/api/investigations/analyze-conditional-access",
        json={
            "investigation_id": "investigation-ca-api-3",
            "title": "Unsafe evidence submission",
            "evidence_id": "evidence-ca-api-3",
            "source": "operator form",
            "conditional_access_failed": True,
            "redacted": False,
        },
    )

    assert response.status_code == 422
    assert "TRACE accepts only redacted manual evidence" in response.text
