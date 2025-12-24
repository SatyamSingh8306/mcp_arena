# mcp_arena

**mcp_arena** is an opinionated Python library for building **MCP (Model Context Protocol) servers** with minimal setup and strong defaults.

It provides **ready-to-use MCP servers** (called *presets*) that already include **domain-specific tools**, authentication, and configuration, plus a **comprehensive agent system** with built-in reasoning, reflection, and planning capabilities.

> 🔹 **MCP server is the core abstraction**
> 🔹 **Agents provide intelligent orchestration**
> 🔹 **Presets ship with tools by default**
> 🔹 **Built on SOLID architecture principles**

---

## Why mcp_arena?

Most MCP examples start from a blank server and ask you to:

* implement protocol wiring
* manually define every tool
* handle auth and schemas
* glue everything together

**mcp_arena flips this model.**

You start with a **fully functional MCP server** and customize only what you need.

---

## Core Concept

### 1. MCP Server (Core)

The MCP server is responsible for:

* exposing tools and resources
* handling authentication
* managing MCP protocol & transport
* registering capabilities

This layer works **independently of agents**.

---

### 2. Presets (Batteries Included)

Presets are **ready-made MCP servers** for common platforms.

Each preset:

* comes with **most commonly used tools built in**
* handles authentication automatically
* follows best practices for that platform

## Available Presets

### 🚀 Development Platforms
- **`GithubMCPServer`** - GitHub repositories, issues, PRs, workflows
- **`GitLabMCPServer`** - GitLab projects, CI/CD, issues
- **`BitbucketMCPServer`** - Bitbucket repositories and pipelines

### 📊 Data & Storage
- **`PostgresMCPServer`** - PostgreSQL database operations
- **`MongoDBMCPServer`** - MongoDB document operations
- **`RedisMCPServer`** - Redis cache and data structures
- **`VectorDBMCPServer`** - Vector database operations

### 🤝 Communication
- **`SlackMCPServer`** - Slack channels, messages, workflows
- **`DiscordMCPServer`** - Discord servers and channels
- **`TeamsMCPServer`** - Microsoft Teams integration

### 📝 Productivity
- **`NotionMCPServer`** - Notion databases, pages, blocks
- **`ConfluenceMCPServer`** - Confluence spaces and pages
- **`JiraMCPServer`** - Jira projects, issues, workflows

### ☁️ Cloud Services
- **`S3MCPServer`** - AWS S3 storage operations
- **`AzureBlobMCPServer`** - Azure Blob storage
- **`GCStorageMCPServer`** - Google Cloud Storage

### 🖥️ System Operations
- **`LocalOperationsMCPServer`** - File system and system operations
- **`DockerMCPServer`** - Docker container management
- **`KubernetesMCPServer`** - Kubernetes cluster operations

---

## Agent Types

### 🤔 Reflection Agent
- **Purpose**: Self-improving responses through iterative refinement
- **Use Case**: Quality-critical tasks requiring precision
- **Features**: Multi-pass refinement, error correction

### ⚡ ReAct Agent  
- **Purpose**: Systematic reasoning and acting
- **Use Case**: Complex problem-solving workflows
- **Features**: Step-by-step reasoning, tool orchestration

### 📋 Planning Agent
- **Purpose**: Goal decomposition and execution planning
- **Use Case**: Multi-step complex tasks
- **Features**: Task breakdown, progress tracking

### 🎯 Router Agent
- **Purpose**: Dynamic agent selection and routing
- **Use Case**: Multi-domain task handling
- **Features**: Smart routing, load balancing

---

### 3. Agent System (Intelligent Orchestration)

The agent system provides **intelligent tool orchestration** with multiple built-in agent types:

* **Reflection Agent** - Self-improving through iterative refinement
* **ReAct Agent** - Reasoning and acting cycle
* **Planning Agent** - Goal decomposition and step-by-step execution
* **Router Agent** - Dynamic agent selection and task routing

Agents:

* use existing MCP tools intelligently
* perform complex reasoning and planning
* handle multi-step workflows
* are completely optional but powerful

You can run:

* MCP server **without agents** (direct tool access)
* MCP server **with single or multiple agents**
* **Agent-only mode** for orchestration tasks

## Quick Start Guide

### 1. Install mcp_arena
```bash
pip install mcp_arena
```

### 2. Choose Your Approach

**🚀 Preset (Recommended for quick start)**
```python
from mcp_arena.presets.github import GithubMCPServer

server = GithubMCPServer(token="your_token")
server.run()
```

**🤖 Agent-Enhanced (For intelligent orchestration)**
```python
from mcp_arena.presets.github import GithubMCPServer
from mcp_arena.agent.react import ReActAgent

agent = ReActAgent(name="github-agent")
server = GithubMCPServer(token="your_token", agents=[agent])
server.run()
```

**🔧 Custom Server (For full control)**
```python
from mcp_arena.mcp.server import BaseMCPServer
from mcp_arena.tools.base import tool

class MyMCPServer(BaseMCPServer):
    def _register_tools(self):
        # Register your tools here
        pass

server = MyMCPServer(name="my-server", description="Custom MCP server")
server.run()
```

---

## GitHub MCP — Zero Configuration Example

`GitHubMCP` already includes a **rich set of GitHub tools** by default
(search, repos, issues, PRs, etc.).

```python
from mcp_arena.presets.github import GithubMCPServer

mcp = GithubMCPServer(
    token="ghp_xxx"
)

mcp.run(port=8000)
```

✔ Tools included by default
✔ Auth handled internally
✔ No manual registration required

---

## Extending a Preset with Custom Tools

You can **add or override tools** when needed.

```python
from mcp_arena.presets.github import GithubMCPServer
from mcp_arena.tools.base import tool

@tool(description="Custom repo analyzer")
def analyze_repo(repo: str):
    return f"Analysis for {repo}"

mcp = GithubMCPServer(
    token="ghp_xxx",
    extra_tools=[analyze_repo]
)

mcp.run()
```

Presets are **extensible, not rigid**.

---

## MCP Server Without Presets (Low-level Use)

If you want full control, you can build directly on the MCP server.

```python
from mcp_arena.mcp.server import BaseMCPServer
from mcp_arena.tools.base import tool

@tool(description="Search internal docs")
def search_docs(query: str):
    return f"Results for {query}"

class DocsMCPServer(BaseMCPServer):
    def _register_tools(self):
        self.add_tool(search_docs)

server = DocsMCPServer(
    name="docs-mcp",
    description="MCP server for internal documentation"
)

server.run()
```

This is useful for:

* internal systems
* custom data sources
* experimental MCP servers

---

## Using Agents for Intelligent Orchestration

Agents provide **intelligent tool orchestration** with built-in reasoning capabilities.

### Reflection Agent
Self-improving agent that refines responses through multiple iterations:

```python
from mcp_arena.presets.github import GithubMCPServer
from mcp_arena.agent.reflection import ReflectionAgent

agent = ReflectionAgent(
    name="github-reflector",
    instructions="Help users explore repositories with self-refinement",
    max_iterations=3
)

mcp = GithubMCPServer(
    token="ghp_xxx",
    agents=[agent]
)

mcp.run()
```

### ReAct Agent
Reasoning and acting cycle for systematic problem-solving:

```python
from mcp_arena.agent.react import ReActAgent

agent = ReActAgent(
    name="github-react",
    instructions="Systematically analyze GitHub repositories",
    max_steps=10
)
```

### Planning Agent
Goal decomposition and step-by-step execution:

```python
from mcp_arena.agent.planning import PlanningAgent

agent = PlanningAgent(
    name="github-planner",
    instructions="Plan and execute complex repository analysis tasks"
)
```

### Router Agent
Dynamic agent selection based on task requirements:

```python
from mcp_arena.agent.router import RouterAgent
from mcp_arena.agent.react import ReActAgent
from mcp_arena.agent.reflection import ReflectionAgent

# Create specialized agents
react_agent = ReActAgent(name="react-agent")
reflect_agent = ReflectionAgent(name="reflect-agent")

# Router selects the best agent for each task
router = RouterAgent(
    name="github-router",
    agents=[react_agent, reflect_agent],
    selection_strategy="auto"
)
```

If you remove agents:

* MCP server still runs
* tools are still exposed
* behavior remains stable

---

## Architecture Overview

```
MCP Client
   │
   ▼
┌──────────────────────────┐
│        MCP Server        │  ← Core Layer
│  - Protocol & Transport  │
│  - Tool Registry         │
│  - Auth & Security       │
└──────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│      Agent System        │  ← Intelligence Layer
│  - Reflection Agent      │
│  - ReAct Agent           │
│  - Planning Agent        │
│  - Router Agent          │
│  - Memory & Policies     │
└──────────────────────────┘
            │
            ▼
┌──────────────────────────┐
│     Tool Ecosystem       │  ← Execution Layer
│  - Domain Presets        │
│  - Custom Tools          │
│  - Tool Orchestration    │
└──────────────────────────┘
```

---

## Design Philosophy

* **MCP servers should work out of the box** - Zero configuration for common use cases
* **Presets include real, useful tools** - Production-ready, not toy examples
* **Agents provide intelligent orchestration** - Smart tool usage and reasoning
* **Built on SOLID principles** - Maintainable, extensible architecture
* **Defaults over configuration** - Sensible defaults, customization when needed
* **Minimal boilerplate, maximum clarity** - Clean, intuitive APIs
* **Composable architecture** - Mix and match components freely

---

## Roadmap

### 🚧 Near Term (v0.2)
* [ ] Full MCP HTTP / stdio transport support
* [ ] Streaming responses and real-time updates
* [ ] Enhanced error handling and logging
* [ ] Performance optimizations

### 🎯 Medium Term (v0.3)
* [ ] More built-in presets (GitLab, Discord, Azure)
* [ ] Tool permission policies and security
* [ ] Agent supervision and monitoring
* [ ] Memory integrations (RAG, vector stores)

### 🚀 Long Term (v1.0)
* [ ] Graph-based agent workflows
* [ ] Multi-agent collaboration patterns
* [ ] Advanced observability and debugging
* [ ] Enterprise features (SSO, audit logs)

### 🤝 Contributing
We welcome contributions! See our [Contributing Guide](CONTRIBUTING.md) for details.

**Priority areas:**
- New preset implementations
- Agent pattern improvements
- Documentation and examples
- Bug fixes and performance

---

## Status

🚧 **Early-stage (v0.1.0)** - Core functionality is stable and tested

✅ **Working Features:**
- MCP server base classes and utilities
- 10+ production-ready presets
- 4 agent types (Reflection, ReAct, Planning, Router)
- Tool creation and registration
- SOLID architecture implementation

🔄 **Evolving APIs:**
- Agent interfaces may be enhanced based on feedback
- New preset additions
- Performance optimizations

📈 **Adoption Ready:**
- Production use cases supported
- Comprehensive documentation
- Active development and support

**Feedback and contributions are welcome!** 🎉

---

## License

MIT


