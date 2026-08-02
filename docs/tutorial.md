# Tutorial — building a "Jarvis" personal-assistant agent

Build an agent that can read your local filesystem, run shell commands, and answer general questions — using `mcp_arena` and `langchain-mcp-adapters`.

## 0. Install

```bash
pip install "mcp-arena[local_operation,agents]" langchain-openai
```

## 1. Pick the MCP server

```python
# server.py — start this in one terminal
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

server = LocalOperationsMCPServer(
    host="127.0.0.1",
    port=9000,
    transport="streamable-http",     # or "sse" / "stdio"
)
server.run()
```

Run it: `python server.py`. It'll listen on `http://127.0.0.1:9000/mcp` (or `/sse`).

## 2. Build the agent

```python
# client.py — the LangChain agent
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [LocalOperationsMCPServer(host="127.0.0.1", port=9000, transport="streamable-http")],
        system_prompt=(
            "You can read, write, and search the user's local filesystem. "
            "Always confirm destructive actions."
        ),
        name="jarvis",
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user",
        "content": "Summarise the README.md in my current directory.",
    }]})
    print(out["messages"][-1].content)

asyncio.run(main())
```

That's it — `make_mcp_agent` does the connection, tool discovery, and agent construction.

## 3. Multi-server

Add GitHub so the agent can also look things up:

```python
from mcp_arena.presents.github import GithubMCPServer
import os

agent = await make_mcp_agent(
    llm,
    [
        LocalOperationsMCPServer(transport="streamable-http", port=9000),
        GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
    ],
    system_prompt="You can read local files and search GitHub.",
)
```

## 4. Filter the tools

Most agents get bogged down with too many tools. Narrow them with `ToolRegistry`:

```python
from mcp_arena.agent import ToolRegistry, make_mcp_agent

reg = ToolRegistry().register_server(local_server)
print("Available:", reg.names())
reg.drop("delete_directory", "format_disk")  # safety first

agent = await make_mcp_agent(llm, [local_server], names=reg.names())
```

## 5. Persistence (memory)

For conversational memory across turns, pass a `checkpointer`:

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = await make_mcp_agent(
    llm,
    [local_server],
    checkpointer=InMemorySaver(),   # or PostgresSaver, etc.
    interrupt_before=["tools"],     # ask before every tool call (HITL)
)
```

See [the langgraph docs](https://langchain-ai.github.io/langgraph/concepts/persistence/) for more checkpointers.

## 6. Wrap with Gradio (optional)

```python
import gradio as gr
import asyncio

def chat(message, history):
    return asyncio.run(agent.ainvoke({
        "messages": history + [{"role": "user", "content": message}]
    }))["messages"][-1].content

gr.ChatInterface(chat).launch()
```

Done. The full Jarvis — local-fs + github + chat UI — in ~20 lines.

## Where to next

- [`AGENT_GUIDE.md`](AGENT_GUIDE.md) — full `make_mcp_agent` reference and `ToolRegistry`
- [`LANGCHAIN_INTEGRATION.md`](LANGCHAIN_INTEGRATION.md) — multi-server, transport choices, sync wrapper
- [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md) — every preset in one place
- [`INSTALLATION.md`](INSTALLATION.md) — extras reference
