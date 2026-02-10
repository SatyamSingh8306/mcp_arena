<div align="center">

# 🎯 MCP_ARENA

### _Build Intelligent AI Agents with Zero Configuration_ 🚀

[![PyPI version](https://badge.fury.io/py/mcp-arena.svg)](https://badge.fury.io/py/mcp-arena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

---

🎯 **mcp_arena** is a production-ready Python library for building **MCP (Model Context Protocol) servers** with intelligent agent orchestration and domain-specific presets.

> 💡 **Why mcp_arena?** Build powerful AI agents with pre-configured MCP servers for popular platforms, intelligent agent patterns, and seamless LangChain integration - all with zero-configuration setup!

---

## 📚 Table of Contents

<table>
<tr>
<td width="50%" valign="top">

### Core Features
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📚 Available Presets](#-available-presets)
- [🤖 Agent Types](#-agent-types)
- [🔧 Custom Tools](#-custom-tools)
- [🤖 LangChain Integration](#-langchain-integration)
- [🏗️ Custom MCP Server](#️-custom-mcp-server)

</td>
<td width="50%" valign="top">

### Resources & Info
- [📖 Documentation](#-documentation)
- [🏛️ Architecture](#️-architecture)
- [📦 Installation Options](#-installation-options)
- [🤝 Contributing](#-contributing)
- [📋 Requirements](#-requirements)
- [📄 License](#-license)
- [🔗 Links](#-links)
- [🚧 Status](#-status)

</td>
</tr>
</table>

---

## ✨ Features

- 🚀 **Ready-to-use MCP servers** for popular platforms (GitHub, Slack, Notion, AWS, etc.)
- 🤖 **Intelligent agents** with reflection, planning, and routing capabilities
- 🔧 **Zero-configuration setup** for common use cases
- 🏗️ **Extensible architecture** built on SOLID principles
- 📦 **Modular design** - use only what you need
- ⚡ **High performance** with async/await support
- 🔒 **Secure** with built-in authentication and authorization
- 🌐 **Multi-transport** support (stdio, HTTP, SSE)
- 🎨 **Rich customization** with icons, metadata, and branding

## 🚀 Quick Start

### 📦 Installation

```bash
# Core library
pip install mcp-arena

# With specific presets
pip install mcp-arena[github,slack,notion]

# All presets
pip install mcp-arena[all]
```

### 💻 Basic Usage

```python
from mcp_arena.presents.github import GithubMCPServer

# ✨ Zero-config GitHub MCP server
mcp_server = GithubMCPServer(token="your_github_token")
mcp_server.run()
```

### 🛠️ Using Tools Directly

```python
from mcp_arena.tools.github import GithubTools
from mcp_arena.presents.github import GithubMCPServer

# Create GitHub MCP server first
mcp_server = GithubMCPServer(token="your_token")

# Create tools wrapper
tool = GithubTools(server=mcp_server)
tools = tool.get_list_of_tools()

@mcp_server.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp_server.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

@mcp_server.prompt()
def greet_user(name: str, style: str = "friendly") -> str:
    """Generate a greeting prompt"""
    styles = {
        "friendly": "Please write a warm, friendly greeting",
        "formal": "Please write a formal, professional greeting",
        "casual": "Please write a casual, relaxed greeting",
    }

    return f"{styles.get(style, styles['friendly'])} for someone named {name}."

```

## 🎨 Advanced Documentation - Icons & Branding

```python
from mcp.server.fastmcp import Icon
from mcp_arena.presents.github import GithubMCPServer

# Create an icon from a file path or URL
icon = Icon(
    src="icon.png",
    mimeType="image/png",
    sizes="64x64"
)

# Add icons to server
mcp = GithubMCPServer(
    "My Server",
    website_url="https://example.com",
    token="*******",
    icons=[icon]
)

# Add icons to tools, resources, and prompts
@mcp.tool(icons=[icon])
def my_tool():
    """Tool with an icon."""
    return "result"

@mcp.resource("demo://resource", icons=[icon])
def my_resource():
    """Resource with an icon."""
    return "content"


```

### 🤖 With Agent Orchestration

```python
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.agent.react_agent import ReactAgent

# Create MCP server
mcp_server = GithubMCPServer(token="your_token")

# Create agent separately
agent = ReactAgent(llm=None, memory_type="conversation")

# Run the server
mcp_server.run()
```

### 🔗 LangChain Integration

#### 🎁 Using MCP Arena Wrapper

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

#### ⚙️ Direct langchain_mcp_adapters Usage

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

---

## 📚 Available Presets

### 💻 Development Platforms
- **GitHub** - Repositories, issues, PRs, workflows
- **GitLab** - Projects, CI/CD, issues  
- **Bitbucket** - Repositories and pipelines

### 🗄️ Data & Storage
- **PostgreSQL** - Database operations
- **MongoDB** - Document operations
- **Redis** - Cache and data structures
- **VectorDB** - Vector database operations

### 💬 Communication
- **Slack** - Channels, messages, workflows
- **WhatsApp** - Messaging via Twilio API
- **Gmail** - Email management and sending
- **Outlook** - Microsoft 365 email and calendar
- **Discord** - Servers and channels
- **Teams** - Microsoft Teams integration

### 📝 Productivity
- **Notion** - Databases, pages, blocks
- **Confluence** - Spaces and pages
- **Jira** - Projects, issues, workflows

### ☁️ Cloud Services
- **AWS S3** - Storage operations
- **Azure Blob** - Azure storage
- **Google Cloud Storage** - GCP storage

### ⚙️ System Operations
- **Local Operations** - File system and system ops
- **Docker** - Container management
- **Kubernetes** - Cluster operations

---

## 🤖 Agent Types

### 🪞 Reflection Agent
Self-improving agent that refines responses through iterative refinement.

```python
from mcp_arena.agent.reflection_agent import ReflectionAgent

agent = ReflectionAgent(
    llm=None,
    memory_type="conversation"
)
```

### ⚡ ReAct Agent
Systematic reasoning and acting cycle for complex problem-solving.

```python
from mcp_arena.agent.react_agent import ReactAgent

agent = ReactAgent(
    llm=None,
    memory_type="conversation"
)
```

### 📋 Planning Agent
Goal decomposition and step-by-step execution for complex tasks.

```python
from mcp_arena.agent.planning_agent import PlanningAgent

agent = PlanningAgent(
    llm=None,
    memory_type="conversation"
)
```

### 🔀 Router Agent
Dynamic agent selection based on task requirements.

```python
from mcp_arena.agent.router import AgentRouter

router = AgentRouter()

# Add routing rules
router.add_route(
    condition=lambda input_text: "github" in input_text.lower(),
    agent_type="react",
    config={"llm": your_llm}
)

router.add_route(
    condition=lambda input_text: "reflect" in input_text.lower(),
    agent_type="reflection",
    config={"llm": your_llm}
)
```

---

## 🔧 Custom Tools

Extend any preset with custom tools:

```python
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.tools.base import tool

@tool(description="Custom repository analyzer")
def analyze_repo(repo: str) -> str:
    return f"Analysis for {repo}"

server = GithubMCPServer(
    token="your_token",
    extra_tools=[analyze_repo]
)
```

---

## 🤖 LangChain Integration

Integrate mcp_arena MCP servers with LangChain agents for powerful multi-service automation:

```python
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_integration import AsyncMCPLangChainIntegration

# Initialize LLM
llm = ChatOpenAI(model="gpt-4")

# Create integration with automatic setup
async with AsyncMCPLangChainIntegration(llm) as integration:
    # Add your MCP servers
    integration.add_github_server(token="your_github_token")
    integration.add_slack_server(bot_token="xoxb-your-slack-token")
    integration.add_gmail_server(
        credentials_path="path/to/credentials.json",
        token_path="path/to/token.json"
    )
    
    # Use the unified agent
    response = await integration.invoke(
        "Check my latest GitHub commits and summarize important emails"
    )
    print(response)
```

### Quick Setup Examples

**🐙 GitHub Agent:**
```python
async with AsyncMCPLangChainIntegration(llm) as integration:
    integration.add_github_server(token="your_token")
    response = await integration.invoke("List my GitHub repositories")
```

**🔄 Multi-Service Agent:**
```python
async with AsyncMCPLangChainIntegration(llm) as integration:
    integration.add_github_server(token="github_token")
    integration.add_slack_server(bot_token="slack_token")
    response = await integration.invoke("Deploy latest code and notify in Slack")
```

**📦 Installation:**
```bash
pip install langchain-openai langchain-mcp-adapters
pip install "mcp_arena[communication]"
```

📖 **[Full Documentation](docs/LANGCHAIN_INTEGRATION.md)**
---
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
---
## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions for all presets and communication services
- **[MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md)** - Comprehensive guide to all 17 available MCP servers
- **[Agent Guide](docs/AGENT_GUIDE.md)** - Using and configuring intelligent agents
- **[Tools Guide](docs/TOOLS_GUIDE.md)** - Tool development and integration
- **[LangChain Integration](docs/LANGCHAIN_INTEGRATION.md)** - Integrate MCP servers with LangChain agents
- **[Quick Start](docs/QUICKSTART.md)** - Get started in minutes
- **[Tutorial](docs/tutorial.md)** - Step-by-step tutorial

### 🏛️ Architecture

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
---
### 📦 Installation Options

```bash
# 🎯 Core only
pip install mcp-arena[core]

# 💻 Development platforms
pip install mcp-arena[github,gitlab,bitbucket]

# 🗄️ Data & storage
pip install mcp-arena[postgres,mongodb,redis,vectordb]

# 💬 Communication
pip install mcp-arena[slack,whatsapp,gmail,outlook]

# 📧 All communication services
pip install mcp-arena[communication]

# 📝 Productivity
pip install mcp-arena[notion,confluence,jira]

# ☁️ Cloud services
pip install mcp-arena[aws,docker,kubernetes]

# ⚙️ System operations
pip install mcp-arena[local_operation]

# 🤖 Agent framework
pip install mcp-arena[agents]

# 🌟 All presets
pip install mcp-arena[all]

# 🚀 Complete with dev tools
pip install mcp-arena[complete]
```

---

## 🤝 Contributing

❤️ We welcome contributions! Please see our documentation for details:

- 📖 **[Contributing Guide](CONTRIBUTING.md)** - How to contribute to the project
- ⚖️ **[Code of Conduct](CODE_OF_CONDUCT.md)** - Our community guidelines and standards
- 🔒 **[Security Policy](SECURITY.md)** - How to report security vulnerabilities

Before contributing, please read these documents to understand our development process and community expectations.

### 🛠️ Development Setup

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

### 🎯 Priority Areas

- New preset implementations
- Agent pattern improvements  
- Documentation and examples
- Bug fixes and performance

---

## 📋 Requirements

- Python 3.12+
- MCP client compatible with Model Context Protocol v1.0+
---
## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🔗 Links

### 📚 Documentation
- 📖 [Complete Documentation Library](docs/) - All documentation files
- 💿 [Installation Guide](docs/INSTALLATION.md) - Installation instructions
- 🚀 [Quick Start Guide](docs/QUICKSTART.md) - Get started in minutes
- 🖥️ [MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md) - Server documentation
- 🤖 [Agent Guide](docs/AGENT_GUIDE.md) - Using and configuring agents
- 🔧 [Tools Guide](docs/TOOLS_GUIDE.md) - Tool development and integration
- 🔗 [LangChain Integration](docs/LANGCHAIN_INTEGRATION.md) - LangChain integration guide
- 📝 [Tutorial](docs/tutorial.md) - Step-by-step tutorial

### 👥 Community & Contributing
- 🤝 [Contributing Guide](CONTRIBUTING.md) - How to contribute
- ⚖️ [Code of Conduct](CODE_OF_CONDUCT.md) - Community guidelines
- 🔒 [Security Policy](SECURITY.md) - Report security vulnerabilities
- 💻 [Repository](https://github.com/SatyamSingh8306/mcp_arena.git) - GitHub repository
- 🐛 [Issues](https://github.com/SatyamSingh8306/mcp_arena/issues) - Report bugs or request features
- 💬 [Discussions](https://github.com/SatyamSingh8306/mcp_arena/discussions) - Ask questions and share ideas

### 📦 Package
- 🐍 [PyPI](https://pypi.org/project/mcp-arena/) - Python Package Index
- 📋 [Changelog](https://github.com/SatyamSingh8306/mcp_arena/releases) - Release notes

---

## 🚧 Status

**Version:** 0.2.1 ✨ (Production-ready)

✅ **Stable Features:**
- 🏗️ MCP server base classes
- 🎁 17 production-ready presets
- 🧠 4 agent types
- 🔧 Tool registration system
- 🏛️ SOLID architecture
- 📞 Communication services (Gmail, Outlook, Slack, WhatsApp)

🔄 **Evolving APIs:**
- 🔮 Agent interfaces may enhance based on feedback
- ➕ New preset additions
- ⚡ Performance optimizations

📈 **Production Ready:**
- 📚 Comprehensive documentation
- 🚀 Active development
- 👥 Community support


