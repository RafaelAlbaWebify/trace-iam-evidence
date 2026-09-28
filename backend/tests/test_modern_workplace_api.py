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


def test_graph_status_is_safe_when_live_connection_is_not_configured(monkeypatch) -> None:
    monkeypatch.delenv("TRACE_GRAPH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TRACE_GRAPH_TENANT_ID", raising=False)
    with TestClient(app) as client:
        response = client.get("/api/modern-workplace/graph/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["mode"] == "delegated-read-only"
    assert "DeviceManagementManagedDevices.Read.All" in payload["scopes"]


def test_live_graph_collection_refuses_unconfigured_runtime() -> None:
    with TestClient(app) as client:
        demo = client.post("/api/modern-workplace/demo").json()
        response = client.post(
            "/api/modern-workplace/graph/collect",
            json={
                "investigation_id": demo["investigation_id"],
                "sign_in_filter": "userId eq 'redacted'",
                "managed_device_filter": "userId eq 'redacted'",
            },
        )
    assert response.status_code == 503
    assert "TRACE_GRAPH_CLIENT_ID" in response.json()["detail"]


def test_modern_workplace_demo_can_be_reloaded_without_external_state() -> None:
    with TestClient(app) as client:
        first = client.post("/api/modern-workplace/demo")
        second = client.post("/api/modern-workplace/demo")
        evidence = client.get("/api/investigations/trace-modern-workplace-demo/evidence")
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["investigation_id"] == first.json()["investigation_id"]
    assert second.json()["run_number"] > first.json()["run_number"]
    assert evidence.status_code == 200
    sources = {item["source"] for item in evidence.json()}
    assert sources == {
        "Microsoft Graph /auditLogs/signIns",
        "Microsoft Graph /identity/conditionalAccess/policies",
        "Microsoft Graph /deviceManagement/managedDevices",
    }
