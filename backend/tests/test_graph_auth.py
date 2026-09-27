from typing import Any

import pytest

from trace_iam.graph.auth import DelegatedGraphTokenProvider, GRAPH_DELEGATED_SCOPES, GraphAuthConfig


class FakeMsal:
    def __init__(self, silent: dict[str, Any] | None, interactive: dict[str, Any]) -> None:
        self.silent = silent
        self.interactive = interactive
        self.interactive_calls = 0
        self.scopes: list[str] = []

    def get_accounts(self) -> list[dict[str, Any]]:
        return [{"home_account_id": "redacted"}]

    def acquire_token_silent(self, scopes: list[str], account: dict[str, Any]) -> dict[str, Any] | None:
        self.scopes = scopes
        return self.silent

    def acquire_token_interactive(self, scopes: list[str]) -> dict[str, Any]:
        self.interactive_calls += 1
        self.scopes = scopes
        return self.interactive


def test_delegated_provider_prefers_silent_cached_token() -> None:
    fake = FakeMsal({"access_token": "cached-token"}, {"access_token": "interactive-token"})
    provider = DelegatedGraphTokenProvider(GraphAuthConfig("client", "tenant"), app=fake)
    assert provider() == "cached-token"
    assert fake.interactive_calls == 0
    assert set(fake.scopes) == set(GRAPH_DELEGATED_SCOPES)


def test_delegated_provider_falls_back_to_interactive_pkce_flow() -> None:
    fake = FakeMsal(None, {"access_token": "interactive-token"})
    provider = DelegatedGraphTokenProvider(GraphAuthConfig("client", "tenant"), app=fake)
    assert provider() == "interactive-token"
    assert fake.interactive_calls == 1


def test_delegated_provider_does_not_accept_failed_authentication() -> None:
    fake = FakeMsal(None, {"error": "access_denied", "error_description": "Consent denied"})
    provider = DelegatedGraphTokenProvider(GraphAuthConfig("client", "tenant"), app=fake)
    with pytest.raises(RuntimeError, match="access_denied"):
        provider()
