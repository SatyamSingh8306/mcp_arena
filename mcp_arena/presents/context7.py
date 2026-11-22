"""Context7 MCP server — current, version-specific library docs for LLMs.

Context7 solves the "my training data is stale" problem: instead of guessing
an API, an agent resolves a library to a Context7 ID and pulls live docs and
code examples. It is one of the most widely adopted MCP servers in 2026 and
is the missing piece in mcp_arena's preset lineup.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Literal, Optional

import httpx

from mcp_arena.mcp.server import BaseMCPServer


class Context7MCPServer(BaseMCPServer):
    """Expose Context7's live documentation lookup as MCP tools.

    Three tools are registered:

    * ``resolve_library_id`` — turn a library name into a Context7 ID
      (e.g. ``/vercel/next.js``). Call this first if you only know the name.
    * ``query_docs`` — fetch current docs / code for a known ID. A plain
      library name also works; it is resolved automatically.
    * ``search_docs`` — one shot: Context7 picks the relevant libraries and
      returns the best matching snippets.

    An API key is optional. Without ``CONTEXT7_API_KEY`` the public rate
    limits apply; with one, higher plan-based limits are used.
    """

    _REQUIRED_EXTRAS = {"httpx": "context7"}

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://context7.com/api",
        timeout: float = 30.0,
        max_snippets: int = 8,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.api_key = api_key or os.getenv("CONTEXT7_API_KEY")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_snippets = max(1, min(max_snippets, 50))
        super().__init__(
            name="Context7 MCP Server",
            description=(
                "Up-to-date, version-specific library documentation and code "
                "examples from Context7."
            ),
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    # ------------------------------------------------------------------ #
    # HTTP plumbing
    # ------------------------------------------------------------------ #
    def _headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET a Context7 endpoint, returning a JSON dict (never raising)."""
        try:
            response = httpx.get(
                f"{self.base_url}/{path.lstrip('/')}",
                headers=self._headers(),
                params=params,
                timeout=self.timeout,
            )
            if response.status_code == 404:
                # v3/search reports "no documentation found" as a 404 — treat
                # it as an empty result rather than an error.
                try:
                    body = response.json()
                except ValueError:
                    body = {}
                if isinstance(body, dict) and body.get("error") == "no_documentation_found":
                    return {"results": [], "codeSnippets": [], "infoSnippets": []}
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"raw": payload}
        except httpx.HTTPStatusError as exc:
            return {"error": f"Context7 API returned {exc.response.status_code}: {exc.response.text}"}
        except (httpx.HTTPError, ValueError) as exc:
            return {"error": f"Context7 request failed: {exc}"}

    # ------------------------------------------------------------------ #
    # Response formatting
    # ------------------------------------------------------------------ #
    @staticmethod
    def _first_library_id(payload: Dict[str, Any]) -> Optional[str]:
        results = payload.get("results") or []
        for item in results:
            if isinstance(item, dict) and item.get("id"):
                return str(item["id"])
        return None

    def _format_libraries(self, payload: Dict[str, Any], name: str) -> str:
        if payload.get("error"):
            return f"Context7 error: {payload['error']}"
        results = payload.get("results") or []
        if not results:
            return f"No Context7 libraries found for '{name}'. Try a different name."
        noun = "library" if len(results) == 1 else "libraries"
        lines = [f"Found {len(results)} Context7 {noun} for '{name}':"]
        for index, lib in enumerate(results[:10], 1):
            lib_id = lib.get("id", "") if isinstance(lib, dict) else ""
            title = lib.get("title", "") if isinstance(lib, dict) else ""
            description = (lib.get("description") or "") if isinstance(lib, dict) else ""
            description = " ".join(str(description).split())
            if len(description) > 240:
                description = description[:237] + "..."
            meta = []
            if title:
                meta.append(str(title))
            score = lib.get("trustScore") if isinstance(lib, dict) else None
            if score is not None:
                meta.append(f"trust score {score}")
            suffix = f" ({', '.join(meta)})" if meta else ""
            lines.append(f"{index}. {lib_id}{suffix}: {description}")
        lines.append("")
        lines.append("Pass one of these IDs to query_docs for documentation.")
        return "\n".join(lines)

    def _format_snippets(
        self,
        payload: Dict[str, Any],
        label: str,
        query: str,
        multi_library: bool = False,
    ) -> str:
        if payload.get("error"):
            return f"Context7 error: {payload['error']}"
        code_snippets = payload.get("codeSnippets") or []
        info_snippets = payload.get("infoSnippets") or []
        if not code_snippets and not info_snippets:
            return (
                f"No Context7 documentation found for '{query}' ({label}). "
                "Try a more specific question or a different library."
            )

        lines = [f"# Context7 docs for '{query}' — {label}", ""]
        shown = 0
        for snippet in code_snippets[: self.max_snippets]:
            if not isinstance(snippet, dict):
                continue
            heading = str(snippet.get("codeTitle") or "Code example")
            lib_id = snippet.get("libraryId", "")
            if multi_library and lib_id:
                heading += f"  [{lib_id}]"
            lines.append(f"## {heading}")
            source = snippet.get("source") or snippet.get("sourceUrl")
            if source:
                lines.append(f"Source: {source}")
            for item in snippet.get("codeList") or []:
                piece = item.get("code", "") if isinstance(item, dict) else str(item)
                if piece:
                    lines.extend(["```", str(piece).strip(), "```", ""])
            shown += 1

        for snippet in info_snippets[: self.max_snippets]:
            if not isinstance(snippet, dict):
                continue
            heading = "Documentation notes"
            lib_id = snippet.get("libraryId", "")
            if multi_library and lib_id:
                heading += f"  [{lib_id}]"
            lines.append(f"## {heading}")
            content = snippet.get("content") or ""
            if content:
                lines.extend([str(content).strip(), ""])
            shown += 1

        if shown >= self.max_snippets:
            lines.append(f"(showing first {self.max_snippets} snippets)")
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------ #
    # Tools
    # ------------------------------------------------------------------ #
    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def resolve_library_id(library_name: str, query: str = "") -> str:
            """Resolve a library name to a Context7 ID like /vercel/next.js.

            Call this before query_docs when you only know the library's name.
            """
            params: Dict[str, Any] = {"libraryName": library_name}
            if query:
                params["query"] = query
            return self._format_libraries(
                self._request("v2/libs/search", params), library_name
            )

        @self.mcp_server.tool()
        def query_docs(library_id: str, query: str, language: str = "") -> str:
            """Get current, version-specific docs for a Context7 library.

            ``library_id`` looks like /facebook/react or
            /vercel/next.js/v16.2.9. A plain name (e.g. "react") is resolved
            automatically. Use a specific question for better results.
            """
            resolved = library_id.strip()
            if not resolved.startswith("/"):
                lookup = self._request(
                    "v2/libs/search", {"libraryName": resolved, "query": query}
                )
                match = self._first_library_id(lookup)
                if not match:
                    return self._format_libraries(lookup, resolved)
                resolved = match

            params: Dict[str, Any] = {
                "libraryId": resolved,
                "query": query,
                "type": "json",
            }
            if language:
                params["language"] = language
            return self._format_snippets(
                self._request("v2/context", params), resolved, query
            )

        @self.mcp_server.tool()
        def search_docs(
            query: str,
            libraries: Optional[List[str]] = None,
            language: str = "",
        ) -> str:
            """One-shot docs search: Context7 selects libraries and returns snippets.

            Use this when you are unsure which library (or libraries) hold the
            answer. Up to four library hints / IDs may be supplied.
            """
            params: Dict[str, Any] = {"query": query, "type": "json"}
            if libraries:
                params["library"] = list(libraries[:4])
            if language:
                params["language"] = language
            return self._format_snippets(
                self._request("v3/search", params), "auto-selected libraries",
                query, multi_library=True,
            )
