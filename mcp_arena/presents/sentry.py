"""Sentry MCP server for read-only error investigation."""
from typing import Any, Dict, Literal, Optional
import os

import httpx

from mcp_arena.mcp.server import BaseMCPServer


class SentryMCPServer(BaseMCPServer):
    """MCP server for inspecting Sentry projects, issues, and events."""

    _REQUIRED_EXTRAS = {"httpx": "sentry"}

    def __init__(
        self,
        auth_token: Optional[str] = None,
        organization: Optional[str] = None,
        base_url: str = "https://sentry.io/api/0",
        timeout: float = 30.0,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.auth_token = auth_token or os.getenv("SENTRY_AUTH_TOKEN")
        self.organization = organization or os.getenv("SENTRY_ORG")
        if not self.auth_token:
            raise ValueError(
                "Sentry auth token is required. Provide auth_token or set SENTRY_AUTH_TOKEN."
            )
        if not self.organization:
            raise ValueError(
                "Sentry organization is required. Provide organization or set SENTRY_ORG."
            )
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        super().__init__(
            name="Sentry MCP Server",
            description="Read-only Sentry error investigation for projects, issues, and events.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            response = httpx.get(
                f"{self.base_url}/{path.lstrip('/')}",
                headers={"Authorization": f"Bearer {self.auth_token}"},
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            return {"error": f"Sentry API returned {exc.response.status_code}: {exc.response.text}"}
        except (httpx.HTTPError, ValueError) as exc:
            return {"error": f"Sentry request failed: {exc}"}

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def list_projects() -> Any:
            """List projects in the configured Sentry organization."""
            return self._request(f"organizations/{self.organization}/projects/")

        @self.mcp_server.tool()
        def search_issues(
            query: str = "is:unresolved",
            limit: int = 25,
            project: Optional[str] = None,
        ) -> Any:
            """Search organization issues, optionally scoped to a project."""
            limit = max(1, min(limit, 100))
            params: Dict[str, Any] = {"query": query, "limit": limit}
            if project:
                params["project"] = project
            return self._request(f"organizations/{self.organization}/issues/", params)

        @self.mcp_server.tool()
        def get_issue(issue_id: str) -> Any:
            """Get details for a Sentry issue."""
            return self._request(f"organizations/{self.organization}/issues/{issue_id}/")

        @self.mcp_server.tool()
        def list_issue_events(issue_id: str, stats_period: str = "24h") -> Any:
            """List recent events for a Sentry issue."""
            return self._request(
                f"organizations/{self.organization}/issues/{issue_id}/events/",
                {"statsPeriod": stats_period},
            )
