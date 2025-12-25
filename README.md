# mcp_arena

[![PyPI version](https://badge.fury.io/py/mcp-arena.svg)](https://badge.fury.io/py/mcp-arena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**mcp_arena** is a production-ready Python library for building **MCP (Model Context Protocol) servers** with intelligent agent orchestration and domain-specific presets.

## ✨ Features

- 🚀 **Ready-to-use MCP servers** for popular platforms (GitHub, Slack, Notion, AWS, etc.)
- 🤖 **Intelligent agents** with reflection, planning, and routing capabilities
- 🔧 **Zero-configuration setup** for common use cases
- 🏗️ **Extensible architecture** built on SOLID principles
- 📦 **Modular design** - use only what you need

## 🚀 Quick Start

### Installation

```bash
# Core library
pip install mcp-arena

# With specific presets
pip install mcp-arena[github,slack,notion]

# All presets
pip install mcp-arena[all]
```

### Basic Usage

```python
from mcp_arena.presents.github import GithubMCPServer

# Zero-config GitHub MCP server
mcp_server = GithubMCPServer(token="your_github_token")
mcp_server.run()
```

### Using Tools Directly

```python
from mcp_arena.tools.github import GithubTools
from mcp_arena.presents.github import GithubMCPServer

# Create GitHub MCP server first
mcp_server = GithubMCPServer(token="your_token")

# Create tools wrapper
tool = GithubTools(server=mcp_server)
tools = tool.get_list_of_tools()
```

### With Agent Orchestration

```python
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.agent.react import ReactAgent

# Create MCP server
mcp_server = GithubMCPServer(token="your_token")

# Create agent separately
agent = ReactAgent(name="github-agent")

# Run the server
mcp_server.run()
```

### LangChain Integration

#### Using MCP Arena Wrapper

```python
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper
from mcp_arena.presents.github import GithubMCPServer

# Create MCP server
github_server = GithubMCPServer(token="your_token")

# Wrap with LangChain
wrapper = MCPLangChainWrapper(
    servers={"github": github_server},
    auto_start=True
)

# Connect and create agent
await wrapper.connect()
agent = wrapper.create_agent(
    llm="gpt-4-turbo",
    system_prompt="You are a GitHub assistant"
)
```

#### Direct langchain_mcp_adapters Usage

```python
from langchain_mcp_adapters.client import MultiServerMCPClient  
from langchain.agents import create_agent
from mcp_arena.presents.github import GithubMCPServer

# Start GitHub MCP server in background
github_server = GithubMCPServer(token="your_token", transport="stdio")
github_server.run()

# Create client with multiple servers
client = MultiServerMCPClient(  
    {
        "github": {
            "transport": "stdio",
            "command": "python",
            "args": ["/path/to/github_server_script.py"],
        },
        "math": {
            "transport": "http",
            "url": "http://localhost:8001/mcp",
        }
    }
)

tools = await client.get_tools()  
agent = create_agent(
    "claude-sonnet-4-5-20250929",
    tools  
)

# Use the agent
github_response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "List my GitHub repositories"}]}
)
math_response = await agent.ainvoke(
    {"messages": [{"role": "user", "content": "what's (3 + 5) x 12?"}]}
)
```

## 📚 Available Presets

### Development Platforms
- **GitHub** - Repositories, issues, PRs, workflows
- **GitLab** - Projects, CI/CD, issues  
- **Bitbucket** - Repositories and pipelines

### Data & Storage
- **PostgreSQL** - Database operations
- **MongoDB** - Document operations
- **Redis** - Cache and data structures
- **VectorDB** - Vector database operations

### Communication
- **Slack** - Channels, messages, workflows
- **Discord** - Servers and channels
- **Teams** - Microsoft Teams integration

### Productivity
- **Notion** - Databases, pages, blocks
- **Confluence** - Spaces and pages
- **Jira** - Projects, issues, workflows

### Cloud Services
- **AWS S3** - Storage operations
- **Azure Blob** - Azure storage
- **Google Cloud Storage** - GCP storage

### System Operations
- **Local Operations** - File system and system ops
- **Docker** - Container management
- **Kubernetes** - Cluster operations

## 🤖 Agent Types

### Reflection Agent
Self-improving agent that refines responses through iterative refinement.

```python
from mcp_arena.agent.reflection import ReflectionAgent

agent = ReflectionAgent(
    name="reflector",
    instructions="Analyze and refine responses",
    max_iterations=3
)
```

### ReAct Agent
Systematic reasoning and acting cycle for complex problem-solving.

```python
from mcp_arena.agent.react import ReActAgent

agent = ReActAgent(
    name="react-agent",
    instructions="Systematically solve problems",
    max_steps=10
)
```

### Planning Agent
Goal decomposition and step-by-step execution for complex tasks.

```python
from mcp_arena.agent.planning import PlanningAgent

agent = PlanningAgent(
    name="planner",
    instructions="Plan and execute complex workflows"
)
```

### Router Agent
Dynamic agent selection based on task requirements.

```python
from mcp_arena.agent.router import RouterAgent

router = RouterAgent(
    name="router",
    agents=[react_agent, reflect_agent],
    selection_strategy="auto"
)
```

## 🔧 Custom Tools

Extend any preset with custom tools:

```python
from mcp_arena.presets.github import GithubMCPServer
from mcp_arena.tools.base import tool

@tool(description="Custom repository analyzer")
def analyze_repo(repo: str) -> str:
    return f"Analysis for {repo}"

server = GithubMCPServer(
    token="your_token",
    extra_tools=[analyze_repo]
)
```

## 🏗️ Custom MCP Server

Build from scratch for full control:

```python
from mcp_arena.mcp.server import BaseMCPServer
from mcp_arena.tools.base import tool

@tool(description="Search internal docs")
def search_docs(query: str) -> str:
    return f"Results for {query}"

class CustomMCPServer(BaseMCPServer):
    def _register_tools(self):
        self.add_tool(search_docs)

server = CustomMCPServer(
    name="custom-server",
    description="Custom MCP server"
)
server.run()
```

## 📖 Documentation

### Architecture

```
MCP Client
   │
   ▼
┌─────────────────┐
│   MCP Server    │  ← Core Layer
│ - Protocol      │
│ - Auth          │
│ - Tool Registry │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│  Agent System   │  ← Intelligence Layer
│ - Reflection    │
│ - ReAct         │
│ - Planning      │
│ - Router        │
└─────────────────┘
   │
   ▼
┌─────────────────┐
│ Tool Ecosystem  │  ← Execution Layer
│ - Presets       │
│ - Custom Tools  │
│ - Orchestration │
└─────────────────┘
```

### Installation Options

```bash
# Core only
pip install mcp-arena[core]

# Development platforms
pip install mcp-arena[github,gitlab,bitbucket]

# Data & storage
pip install mcp-arena[postgres,mongodb,redis,vectordb]

# Communication
pip install mcp-arena[slack]

# Productivity
pip install mcp-arena[notion,confluence,jira]

# Cloud services
pip install mcp-arena[aws,docker,kubernetes]

# System operations
pip install mcp-arena[local_operation]

# Agent framework
pip install mcp-arena[agents]

# All presets
pip install mcp-arena[all]

# Complete with dev tools
pip install mcp-arena[complete]
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Setup

```bash
# Clone the repository
git clone https://github.com/SatyamSingh8306/mcp_arena.git
cd mcp_arena

# Install in development mode
pip install -e .[dev]

# Run tests
pytest

# Run linting
black .
isort .
mypy .
```

### Priority Areas

- New preset implementations
- Agent pattern improvements  
- Documentation and examples
- Bug fixes and performance

## 📋 Requirements

- Python 3.12+
- MCP client compatible with Model Context Protocol v1.0+

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Documentation](https://github.com/SatyamSingh8306/mcp_arena)
- [Repository](https://github.com/SatyamSingh8306/mcp_arena.git)
- [Issues](https://github.com/SatyamSingh8306/mcp_arena/issues)
- [PyPI](https://pypi.org/project/mcp-arena/)

## 🚧 Status

**Version:** 0.1.0 (Early-stage)

✅ **Stable Features:**
- MCP server base classes
- 10+ production-ready presets
- 4 agent types
- Tool registration system
- SOLID architecture

🔄 **Evolving APIs:**
- Agent interfaces may enhance based on feedback
- New preset additions
- Performance optimizations

📈 **Production Ready:**
- Comprehensive documentation
- Active development
- Community support


