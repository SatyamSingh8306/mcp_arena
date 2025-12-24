# Quick Start Examples

## 1. Install GitHub MCP Server Only

```bash
pip install mcp_arena[github]
```

## 2. Basic GitHub MCP Server

```python
from mcp_arena.presents.github import GithubMCPServer
import os

# Create server with your GitHub token
token = os.getenv("GITHUB_TOKEN")
server = GithubMCPServer(token=token)

# Start the server
server.run(host="localhost", port=8000)
```

## 3. Install Slack MCP Server Only

```bash
pip install mcp_arena[slack]
```

```python
from mcp_arena.presents.slack import SlackMCPServer
import os

token = os.getenv("SLACK_BOT_TOKEN")
server = SlackMCPServer(token=token)
server.run()
```

## 4. Install Multiple Specific Servers

```bash
# Install both GitHub and Slack
pip install mcp_arena[github,slack]
```

## 5. Install All Available Servers

```bash
pip install mcp_arena[all]
```

## 6. Using with LangChain Agent

```python
from mcp_arena.agent.langgraph_agent import LangGraphAgent
from mcp_arena.presents.github import GithubMCPServer
import os

# Create MCP server
github_server = GithubMCPServer(token=os.getenv("GITHUB_TOKEN"))

# Create agent that uses the MCP server
agent = LangGraphAgent(
    mcp_servers=[github_server],
    model="gpt-4",
)

# Ask the agent to do something
result = agent.run("What are my recent GitHub repositories?")
print(result)
```

## 7. Custom Tool Registration

```python
from mcp_arena.mcp.server import MCPServer
from mcp_arena.tools.base import BaseTool

class MyCustomTool(BaseTool):
    name = "my_custom_tool"
    description = "Does something awesome"
    
    def execute(self, input: str) -> str:
        return f"Processed: {input}"

# Create server
server = MCPServer("my-server")
server.register_tool(MyCustomTool())
server.run()
```

## 8. Configure Environment Variables

Create `.env` file:
```env
# For GitHub MCP
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# For Slack MCP
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx

# For Notion MCP
NOTION_API_KEY=secret_xxxxxxxxxxxx

# Server Configuration
MCP_SERVER_HOST=0.0.0.0
MCP_SERVER_PORT=8000
LOG_LEVEL=INFO
```

Then in your code:
```python
import os
from dotenv import load_dotenv

load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")
slack_token = os.getenv("SLACK_BOT_TOKEN")
```

## 9. Using Memory/RAG

```python
from mcp_arena.mcp.server import MCPServer
from mcp_arena.memory.faiss import FAISSMemory

server = MCPServer("my-server")

# Add FAISS memory for semantic search
memory = FAISSMemory()
server.set_memory(memory)

# Index some documents
memory.add_documents([
    {"content": "Python is great", "metadata": {"type": "note"}},
    {"content": "Rust is fast", "metadata": {"type": "note"}},
])

# Search documents
results = memory.search("fast languages")
```

## 10. Running as CLI

```bash
# Using the mcp_arena CLI
mcp_arena server --preset github --token $GITHUB_TOKEN

# Or start a custom server
mcp_arena run my_server.py
```

---

For more details, see:
- [INSTALLATION.md](INSTALLATION.md) - Full installation guide
- [README.md](README.md) - Core concepts and architecture
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guidelines
