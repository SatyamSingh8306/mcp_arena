# LangChain Integration Guide

`mcp_arena` ships MCP servers, and a thin agent wrapper that wires those servers into a [LangChain v1](https://reference.langchain.com/python/langchain/agents/factory/create_agent) agent. The function is `mcp_arena.agent.make_mcp_agent`.

> **Removed in 0.4.0:** `MCPLangChainIntegration` and `MCPLangChainWrapper` — both superseded by `make_mcp_agent`. See `CHANGELOG.md` for details.

## Install

```bash
pip install mcp-arena[agents]                # core agents
pip install mcp-arena[agents,openai]         # adds nothing yet — provider pkgs below
pip install langchain-openai                 # or langchain-anthropic, langchain-groq, …
```

`mcp-arena[agents]` pulls in `langchain>=1.0,<2.0` and `langchain-mcp-adapters>=0.1,<1.0`. Install the LLM provider of your choice next to it.

## Minimal example

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [GithubMCPServer(token="ghp_…")] if False else [],
        # ^ nothing — leave empty to fail-fast with a clear message.
        # For a real run:
        # [GithubMCPServer(token="ghp_…")],
        system_prompt="You can search GitHub.",
    )

asyncio.run(main())
```

A runnable real-world version:

```python
import asyncio, os
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.slack import SlackMCPServer

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [
            GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
            SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"]),
        ],
        system_prompt=(
            "You can search GitHub repos and post to Slack. "
            "Always cite the repo name and owner before summarising."
        ),
        name="devops_bot",
    )

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Find the top-3 starred repos in my org and drop the links in #general.",
        }]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

## What it does under the hood

```
make_mcp_agent(llm, servers, …)
    │
    ├── For each server, derive an MCP-adapter connection entry:
    │       stdio  → spawn "python -m mcp_arena.presents.<module>"
    │       sse    → http://<host>:<port>/sse
    │       http   → http://<host>:<port>/mcp  (streamable_http)
    │
    ├── MultiServerMCPClient(connections).get_tools()
    │
    ├── Apply filters / extras if you passed them
    │
    └── langchain.agents.create_agent(llm, tools, system_prompt=…, **kwargs)
            └── returns a compiled LangGraph runnable
```

You don't manage subprocesses, sessions, or cleanup — stdio servers self-terminate when the client closes.

## Filters: keep only the tools you want

```python
from mcp_arena.agent import make_mcp_agent, ToolRegistry

reg = ToolRegistry().register_server(slack_server)
print("Available:", reg.names())             # ['chat_postMessage', 'list_channels', ...]
reg.keep("chat_postMessage", "list_channels") # narrow to two

agent = await make_mcp_agent(
    llm,
    [slack_server],
    names=reg.names(),
)
```

See [`AGENT_GUIDE.md`](AGENT_GUIDE.md) for the full registry API: `register`, `keep`, `drop`, `rename`, `from_source`, `to_openai`, `get_callables`.

## Mixing MCP and non-MCP tools

```python
from mcp_arena.agent import BaseTool, make_mcp_agent

class UpperTool(BaseTool):
    def __init__(self):
        super().__init__(name="uppercase", description="Capitalise a string")
    def execute(self, s: str) -> str:
        return s.upper()

agent = await make_mcp_agent(
    llm,
    [slack_server],
    extra_tools=[UpperTool()],
)
```

## Forwarded `create_agent` parameters

Everything `langchain.agents.create_agent` accepts is forwarded verbatim via `**create_agent_kwargs`. Reference: [create_agent (v1)](https://reference.langchain.com/python/langchain/agents/factory/create_agent).

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = await make_mcp_agent(
    llm,
    [github_server, slack_server],
    system_prompt="Always confirm before posting.",
    checkpointer=InMemorySaver(),     # persistence
    interrupt_before=["tools"],        # human-in-the-loop
    name="devops_bot",
    debug=True,
)
```

See `AGENT_GUIDE.md §3` for the full list — `middleware`, `response_format`, `state_schema`, `context_schema`, `store`, `interrupt_after`, `cache`, `transformers`, …

## Multi-server

Just pass a list. Each server becomes its own connection; tool names can collide, so disambiguate if needed:

```python
agent = await make_mcp_agent(
    llm,
    [server_a, server_b],  # same transport / different ports
    server_names={id(server_a): "alpha", id(server_b): "beta"},
)
```

## Transport choices

| `BaseMCPServer.transport` | What happens                                                                  |
| ------------------------- | ----------------------------------------------------------------------------- |
| `stdio`                   | Builder spawns `python -m mcp_arena.presents.<module>` and talks over stdin.  |
| `sse`                     | Builder connects to `http://<host>:<port>/sse`.                                |
| `http` / `streamable-http`| Builder connects to `http://<host>:<port>/mcp` (transport `streamable_http`). |

Switch on the server side:

```python
AudioMCPServer(transport="sse", host="0.0.0.0", port=8001)
```

## Sync wrapper

`make_mcp_agent` is async (the MCP adapter only exposes an async `get_tools()`). If you can't `await`, use `make_mcp_agent_sync`:

```python
from mcp_arena.agent import make_mcp_agent_sync

agent = make_mcp_agent_sync(
    llm,
    [server],
    system_prompt="...",
)
```

Calls `asyncio.run` internally — don't use it from inside a running event loop.

## Troubleshooting

| Symptom                                           | Likely cause                                                  |
| ------------------------------------------------- | ------------------------------------------------------------- |
| `ValueError: make_mcp_agent requires at least one MCP server` | Forgot the `servers` argument.                          |
| `ImportError: langchain_mcp_adapters`             | `pip install "mcp-arena[agents]"`.                            |
| Server fails to start in stdio mode               | Credentials missing — most presets read from env vars.         |
| Subprocess keeps spawning but the agent times out | Server constructor needs credentials up-front; pass them in.   |
| `RuntimeError("asyncio.run() cannot be called…")` | You called `make_mcp_agent_sync(...)` from inside a loop. `await make_mcp_agent(...)` instead. |

## Migrating from 0.3.x

```python
# before (0.3.x)
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper
wrapper = MCPLangChainWrapper(servers={"github": github_server}, auto_start=True)
await wrapper.connect()
agent = wrapper.create_agent(llm=llm, system_prompt="...")
response = await wrapper.invoke_agent(agent, "...")

# after (0.4.0)
from mcp_arena.agent import make_mcp_agent
agent = await make_mcp_agent(
    llm,
    [github_server],
    system_prompt="...",
)
response = await agent.ainvoke({"messages": [{"role": "user", "content": "..."}]})
```

That's the whole migration.
