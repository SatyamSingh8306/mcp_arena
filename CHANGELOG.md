# Changelog

All notable changes to `mcp_arena` are documented here. Versions follow [SemVer](https://semver.org/). This project is pre-1.0, so breaking changes may land in minor versions.

## [0.5.0] - 2026-11-22

Headline: two new MCP server presets, `SentryMCPServer` and `Context7MCPServer`. This is an additive, backwards-compatible minor update. Both presets are discoverable through the CLI and lazy loader, and no existing preset changes behavior.

### Added

#### `SentryMCPServer` (`mcp_arena.presents.sentry`)

Read-only investigation of production errors in Sentry. A read-only tool set is safe to hand to an LLM: it gives the agent stack traces, affected releases, breadcrumbs, and issue context without write access to production.

Tools registered:

- `list_projects` — list projects in the configured organization.
- `search_issues` — search issues with a Sentry query (`is:unresolved` by default), with optional project scope and a result limit clamped to 1-100.
- `get_issue` — details for one issue ID.
- `list_issue_events` — recent events for an issue over a configurable `statsPeriod` (default `24h`).

Auth uses `auth_token` / `SENTRY_AUTH_TOKEN` and `organization` / `SENTRY_ORG`; both are required and missing values produce clear errors. The preset uses `httpx` and the `mcp-arena[sentry]` extra, supports all standard transports, and accepts `base_url` for self-hosted Sentry.

#### `Context7MCPServer` (`mcp_arena.presents.context7`)

Live, version-specific library documentation for LLMs. Context7 addresses stale training data and hallucinated APIs by fetching current docs and code examples at inference time.

Tools registered:

- `resolve_library_id` — map a library name to a Context7 ID such as `/vercel/next.js` (`GET /api/v2/libs/search`).
- `query_docs` — retrieve docs or code for a known ID, or auto-resolve a plain name, with optional language and version-pinned IDs (`GET /api/v2/context`).
- `search_docs` — one-shot search where Context7 picks the libraries, with up to four hints (`GET /api/v3/search`).

Auth uses `api_key` / `CONTEXT7_API_KEY` and is optional; public rate limits apply without a key. The preset uses `httpx` and the `mcp-arena[context7]` extra. It handles `404 no_documentation_found` as an empty result and bounds output with `max_snippets`.

#### Tests and packaging

- `tests/test_sentry.py` verifies the configured token, organization, and bound limits.
- `tests/test_context7.py` covers tool registration, auth handling, endpoint and parameter wiring, name resolution, hint bounding, and error handling.
- `sentry` and `context7` are included in the import and `_REQUIRED_EXTRAS` test suites, and both extras are part of `mcp-arena[all]`.

### Changed

- Version set to `0.5.0` in `pyproject.toml`, `mcp_arena.__version__`, and the CLI `about` output; the CLI feature count now reads "30+ presets".
- `context7` added to the keywords in `pyproject.toml`.

## [0.4.1] - 2026-08-01

### Removed

- `mcp_arena.agent.react_agent.ReactAgent`
- `mcp_arena.agent.reflection_agent.ReflectionAgent`
- `mcp_arena.agent.planning_agent.PlanningAgent`
- `mcp_arena.agent.factory.AgentFactory` / `AgentBuilder` / `AgentRegistry`
- `mcp_arena.agent.router` (`AgentRouter`, `MultiAgentOrchestrator`, and related classes)
- `mcp_arena.agent.policies`
- `mcp_arena.agent.memory`, `state`, `interfaces`, and `base`
- `mcp_arena.tools.{calculator,filesystem,web,search,time_tool,data_analysis}`
- `mcp_arena.wrapper.langchain_integration` and `langchain_wrapper`
- `mcp_arena.mcp.registry`
- `examples/agent_examples.py` and the legacy agent tests

### Added

- `mcp_arena.agent.make_mcp_agent(llm, servers, *, system_prompt=None, names=None, server_names=None, extra_tools=None, **create_agent_kwargs)` — async; returns whatever `langchain.agents.create_agent` returns.
- `mcp_arena.agent.make_mcp_agent_sync(...)` — synchronous wrapper.
- `mcp_arena.agent.ToolRegistry` — discover, filter, rename, and drop tools from any number of MCP servers. Methods: `register_server`, `register`, `keep`, `drop`, `rename`, `from_source`, `names`, `list`, `to_openai`, `get_callables`.
- `mcp_arena.agent.BaseTool` — base class for user-defined, non-MCP tools.
- `mcp_arena.presents.__init__` — AST-driven lazy loader that exports every `*Server` class found in `mcp_arena/presents/*.py`.

### Changed

- The core install now ships three MCP server presets: `LocalOperationsMCPServer`, `GenericAPIMCPServer`, and `SMTPServer`. `pip install mcp-arena` is enough to run a working server.
- Every preset declares `_REQUIRED_EXTRAS`. Constructing a preset without its dependency now raises an `ImportError` with the exact `pip install "mcp-arena[<extra>]"` command.
- `mcp-arena[agents]` installs `langchain>=1.0,<2.0` and `langchain-mcp-adapters>=0.1,<1.0`. LLM providers are no longer installed automatically.
- `[local_operation]` and `[generic_api]` remain as no-op extras for backwards compatibility.
- The CLI entry points `mcp_arena` and `mcp-arena` are unchanged.
- `_config_for` in the agent builder uses `streamable_http` for HTTP and `sse` for SSE when configuring the MCP adapter.
- Documentation was rewritten around the minimal `make_mcp_agent` flow.

### Migration guide (0.3.x to 0.4.0)

| 0.3.x | 0.4.0 |
| --- | --- |
| `from mcp_arena.agent.react_agent import ReactAgent` | `from mcp_arena.agent import make_mcp_agent` |
| `agent = ReactAgent(llm=llm, max_steps=10)` | `agent = await make_mcp_agent(llm, [s1, s2], system_prompt="...")` |
| `MCPLangChainWrapper` / `MCPLangChainIntegration` | `make_mcp_agent` with server objects directly |
| `CalculatorTool()`, `FileSystemTool()`, ... | Subclass `BaseTool` or use MCP-server tools |
| `tool_registry.register_tool(...)` | `tool_registry.register(BaseTool(...))` |

`agent.process("...")` is replaced by `await agent.ainvoke({"messages": [{"role": "user", "content": "..."}]})`.

## [0.3.1] and earlier

See git history.
