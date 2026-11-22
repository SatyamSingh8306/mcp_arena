# Changelog

All notable changes to `mcp_arena` are documented here. Versions follow [SemVer](https://semver.org/). This project is pre-1.0; breaking changes may land in minor versions.

## [0.5.0] — 2026-11-22 (upcoming release)

**Headline: two new MCP server presets land in this release — `SentryMCPServer` and
`Context7MCPServer`.** This is an additive, backwards-compatible minor update: the
two more ready-to-run presets are discoverable via the CLI/lazy loader, and no existing preset changes behavior.

### Added

#### 1. `SentryMCPServer` (`mcp_arena.presents.sentry`)
Read-only investigation of production errors inside Sentry. Why it is in demand:
error monitoring is one of the most common things an agent needs to touch, and a
**read-only** tool set is safe to hand to an LLM — it gives the agent stack traces,
affected releases, breadcrumbs and issue context without any write access to
production. Sentry's own hosted MCP crossed ~417k package downloads in 30 days
(Sept 2026), which reflects how central "give the agent production context" has
become to modern debugging workflows. This preset brings that workflow into
`mcp_arena` with a plain API token instead of requiring the hosted OAuth service.

Tools registered:
- `list_projects` — list projects in the configured organization.
- `search_issues` — search issues with a Sentry query (`is:unresolved` by default), optional project scope, and a result limit clamped to 1–100.
- `get_issue` — details for one issue ID.
- `list_issue_events` — recent events for an issue over a configurable `statsPeriod` (default `24h`).

Auth: `auth_token` / `SENTRY_AUTH_TOKEN` plus `organization` / `SENTRY_ORG`
(both required, with clear errors if missing). Uses `httpx` and the `mcp-arena[sentry]`
extra; supports all standard transports and self-hosted Sentry via `base_url`.

#### 2. `Context7MCPServer` (`mcp_arena.presents.context7`)
Live, version-specific library documentation for LLMs. Why it is in demand:
Context7 is consistently ranked in the top three MCP servers in 2026 and is one
of the most widely adopted integrations in tools like Claude Code and Cursor. It
fixes the single biggest source of agent mistakes — stale training data and
hallucinated APIs — by fetching current docs and code examples at inference time.
It was the notable gap in `mcp_arena`'s preset lineup.

Tools registered:
- `resolve_library_id` — map a library name to a Context7 ID such as `/vercel/next.js` (`GET /api/v2/libs/search`).
- `query_docs` — retrieve docs/code for a known ID (or a plain name, auto-resolved), with optional language and version-pinned IDs (`GET /api/v2/context`).
- `search_docs` — one-shot search where Context7 picks the libraries, with up to four hints (`GET /api/v3/search`).

Auth: `api_key` / `CONTEXT7_API_KEY` is **optional** — without it the public rate
limits apply. Uses `httpx` and the `mcp-arena[context7]` extra. Handles
`404 no_documentation_found` as an empty result and bounds output with
`max_snippets` so large docs do not swamp the model's context.

#### Tests & packaging
- `tests/test_sentry.py` verifies the configured token, org, and bound limits.
- `tests/test_context7.py` (8 tests) covers tool registration, auth handling, endpoint/params wiring, name resolution, hint bounding, and error handling.
- Both `sentry` and `context7` are included in the import and `_REQUIRED_EXTRAS` parametrized suites; both extras are in `mcp-arena[all]`.

### Changed
- Version bumped to `0.5.0` across `pyproject.toml`, `mcp_arena.__version__`, and the CLI `about` output; the CLI feature count now reads "30+ presets".
- `context7` added to the keywords in `pyproject.toml`.

## [0.4.1] — 2026-08-01

### Removed
- `mcp_arena.agent.react_agent.ReactAgent`
- `mcp_arena.agent.reflection_agent.ReflectionAgent`
- `mcp_arena.agent.planning_agent.PlanningAgent`
- `mcp_arena.agent.factory.AgentFactory` / `AgentBuilder` / `AgentRegistry`
- `mcp_arena.agent.router` (`AgentRouter`, `MultiAgentOrchestrator`, etc.)
- `mcp_arena.agent.policies` (all policies)
- `mcp_arena.agent.memory`, `mcp_arena.agent.state`, `mcp_arena.agent.interfaces`, `mcp_arena.agent.base`
- `mcp_arena.tools.{calculator,filesystem,web,search,time_tool,data_analysis}` (legacy built-in "generic" tools; MCP servers cover these)
- `mcp_arena.wrapper.langchain_integration` (`MCPLangChainIntegration`)
- `mcp_arena.wrapper.langchain_wrapper` (`MCPLangChainWrapper`)
- `mcp_arena.mcp.registry` (`RegistryMCP`)
- `examples/agent_examples.py` (legacy `ReflectionAgent` / `CalculatorTool` examples)
- `tests/test_agents.py`, `tests/test_langchain_integration.py`

### Added
- `mcp_arena.agent.make_mcp_agent(llm, servers, *, system_prompt=None, names=None, server_names=None, extra_tools=None, **create_agent_kwargs)` — async; returns whatever `langchain.agents.create_agent` returns (a compiled LangGraph runnable).
- `mcp_arena.agent.make_mcp_agent_sync(...)` — sync wrapper around the above.
- `mcp_arena.agent.ToolRegistry` — discover / filter / rename / drop tools from any number of MCP servers, then hand them to an agent. Includes `register_server(server)`, `register(BaseTool)`, `keep(...)`, `drop(...)`, `rename(...)`, `from_source(...)`, `names()`, `list()`, `to_openai()`, `get_callables()`.
- `mcp_arena.agent.BaseTool` — keep only the subclass-this base for user-defined (non-MCP) tools; the canned `CalculatorTool`/`FileSystemTool`/etc. presets are gone.
- `mcp_arena.present.__init__` is now an AST-driven lazy loader — `*Server` classes are discovered from `mcp_arena/presents/*.py` at import time, so dropping in a new preset auto-exports it.

### Changed
- **Core install now ships three MCP server presets out of the box:** `LocalOperationsMCPServer` (file / system / process tools), `GenericAPIMCPServer` (any HTTP API call), and `SMTPServer` (outbound email via stdlib). No extra required — `pip install mcp-arena` lets you run a working MCP server.
- **Friendly missing-extra error:** every preset declares `_REQUIRED_EXTRAS = {"pkg_name": "extra_name", ...}`. Constructing a preset whose required dep isn't installed now raises an `ImportError` with the exact `pip install "mcp-arena[<extra>]"` command, instead of silently registering zero tools. Verified by `tests/test_required_extras.py`.
- **PyPI:** `mcp-arena[agents]` extra installs `langchain>=1.0,<2.0` and `langchain-mcp-adapters>=0.1,<1.0`. `langchain-groq` is no longer auto-installed — install the LLM provider you actually use.
- **Back-compat aliases:** `[local_operation]` and `[generic_api]` are now no-op extras so existing `pip install mcp-arena[local_operation]` / `[generic_api]` commands still work.
- **CLI:** `mcp_arena` and `mcp-arena` entry points unchanged.
- **Presets:** `_config_for` in the new builder uses `streamable_http` (the correct MCP adapter value) for HTTP and `sse` for SSE; the prior `streamable-http` (hyphen) variant is gone.
- **Tests:** 14 new tests in `tests/test_make_mcp_agent.py` covering `_config_for` (4 transports), `make_mcp_agent` (empty-server guard, build path, name filter, full kwargs-forwarding), and the `ToolRegistry` API. Old legacy-agent tests removed.
- **Docs:** `docs/AGENT_GUIDE.md`, `docs/LANGCHAIN_INTEGRATION.md`, `docs/QUICKSTART.md`, `docs/TOOLS_GUIDE.md`, `README.md` all rewritten to reflect the new minimal `make_mcp_agent` flow.

### Migration guide (0.3.x → 0.4.0)

| 0.3.x                                                          | 0.4.0                                                                                |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `from mcp_arena.agent.react_agent import ReactAgent`            | `from mcp_arena.agent import make_mcp_agent`                                         |
| `agent = ReactAgent(llm=llm, max_steps=10)`                    | `agent = await make_mcp_agent(llm, [s1, s2], system_prompt="...")`                   |
| `from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper` | `from mcp_arena.agent import make_mcp_agent` (delete `wrapper`, just pass servers)    |
| `CalculatorTool()`, `FileSystemTool()`, …                      | Subclass `BaseTool` (kept) — the canned presets are gone. Use MCP-server tools.      |
| `tool_registry.register_tool(...)` (builder)                   | `tool_registry.register(BaseTool(...))` (fluent, not builder)                         |

If you relied on `agent.process("...")`, the new equivalent is `await agent.ainvoke({"messages": [{"role": "user", "content": "..."}]})` (LangGraph v1).

## [0.3.1] — Earlier
See git history.
