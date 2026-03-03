# Minimal End-to-End MCP Server Examples

A collection of "hello-world" style examples demonstrating how to build and use MCP servers with `mcp_arena`. These examples are designed for **developer onboarding** — each one is self-contained, minimal, and well-commented.

## Examples Overview

| File | Description |
|------|-------------|
| `01_hello_server.py` | Minimal MCP server with a single tool |
| `02_prompt_and_tool.py` | MCP server with a tool + a prompt template |
| `03_agent_flow.py` | Full end-to-end: MCP server → Agent → Tool execution |
| `04_multi_tool_server.py` | MCP server with multiple tools and structured responses |

## Prerequisites

```bash
pip install mcp_arena
```

## Quick Start

### 1. Run a Minimal Server

```bash
python 01_hello_server.py
```

This starts an MCP server with a single `greet` tool over stdio transport.

### 2. Server with Prompt + Tool

```bash
python 02_prompt_and_tool.py
```

Demonstrates how to combine a tool with a reusable prompt template.

### 3. Full Agent Flow

```bash
python 03_agent_flow.py
```

Shows the complete pipeline: create server → wrap tools → create agent → process query.

### 4. Multi-Tool Server

```bash
python 04_multi_tool_server.py
```

A slightly more advanced example with multiple tools and structured data.

## Architecture Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  MCP Server  │────▶│  Agent       │────▶│  Tools      │
│  (FastMCP)   │     │  (ReAct/     │     │  (greet,    │
│              │     │   Reflect)   │     │   calc, ..) │
└─────────────┘     └──────────────┘     └─────────────┘
       │                    │
       ▼                    ▼
  Prompts/            Memory/State
  Resources           Management
```

**Key Concepts:**
- **BaseMCPServer**: Abstract base class — subclass it and implement `_register_tools()`
- **Tools**: Functions decorated with `@self.mcp_server.tool()` inside your server
- **Prompts**: Templates registered with `@self.mcp_server.prompt()`
- **Agents**: Orchestrators (ReAct, Reflection, Planning) that use tools to answer queries
- **MCPAgentWrapper**: Bridges MCP server tools into agent-compatible format

## Next Steps

- See [docs/QUICKSTART.md](../docs/QUICKSTART.md) for the full quickstart guide
- See [docs/TOOLS_GUIDE.md](../docs/TOOLS_GUIDE.md) for all available built-in tools
- See [docs/AGENT_GUIDE.md](../docs/AGENT_GUIDE.md) for agent configuration
- See [docs/MCP_SERVERS_GUIDE.md](../docs/MCP_SERVERS_GUIDE.md) for preset servers
