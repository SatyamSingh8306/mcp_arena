"""Build a LangChain agent from MCP arena servers + an LLM.

`make_mcp_agent(llm, servers, system_prompt=...)` returns the same kind of
object `langchain.agents.create_agent` returns — a compiled LangGraph
that you call with `.invoke({"messages": [...]})` or `.ainvoke(...)`.

Each MCP server in `servers` becomes a connection in a
`MultiServerMCPClient`; the agent gets every tool the servers expose.

Every other parameter supported by `langchain.agents.create_agent` is
forwarded unchanged via `**create_agent_kwargs` — see
https://reference.langchain.com/python/langchain/agents/factory/create_agent

Usage:

    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import make_mcp_agent
    from mcp_arena.presents.audio import AudioMCPServer
    from mcp_arena.presents.image import ImageMCPServer

    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [AudioMCPServer(), ImageMCPServer()],
        system_prompt="You can edit audio and images.",
        # any create_agent kwarg:
        response_format=MyTypedDict,
        state_schema=CustomState,
        checkpointer=my_checkpointer,
        interrupt_before=["tools"],   # human-in-the-loop
    )
    result = await agent.ainvoke({"messages": [{"role": "user", "content": "trim the clip"}]})
"""
import inspect
import sys
from typing import Any, Dict, List, Optional, Sequence, Union

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from mcp_arena.mcp.server import BaseMCPServer


def _config_for(server: BaseMCPServer) -> Dict[str, Any]:
    """Translate a BaseMCPServer instance into a MultiServerMCPClient connection entry."""
    transport = server.transport
    if transport == "stdio":
        # Spawn the server as `python -m mcp_arena.presents.<module>` in a subprocess.
        # Works because every preset lives in mcp_arena.presents and accepts no required
        # args beyond the BaseMCPServer defaults.
        module_name = server.__class__.__module__.rsplit(".", 1)[-1]
        return {
            "transport": "stdio",
            "command": sys.executable,
            "args": ["-m", f"mcp_arena.presents.{module_name}"],
        }
    if transport in ("http", "streamable-http"):
        return {"transport": "streamable_http", "url": f"http://{server.host}:{server.port}/mcp"}
    if transport == "sse":
        return {"transport": "sse", "url": f"http://{server.host}:{server.port}/sse"}
    raise ValueError(f"Unsupported transport: {transport!r}")


async def make_mcp_agent(
    llm: Union[str, BaseChatModel],
    servers: Sequence[BaseMCPServer],
    *,
    system_prompt: Optional[str] = None,
    names: Optional[Sequence[str]] = None,
    server_names: Optional[Dict[str, str]] = None,
    extra_tools: Optional[Sequence[Any]] = None,
    **create_agent_kwargs,
) -> Runnable:
    """Build a LangChain agent whose tools come from the given MCP servers.

    Args:
        llm: Either a `BaseChatModel` instance or a model string (e.g. `"openai:gpt-4o"`).
        servers: One or more `BaseMCPServer` instances. Each becomes a connection
            in a `MultiServerMCPClient`; all tools they expose become agent tools.
        system_prompt: Optional instruction passed to `create_agent`.
        names: Optional filter — keep only these tool names across all servers.
        server_names: Optional `{server_object_id: "display_name"}` mapping; the
            default key is `server.name`. Used for the connection key in
            `MultiServerMCPClient`.
        extra_tools: Additional non-MCP tools to add to the agent.
        **create_agent_kwargs: Forwarded to `langchain.agents.create_agent`
            (e.g. `state_schema`, `checkpointer`, `response_format`).

    Returns:
        A compiled LangGraph runnable — same shape as
        `langchain.agents.create_agent` returns. Call `.invoke(...)` or `.ainvoke(...)`.
    """
    # Import lazily so the rest of mcp_arena stays importable without langchain installed.
    from langchain.agents import create_agent
    from langchain_mcp_adapters.client import MultiServerMCPClient

    if not servers:
        raise ValueError("make_mcp_agent requires at least one MCP server")

    connections = {
        (server_names or {}).get(id(server), server.name): _config_for(server)
        for server in servers
    }
    client = MultiServerMCPClient(connections)
    tools = await client.get_tools()

    if names is not None:
        keep = set(names)
        tools = [t for t in tools if t.name in keep]
    if extra_tools:
        tools = list(tools) + list(extra_tools)

    return create_agent(
        llm,
        tools,
        system_prompt=system_prompt,
        **create_agent_kwargs,
    )


# Anything create_agent accepts verbatim. Keep this in sync with langchain v1's
# factory signature — https://reference.langchain.com/python/langchain/agents/factory/create_agent
__all_create_agent_kwargs__ = (
    "middleware",
    "response_format",
    "state_schema",
    "context_schema",
    "checkpointer",
    "store",
    "interrupt_before",
    "interrupt_after",
    "debug",
    "name",
    "cache",
    "transformers",
)


def make_mcp_agent_sync(
    llm: Union[str, BaseChatModel],
    servers: Sequence[BaseMCPServer],
    *,
    system_prompt: Optional[str] = None,
    **kwargs,
) -> Runnable:
    """Sync wrapper around `make_mcp_agent` for callers who can't await."""
    coro = make_mcp_agent(llm, servers, system_prompt=system_prompt, **kwargs)
    # asyncio.run only works if no event loop is running in the current thread.
    try:
        asyncio_module = __import__("asyncio")
    except ImportError:
        raise RuntimeError("asyncio is required")
    return asyncio_module.run(coro)


# A type alias so docstrings / IDEs show the runtime contract.
Agent = Runnable