import json

import httpx
import pytest

from trace_iam.graph import GraphClient, GraphError


def response(status: int, payload: dict[str, object], headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status, content=json.dumps(payload), headers=headers)


def test_sign_ins_follow_odata_next_link_and_keep_query_on_first_page_only() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            assert request.url.params["$filter"] == "userId eq 'redacted-user-id'"
            assert "conditionalAccessStatus" in request.url.params["$select"]
            return response(200, {"value": [{"id": "signin-1"}], "@odata.nextLink": "https://graph.microsoft.com/v1.0/auditLogs/signIns?$skiptoken=opaque"})
        assert "$filter" not in request.url.params
        return response(200, {"value": [{"id": "signin-2"}]})

    with GraphClient(lambda: "test-token", transport=httpx.MockTransport(handler)) as client:
        result = client.list_sign_ins(filter_expression="userId eq 'redacted-user-id'")

    assert [item["id"] for item in result.values] == ["signin-1", "signin-2"]
    assert result.request_count == 2
    assert requests[0].headers["Authorization"] == "Bearer test-token"


def test_intune_managed_devices_uses_read_only_collection() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/deviceManagement/managedDevices")
        assert "complianceState" in request.url.params["$select"]
        return response(200, {"value": [{"id": "device-1", "complianceState": "noncompliant"}]})

    with GraphClient(lambda: "test-token", transport=httpx.MockTransport(handler)) as client:
        result = client.list_managed_devices()
    assert result.values[0]["complianceState"] == "noncompliant"


def test_conditional_access_policy_collection_is_explicit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/identity/conditionalAccess/policies")
        assert "grantControls" in request.url.params["$select"]
        return response(200, {"value": [{"id": "policy-1", "displayName": "Require compliant device"}]})

    with GraphClient(lambda: "test-token", transport=httpx.MockTransport(handler)) as client:
        result = client.list_conditional_access_policies()
    assert result.values[0]["displayName"] == "Require compliant device"


@pytest.mark.parametrize(("status", "category"), [(401, "authentication"), (403, "authorization")])
def test_authentication_and_authorization_failures_are_distinct(status: int, category: str) -> None:
    transport = httpx.MockTransport(lambda _: response(status, {"error": {"code": "Denied"}}))
    with GraphClient(lambda: "test-token", transport=transport) as client:
        with pytest.raises(GraphError) as caught:
            client.list_sign_ins()
    assert caught.value.status_code == status
    assert caught.value.category == category


def test_429_respects_retry_after_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return response(429, {"error": {"code": "TooManyRequests"}}, {"Retry-After": "2"})
        return response(200, {"value": [{"id": "signin-after-retry"}]})

    with GraphClient(
        lambda: "test-token",
        transport=httpx.MockTransport(handler),
        sleeper=sleeps.append,
    ) as client:
        result = client.list_sign_ins()
    assert result.values[0]["id"] == "signin-after-retry"
    assert sleeps == [2.0]


def test_empty_token_is_rejected_before_request() -> None:
    with GraphClient(lambda: "", transport=httpx.MockTransport(lambda _: response(200, {"value": []}))) as client:
        with pytest.raises(GraphError) as caught:
            client.list_sign_ins()
    assert caught.value.category == "authentication"
