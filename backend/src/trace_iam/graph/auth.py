from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, cast

import msal  # type: ignore[import-untyped]

GRAPH_DELEGATED_SCOPES = (
    "AuditLog.Read.All",
    "Policy.Read.ConditionalAccess",
    "DeviceManagementManagedDevices.Read.All",
)


class MsalPublicClient(Protocol):
    def get_accounts(self) -> list[dict[str, Any]]: ...
    def acquire_token_silent(self, scopes: list[str], account: dict[str, Any]) -> dict[str, Any] | None: ...
    def acquire_token_interactive(self, scopes: list[str]) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class GraphAuthConfig:
    client_id: str
    tenant_id: str

    def __post_init__(self) -> None:
        if not self.client_id.strip() or not self.tenant_id.strip():
            raise ValueError("Graph client_id and tenant_id are required")

    @property
    def authority(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}"


class DelegatedGraphTokenProvider:
    """Interactive delegated Graph authentication for a local public-client application."""

    def __init__(self, config: GraphAuthConfig, app: MsalPublicClient | None = None) -> None:
        self._app = app or cast(
            MsalPublicClient,
            msal.PublicClientApplication(config.client_id, authority=config.authority),
        )

    def __call__(self) -> str:
        scopes = list(GRAPH_DELEGATED_SCOPES)
        accounts = self._app.get_accounts()
        result: dict[str, Any] | None = None
        if accounts:
            result = self._app.acquire_token_silent(scopes=scopes, account=accounts[0])
        if not result:
            result = self._app.acquire_token_interactive(scopes=scopes)
        token = result.get("access_token") if result else None
        if not isinstance(token, str) or not token.strip():
            error = result.get("error") if result else "authentication_failed"
            description = result.get("error_description") if result else None
            detail = f": {description}" if isinstance(description, str) and description else ""
            raise RuntimeError(f"Microsoft identity authentication failed ({error}){detail}")
        return token
