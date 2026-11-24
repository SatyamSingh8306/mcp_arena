# Tutorial: building a personal-assistant agent

Build an agent that reads your local filesystem, searches GitHub, and chats through a simple UI, using `mcp_arena` and `langchain-mcp-adapters`.

## 1. Install

```bash
pip install "mcp-arena[local_operation,agents]" langchain-openai
```

## 2. Start an MCP server

```python
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

server = LocalOperationsMCPServer(
    host="127.0.0.1",
    port=9000,
    transport="streamable-http",
)
server.run()
```

Save as `server.py` and run `python server.py`. It listens on `http://127.0.0.1:9000/mcp`.

## 3. Build the agent

```python
import asyncio

from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [LocalOperationsMCPServer(host="127.0.0.1", port=9000, transport="streamable-http")],
        system_prompt=(
            "You can read, write, and search the user's local filesystem. "
            "Always confirm destructive actions."
        ),
        name="jarvis",
    )
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Summarise the README.md in my current directory.",
        }]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

`make_mcp_agent` handles the connection, tool discovery, and agent construction.

## 4. Add another server

```python
import os

from mcp_arena.presents.github import GithubMCPServer

agent = await make_mcp_agent(
    llm,
    [
        LocalOperationsMCPServer(transport="streamable-http", port=9000),
        GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
    ],
    system_prompt="You can read local files and search GitHub.",
)
```

## 5. Filter the tools

Narrow the tool set so the model is not overwhelmed:

```python
from mcp_arena.agent import ToolRegistry

registry = ToolRegistry().register_server(local_server)
print(registry.names())
registry.drop("delete_directory", "format_disk")

agent = await make_mcp_agent(llm, [local_server], names=registry.names())
```

## 6. Add persistence

Pass a LangGraph checkpointer for conversational memory across turns:

```python
from langgraph.checkpoint.memory import InMemorySaver

agent = await make_mcp_agent(
    llm,
    [local_server],
    checkpointer=InMemorySaver(),
    interrupt_before=["tools"],
)
```

See the [LangGraph persistence documentation](https://langchain-ai.github.io/langgraph/concepts/persistence/) for other checkpointers.

## 7. Add a chat UI (optional)

```python
import asyncio

import gradio as gr

def chat(message, history):
    messages = history + [{"role": "user", "content": message}]
    result = asyncio.run(agent.ainvoke({"messages": messages}))
    return result["messages"][-1].content

gr.ChatInterface(chat).launch()
```

## Next steps

- [Agent Guide](AGENT_GUIDE.md) — full `make_mcp_agent` reference and `ToolRegistry`
- [LangChain Integration](LANGCHAIN_INTEGRATION.md) — multiple servers, transports, sync wrapper
- [MCP Servers Guide](MCP_SERVERS_GUIDE.md) — every preset in one place
- [Installation](INSTALLATION.md) — extras reference
