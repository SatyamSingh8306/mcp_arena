# Installation Guide

## Quick Start

### Install Core Library
```bash
pip install mcp_arena[core]
```

### Install with Specific MCP Server
Each MCP server preset can be installed separately using extras:

#### Development Platforms
```bash
# GitHub MCP Server
pip install mcp_arena[github]

# GitLab MCP Server
pip install mcp_arena[gitlab]

# Bitbucket MCP Server
pip install mcp_arena[bitbucket]
```

#### Data & Storage
```bash
# PostgreSQL MCP Server
pip install mcp_arena[postgres]

# MongoDB MCP Server
pip install mcp_arena[mongodb]

# Redis MCP Server
pip install mcp_arena[redis]

# Vector Database MCP Server
pip install mcp_arena[vectordb]
```

#### Communication Platforms
```bash
# Slack MCP Server
pip install mcp_arena[slack]

# WhatsApp MCP Server
pip install mcp_arena[whatsapp]

# Discord MCP Server
pip install mcp_arena[discord]

# Microsoft Teams MCP Server
pip install mcp_arena[teams]
```

#### Email Services
```bash
# Gmail MCP Server
pip install mcp_arena[gmail]

# Outlook MCP Server
pip install mcp_arena[outlook]

# All Email Services
pip install mcp_arena[email]
```

#### Messaging Services
```bash
# Slack MCP Server
pip install mcp_arena[slack]

# WhatsApp MCP Server
pip install mcp_arena[whatsapp]

# All Messaging Services
pip install mcp_arena[messaging]
```

#### All Communication Services
```bash
# Install all communication services (Gmail, Outlook, Slack, WhatsApp)
pip install mcp_arena[communication]
```

#### Productivity Tools
```bash
# Notion MCP Server
pip install mcp_arena[notion]

# Confluence MCP Server
pip install mcp_arena[confluence]

# Jira MCP Server
pip install mcp_arena[jira]
```

#### Cloud Services
```bash
# AWS MCP Server
pip install mcp_arena[aws]

# Azure MCP Server
pip install mcp_arena[azure]

# Google Cloud MCP Server
pip install mcp_arena[gcp]
```

#### System Operations
```bash
# Local Operations MCP Server
pip install mcp_arena[local_operation]

# Docker MCP Server
pip install mcp_arena[docker]

# Kubernetes MCP Server
pip install mcp_arena[kubernetes]
```

#### Agent Framework
```bash
# Agent dependencies (for using agents)
pip install mcp_arena[agents]
```

### Install All Presets
```bash
# All MCP server presets (no dev dependencies)
pip install mcp_arena[all]

# Complete installation (includes dev tools)
pip install mcp_arena[complete]
```

### Install from Source
```bash
git clone https://github.com/mcp_arena/mcp_arena.git
cd mcp_arena
pip install -e .
```

### Development Installation
```bash
# Install with development dependencies
pip install -e .[complete]

# Or install core + dev tools only
pip install -e .[core,dev]
```

## Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Update `.env` with your credentials:
```env
# For GitHub MCP
GITHUB_TOKEN=your_github_token

# For Slack MCP
SLACK_BOT_TOKEN=your_slack_token

# For Notion MCP
NOTION_API_KEY=your_notion_key

# etc.
```

## Running Your First MCP Server

```python
from mcp_arena.mcp.server import BaseMCPServer
from mcp_arena.presets.github import GithubMCPServer

# Create GitHub MCP Server
server = GithubMCPServer(token="your_token")

# Start the server
server.run()
```

## Testing Installation

```bash
python -c "from mcp_arena import BaseMCPServer; print('✓ mcp_arena installed successfully')"
```

## Troubleshooting

### Missing Dependencies
If you get import errors, make sure you installed the correct optional dependencies:

```bash
# For GitHub
pip install mcp_arena[github]

# For agents
pip install mcp_arena[agents]

# For all presets
pip install mcp_arena[all]
```

### Python Version
Ensure you're using Python 3.12 or higher:
```bash
python --version
```

### Import Errors
If you encounter import errors, try installing the core dependencies first:
```bash
pip install mcp_arena[core]
```

## Next Steps

- Read the [README.md](README.md) for core concepts
- Check out examples in the `examples/` directory
- See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines
