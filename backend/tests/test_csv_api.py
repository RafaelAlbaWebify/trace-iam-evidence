from fastapi.testclient import TestClient

from trace_iam.main import app

client = TestClient(app)

CSV_TEXT = """Sign-in ID,Conditional Access Status,Failure Reason,Conditional Access Policy
signin-001,failure,Device is not compliant,Require compliant device
"""


def test_csv_api_generates_conditional_access_report() -> None:
    response = client.post(
        "/api/investigations/analyze-conditional-access-csv",
        json={
            "investigation_id": "investigation-csv-api-1",
            "title": "CSV Conditional Access review",
            "source": "public-safe sample",
            "csv_text": CSV_TEXT,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["finding_count"] == 1
    assert payload["evaluated_rule_ids"] == ["CA-001"]
    assert payload["json_report"]["findings"][0]["rule_id"] == "CA-001"
    assert "Require compliant device" not in payload["markdown_report"] or payload["markdown_report"]


def test_csv_api_returns_actionable_validation_error() -> None:
    response = client.post(
        "/api/investigations/analyze-conditional-access-csv",
        json={
            "investigation_id": "investigation-csv-api-2",
            "title": "Malformed CSV review",
            "source": "public-safe sample",
            "csv_text": "Sign-in ID,Conditional Access Status\n1,unknown\n",
        },
    )

    assert response.status_code == 422
    assert "missing required headers" in response.json()["detail"]
