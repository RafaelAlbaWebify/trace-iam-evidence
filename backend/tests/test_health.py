from fastapi.testclient import TestClient

from trace_iam.main import app


client = TestClient(app)


def test_health_endpoint_reports_product_status() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "product": "TRACE IAM Evidence",
        "version": "0.1.0",
    }
