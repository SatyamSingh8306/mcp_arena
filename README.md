# mcp_arena

[![PyPI version](https://badge.fury.io/py/mcp-arena.svg)](https://badge.fury.io/py/mcp-arena)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/mcp-arena?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/mcp-arena)

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

@mcp_server.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b


# Add a dynamic greeting resource
@mcp_servevr.resource("greeting://{name}")
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

## Advance Documentation
```
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

### With Agent Orchestration

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

### Browser & Automation
- **Browser** - Browser automation with Playwright (navigate, screenshot, forms, extract data)
- **Screen Capture** - Take screenshots and screen recordings with PyAutoGUI

### Video & Media
- **Video** - Video editing (trim, merge, effects, format conversion) with FFmpeg
- **PDF** - PDF processing (extract text/images, merge, split, watermark, encrypt)
- **QR Code** - Generate and decode QR codes

### Data & Files
- **Spreadsheet** - Excel/CSV read/write with pandas and openpyxl
- **Web Scraping** - Extract data from websites with requests and BeautifulSoup

### Communication
- **Slack** - Channels, messages, workflows
- **WhatsApp** - Messaging via Twilio API
- **Gmail** - Email management and sending
- **Outlook** - Microsoft 365 email and calendar
- **Discord** - Servers and channels
- **Teams** - Microsoft Teams integration
- **Notification** - Multi-platform notifications (Email, Slack, webhooks)

### Development Platforms
- **GitHub** - Repositories, issues, PRs, workflows
- **GitLab** - Projects, CI/CD, issues
- **Bitbucket** - Repositories and pipelines

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
from mcp_arena.agent.reflection_agent import ReflectionAgent

agent = ReflectionAgent(
    llm=None,
    memory_type="conversation"
)
```

### ReAct Agent
Systematic reasoning and acting cycle for complex problem-solving.

```python
from mcp_arena.agent.react_agent import ReactAgent

agent = ReactAgent(
    llm=None,
    memory_type="conversation"
)
```

### Planning Agent
Goal decomposition and step-by-step execution for complex tasks.

```python
from mcp_arena.agent.planning_agent import PlanningAgent

agent = PlanningAgent(
    llm=None,
    memory_type="conversation"
)
```

### Router Agent
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

## 🤖 LangChain Integration

Integrate mcp_arena MCP servers with LangChain agents for powerful multi-service automation:

```python
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper
from mcp_arena.presents.browser import BrowserMCPServer

# Initialize LLM
llm = ChatOpenAI(model="gpt-4-turbo")

# Create wrapper with browser server
wrapper = MCPLangChainWrapper(
    servers={"browser": BrowserMCPServer(headless=True)},
    auto_start=True
)

# Connect and create agent
await wrapper.connect()
agent = wrapper.create_agent(
    llm=llm,
    system_prompt="You are a helpful browser automation assistant"
)

# Use the agent
response = await wrapper.invoke_agent(
    agent,
    "Go to example.com and tell me the page title"
)
```

### Multi-Server Agent Example

```python
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper
from mcp_arena.presents.browser import BrowserMCPServer
from mcp_arena.presents.pdf import PDFMCPServer
from mcp_arena.presents.web_scraping import WebScrapingMCPServer

# Initialize LLM
llm = ChatOpenAI(model="gpt-4-turbo")

# Create wrapper with multiple servers
wrapper = MCPLangChainWrapper(
    servers={
        "browser": BrowserMCPServer(headless=True),
        "pdf": PDFMCPServer(),
        "web": WebScrapingMCPServer()
    },
    auto_start=True
)

# Connect and create agent with all tools
await wrapper.connect()
agent = wrapper.create_agent(
    llm=llm,
    system_prompt="""You are a powerful research assistant with access to:
    - Browser automation (navigate websites, take screenshots)
    - PDF processing (extract text, merge, split)
    - Web scraping (extract data from websites)
    """
)

# Use the agent
response = await wrapper.invoke_agent(
    agent,
    "Research climate change: find a Wikipedia article, take a screenshot, and extract key facts to a PDF"
)
```

**Installation:**
```bash
pip install langchain-openai langchain-mcp-adapters
pip install "mcp-arena[browser,video,pdf,webscraping]"
```

📖 **[Full Documentation](docs/LANGCHAIN_INTEGRATION.md)**
📖 **[Agent Examples](mcp_arena/examples/mcp_server_agent_examples.py)**

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

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed installation instructions for all presets and communication services
- **[MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md)** - Comprehensive guide to all 17 available MCP servers
- **[Agent Guide](docs/AGENT_GUIDE.md)** - Using and configuring intelligent agents
- **[Tools Guide](docs/TOOLS_GUIDE.md)** - Tool development and integration
- **[LangChain Integration](docs/LANGCHAIN_INTEGRATION.md)** - Integrate MCP servers with LangChain agents
- **[Quick Start](docs/QUICKSTART.md)** - Get started in minutes
- **[Tutorial](docs/tutorial.md)** - Step-by-step tutorial

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

# Browser automation
pip install mcp-arena[browser]

# Video editing
pip install mcp-arena[video]

# PDF processing
pip install mcp-arena[pdf]

# QR code generation
pip install mcp-arena[qrcode]

# Spreadsheet operations
pip install mcp-arena[spreadsheet]

# Web scraping
pip install mcp-arena[webscraping]

# Screen capture
pip install mcp-arena[screencapture]

# Cloud storage (AWS S3, GCS, Azure)
pip install mcp-arena[cloudstorage]

# Notifications (Email, Slack, webhooks)
pip install mcp-arena[notification]

# Development platforms
pip install mcp-arena[github,gitlab,bitbucket]

# Data & storage
pip install mcp-arena[postgres,mongodb,redis,vectordb]

# Communication
pip install mcp-arena[slack,whatsapp,gmail,outlook]

# All communication services
pip install mcp-arena[communication]

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

- [Documentation](docs/) - Complete documentation library
- [Installation Guide](docs/INSTALLATION.md) - Installation instructions
- [MCP Servers Guide](docs/MCP_SERVERS_GUIDE.md) - Server documentation
- [LangChain Integration](docs/LANGCHAIN_INTEGRATION.md) - LangChain integration guide
- [Repository](https://github.com/SatyamSingh8306/mcp_arena.git)
- [Issues](https://github.com/SatyamSingh8306/mcp_arena/issues)
- [PyPI](https://pypi.org/project/mcp-arena/)

## 🚧 Status

**Version:** 0.2.1 (Production-ready)

✅ **Stable Features:**
- MCP server base classes
- 17 production-ready presets
- 4 agent types
- Tool registration system
- SOLID architecture
- Communication services (Gmail, Outlook, Slack, WhatsApp)

🔄 **Evolving APIs:**
- Agent interfaces may enhance based on feedback
- New preset additions
- Performance optimizations

📈 **Production Ready:**
- Comprehensive documentation
- Active development
- Community support


