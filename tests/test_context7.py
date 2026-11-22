"""Tests for the Context7 MCP server preset."""
from unittest.mock import Mock, patch

import httpx

from mcp_arena.presents.context7 import Context7MCPServer


def _tool(server, name):
    return server.mcp_server._tool_manager._tools[name].fn


def _response(payload, status_code=200, text=""):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = payload
    response.text = text
    response.raise_for_status.return_value = None
    return response


def test_context7_registers_its_three_tools():
    server = Context7MCPServer(api_key="ctx7sk-test")
    assert set(server.mcp_server._tool_manager._tools) == {
        "resolve_library_id",
        "query_docs",
        "search_docs",
    }
    assert server.name == "Context7 MCP Server"


def test_api_key_from_env_adds_auth_header(monkeypatch):
    monkeypatch.setenv("CONTEXT7_API_KEY", "ctx7sk-from-env")
    server = Context7MCPServer()
    assert server.api_key == "ctx7sk-from-env"
    assert server._headers()["Authorization"] == "Bearer ctx7sk-from-env"


def test_api_key_is_optional():
    server = Context7MCPServer()
    assert "Authorization" not in server._headers()


def test_resolve_library_id_uses_search_endpoint_and_formats_results():
    server = Context7MCPServer(api_key="ctx7sk-test", timeout=12.5)
    payload = {"results": [{
        "id": "/vercel/next.js",
        "title": "Next.js",
        "description": "The React framework for the web.",
        "trustScore": 9.5,
    }]}
    response = _response(payload)

    with patch("mcp_arena.presents.context7.httpx.get", return_value=response) as request:
        out = _tool(server, "resolve_library_id")("next.js", query="app router")

    request.assert_called_once_with(
        "https://context7.com/api/v2/libs/search",
        headers=server._headers(),
        params={"libraryName": "next.js", "query": "app router"},
        timeout=12.5,
    )
    assert "/vercel/next.js" in out
    assert "Next.js" in out
    assert "trust score 9.5" in out


def test_query_docs_with_known_id_skips_resolution():
    server = Context7MCPServer(api_key="ctx7sk-test")
    response = _response({
        "codeSnippets": [{
            "codeTitle": "Fetching data",
            "libraryId": "/vercel/next.js",
            "codeList": [{"code": "const r = await fetch('/api');"}],
        }],
        "infoSnippets": [{"content": "Use async/await in Server Components."}],
    })

    with patch("mcp_arena.presents.context7.httpx.get", return_value=response) as request:
        out = _tool(server, "query_docs")(
            "/vercel/next.js", "how to fetch data", language="TypeScript"
        )

    request.assert_called_once_with(
        "https://context7.com/api/v2/context",
        headers=server._headers(),
        params={
            "libraryId": "/vercel/next.js",
            "query": "how to fetch data",
            "type": "json",
            "language": "TypeScript",
        },
        timeout=30.0,
    )
    assert "Fetching data" in out
    assert "const r = await fetch" in out
    assert "async/await" in out


def test_query_docs_resolves_plain_library_name_first():
    server = Context7MCPServer()
    lookup = _response({"results": [{"id": "/facebook/react"}]})
    docs = _response({"infoSnippets": [{"content": "useState basics"}]})

    with patch(
        "mcp_arena.presents.context7.httpx.get", side_effect=[lookup, docs]
    ) as request:
        out = _tool(server, "query_docs")("react", "how to use useState")

    assert request.call_count == 2
    assert request.call_args_list[0].args[0].endswith("/v2/libs/search")
    assert request.call_args_list[1].args[0].endswith("/v2/context")
    assert request.call_args_list[1].kwargs["params"]["libraryId"] == "/facebook/react"
    assert "useState basics" in out


def test_search_docs_passes_library_hints_and_language():
    server = Context7MCPServer()
    response = _response({"codeSnippets": [{
        "codeTitle": "Example",
        "libraryId": "/facebook/react",
        "codeList": [{"code": "useState(0)"}],
    }]})

    with patch("mcp_arena.presents.context7.httpx.get", return_value=response) as request:
        out = _tool(server, "search_docs")(
            "how to manage state",
            libraries=["react", "next.js", "zustand", "redux", "mobx"],
            language="TypeScript",
        )

    params = request.call_args.kwargs["params"]
    assert request.call_args.args[0].endswith("/v3/search")
    assert params["library"] == ["react", "next.js", "zustand", "redux"]
    assert params["language"] == "TypeScript"
    assert "[/facebook/react]" in out


def test_no_documentation_found_is_treated_as_empty_result():
    server = Context7MCPServer()
    response = _response({"error": "no_documentation_found"}, status_code=404)

    with patch("mcp_arena.presents.context7.httpx.get", return_value=response):
        out = _tool(server, "search_docs")("something obscure")

    assert "No Context7 documentation found" in out
    assert "error" not in out.lower()


def test_http_errors_are_reported_not_raised():
    server = Context7MCPServer()
    response = _response({"error": "unauthorized"}, status_code=401, text="bad key")
    response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "bad key", request=Mock(), response=response
    )

    with patch("mcp_arena.presents.context7.httpx.get", return_value=response):
        out = _tool(server, "resolve_library_id")("react")

    assert "Context7 API returned 401" in out
