from unittest.mock import Mock, patch

from mcp_arena.presents.sentry import SentryMCPServer


def test_sentry_tools_use_configured_api_and_bound_limits():
    server = SentryMCPServer(auth_token="token", organization="acme")
    response = Mock()
    response.json.return_value = []
    response.raise_for_status.return_value = None

    with patch("mcp_arena.presents.sentry.httpx.get", return_value=response) as request:
        server.mcp_server._tool_manager._tools["search_issues"].fn(
            "errors", limit=999, project="web"
        )

    request.assert_called_once_with(
        "https://sentry.io/api/0/organizations/acme/issues/",
        headers={"Authorization": "Bearer token"},
        params={"query": "errors", "limit": 100, "project": "web"},
        timeout=30.0,
    )
