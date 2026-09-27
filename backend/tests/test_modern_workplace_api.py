from fastapi.testclient import TestClient

from trace_iam.main import app


def test_modern_workplace_demo_exposes_graph_entra_intune_correlation() -> None:
    with TestClient(app) as client:
        response = client.post("/api/modern-workplace/demo")
    assert response.status_code == 200
    payload = response.json()
    assert payload["investigation_id"] == "trace-modern-workplace-demo"
    assert "CA-002" in payload["evaluated_rule_ids"]
    assert payload["finding_count"] >= 2
    sources = " ".join(payload["evidence_sources"])
    assert "/auditLogs/signIns" in sources
    assert "/identity/conditionalAccess/policies" in sources
    assert "/deviceManagement/managedDevices" in sources
    report = payload["json_report"]
    titles = [finding["title"] for finding in report["findings"]]
    assert any("noncompliant device evidence" in title for title in titles)
    correlation = next(f for f in report["findings"] if f["rule_id"] == "CA-002")
    assert any("does not prove" in item for item in correlation["limitations"])
