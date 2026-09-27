from __future__ import annotations

from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from time import sleep
from typing import Any, Callable, Mapping, Protocol

import httpx


class TokenProvider(Protocol):
    def __call__(self) -> str: ...


@dataclass(frozen=True, slots=True)
class GraphResponse:
    values: tuple[dict[str, Any], ...]
    request_count: int


class GraphError(RuntimeError):
    def __init__(self, status_code: int, category: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.category = category


class GraphClient:
    """Small read-only Microsoft Graph v1.0 client with explicit operational behavior."""

    def __init__(
        self,
        token_provider: TokenProvider,
        *,
        transport: httpx.BaseTransport | None = None,
        base_url: str = "https://graph.microsoft.com/v1.0",
        max_retries: int = 2,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self._token_provider = token_provider
        self._client = httpx.Client(base_url=base_url, transport=transport, timeout=15.0)
        self._max_retries = max_retries
        self._sleeper = sleeper

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> GraphClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def list_sign_ins(self, *, filter_expression: str | None = None) -> GraphResponse:
        params = {
            "$select": (
                "id,createdDateTime,userId,appId,resourceDisplayName,status,"
                "conditionalAccessStatus,appliedConditionalAccessPolicies,deviceDetail"
            )
        }
        if filter_expression:
            params["$filter"] = filter_expression
        return self._get_collection("/auditLogs/signIns", params=params)

    def list_conditional_access_policies(self) -> GraphResponse:
        return self._get_collection(
            "/identity/conditionalAccess/policies",
            params={"$select": "id,displayName,state,conditions,grantControls"},
        )

    def list_managed_devices(self, *, filter_expression: str | None = None) -> GraphResponse:
        params = {
            "$select": (
                "id,deviceName,userId,operatingSystem,osVersion,complianceState,"
                "managementAgent,lastSyncDateTime,azureADDeviceId"
            )
        }
        if filter_expression:
            params["$filter"] = filter_expression
        return self._get_collection("/deviceManagement/managedDevices", params=params)

    def _get_collection(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> GraphResponse:
        values: list[dict[str, Any]] = []
        request_count = 0
        next_url: str | None = path
        next_params: Mapping[str, str] | None = params
        while next_url:
            payload = self._request(next_url, params=next_params)
            request_count += 1
            page_values = payload.get("value")
            if not isinstance(page_values, list):
                raise GraphError(502, "invalid_response", "Graph collection response has no value array")
            values.extend(item for item in page_values if isinstance(item, dict))
            raw_next = payload.get("@odata.nextLink")
            next_url = raw_next if isinstance(raw_next, str) and raw_next else None
            next_params = None
        return GraphResponse(values=tuple(values), request_count=request_count)

    def _request(self, url: str, *, params: Mapping[str, str] | None) -> dict[str, Any]:
        attempts = 0
        while True:
            token = self._token_provider().strip()
            if not token:
                raise GraphError(401, "authentication", "Token provider returned no access token")
            response = self._client.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            if response.status_code == 429 and attempts < self._max_retries:
                attempts += 1
                self._sleeper(_retry_after_seconds(response.headers.get("Retry-After")))
                continue
            if response.status_code == 401:
                raise GraphError(401, "authentication", "Microsoft Graph rejected the access token")
            if response.status_code == 403:
                raise GraphError(
                    403,
                    "authorization",
                    "Microsoft Graph denied the request; review consent, permissions, roles, and licensing",
                )
            if response.status_code == 429:
                raise GraphError(429, "throttled", "Microsoft Graph throttling persisted after retry budget")
            if response.is_error:
                raise GraphError(response.status_code, "graph_http", f"Microsoft Graph returned HTTP {response.status_code}")
            payload = response.json()
            if not isinstance(payload, dict):
                raise GraphError(502, "invalid_response", "Microsoft Graph returned a non-object JSON payload")
            return payload


def _retry_after_seconds(value: str | None) -> float:
    if value is None:
        return 1.0
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            from datetime import datetime, timezone

            retry_at = parsedate_to_datetime(value)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError):
            return 1.0
