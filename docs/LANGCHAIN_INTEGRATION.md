# LangChain Integration Guide

This guide explains how to integrate mcp_arena MCP servers with LangChain agents using the provided wrapper classes.

## Overview

The `mcp_arena.wrapper.langchain_integration` module provides two main classes:

- **`MCPLangChainIntegration`** - Base class for manual setup
- **`AsyncMCPLangChainIntegration`** - Async context manager for automatic setup

## Quick Start

### Installation

```bash
# Install required dependencies
pip install langchain-openai langchain-mcp-adapters

# Install mcp_arena with communication services
pip install "mcp_arena[communication]"
```

### Basic Usage

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_integration import AsyncMCPLangChainIntegration

async def main():
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4")
    
    # Create integration with context manager
    async with AsyncMCPLangChainIntegration(llm) as integration:
        # Add GitHub server
        integration.add_github_server(
            token="your_github_token",
            transport="stdio"
        )
        
        # Add Slack server
        integration.add_slack_server(
            bot_token="xoxb-your-slack-token",
            transport="stdio"
        )
        
        # Use the agent
        response = await integration.invoke(
            "List my GitHub repositories and their star counts"
        )
        print(f"Agent Response: {response}")

# Run the example
asyncio.run(main())
```

## Detailed Usage

### Manual Setup

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_integration import MCPLangChainIntegration

async def main():
    # Initialize LLM
    llm = ChatOpenAI(model="gpt-4")
    
    # Create integration
    integration = MCPLangChainIntegration(llm)
    
    try:
        # Add servers
        integration.add_github_server(token="your_token")
        integration.add_slack_server(bot_token="your_token")
        
        # Initialize everything
        await integration.initialize()
        
        # Use the agent
        response = await integration.invoke("Your message here")
        print(response)
        
    finally:
        # Clean shutdown
        await integration.shutdown()

asyncio.run(main())
```

### Adding Different Server Types

#### GitHub Server
```python
integration.add_github_server(
    token="github_pat_token",
    name="github",  # Optional custom name
    transport="stdio"
)
```

#### Slack Server
```python
integration.add_slack_server(
    bot_token="xoxb-your-slack-token",
    name="slack",
    transport="stdio"
)
```

#### Gmail Server
```python
integration.add_gmail_server(
    credentials_path="path/to/credentials.json",
    token_path="path/to/token.json",
    name="gmail"
)
```

#### Custom Server
```python
from mcp_arena.presents.docker import DockerMCPServer

docker_server = DockerMCPServer(
    host="127.0.0.1",
    port=8003,
    transport="stdio"
)

integration.add_mcp_server("docker", docker_server)
```

### Transport Options

- **`stdio`** - Standard input/output (default, good for local testing)
- **`sse`** - Server-Sent Events (good for web clients)
- **`streamable-http`** - Full HTTP protocol (good for complex interactions)

```python
# Use SSE transport
integration.add_github_server(
    token="your_token",
    transport="sse",
    host="0.0.0.0",  # Listen on all interfaces
    port=8001
)
```

## Advanced Features

### Multi-Service Agents

The integration automatically combines tools from all added servers:

```python
async with AsyncMCPLangChainIntegration(llm) as integration:
    # Add multiple services
    integration.add_github_server(token="github_token")
    integration.add_slack_server(bot_token="slack_token")
    integration.add_gmail_server(
        credentials_path="creds.json",
        token_path="token.json"
    )
    
    # Agent can now use all services
    response = await integration.invoke(
        "Check my latest GitHub commits, "
        "summarize important Gmail messages, "
        "and post a summary to Slack"
    )
```

### Error Handling

The integration provides graceful error handling:

```python
try:
    async with AsyncMCPLangChainIntegration(llm) as integration:
        integration.add_github_server(token="invalid_token")
        response = await integration.invoke("Test message")
except Exception as e:
    print(f"Integration error: {e}")
```

### Server Configuration

You can pass additional configuration to servers:

```python
integration.add_github_server(
    token="your_token",
    host="127.0.0.1",
    port=8001,
    transport="stdio",
    debug=True,
    auto_register_tools=True
)
```

## Examples

### GitHub-Only Agent
```python
async def github_agent():
    llm = ChatOpenAI(model="gpt-4")
    
    async with AsyncMCPLangChainIntegration(llm) as integration:
        integration.add_github_server(token="your_token")
        
        response = await integration.invoke(
            "What are my latest 5 GitHub activities?"
        )
        return response
```

### Communication Services Agent
```python
async def communication_agent():
    llm = ChatOpenAI(model="gpt-4")
    
    async with AsyncMCPLangChainIntegration(llm) as integration:
        integration.add_gmail_server(
            credentials_path="gmail_creds.json",
            token_path="gmail_token.json"
        )
        integration.add_slack_server(bot_token="slack_token")
        
        response = await integration.invoke(
            "Check my important emails and summarize them"
        )
        return response
```

### DevOps Agent
```python
async def devops_agent():
    llm = ChatOpenAI(model="gpt-4")
    
    async with AsyncMCPLangChainIntegration(llm) as integration:
        integration.add_github_server(token="github_token")
        from mcp_arena.presents.docker import DockerMCPServer
        
        docker_server = DockerMCPServer(transport="stdio")
        integration.add_mcp_server("docker", docker_server)
        
        response = await integration.invoke(
            "Deploy the latest changes from GitHub to Docker"
        )
        return response
```

## Requirements

### Python Version
- Python 3.8+

### Dependencies
- `langchain` - Core LangChain framework
- `langchain-mcp-adapters` - MCP adapter for LangChain
- `langchain-openai` - OpenAI LLM provider (or other LangChain LLMs)
- `mcp_arena` - This library with relevant server packages

### MCP Server Dependencies
Dependencies vary by server type:

- **GitHub**: `PyGithub`
- **Slack**: `slack-sdk`
- **Gmail**: `google-auth`, `google-api-python-client`
- **Docker**: `docker`
- **And more...**

Install with:
```bash
pip install "mcp_arena[complete]"  # All dependencies
# or
pip install "mcp_arena[github,slack,gmail,docker]"  # Specific ones
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed
2. **Server Startup**: Check that servers can start independently
3. **Token Issues**: Verify API tokens are valid and have proper permissions
4. **Port Conflicts**: Use different ports for HTTP transports

### Debug Mode

Enable debug mode for more verbose output:

```python
integration.add_github_server(
    token="your_token",
    debug=True  # Enables debug logging
)
```

### Testing

Test individual servers before integration:

```python
# Test GitHub server alone
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token="your_token")
# server.run()  # Uncomment to test
```

## Best Practices

1. **Use Context Managers**: Prefer `AsyncMCPLangChainIntegration` for automatic cleanup
2. **Handle Tokens Securely**: Use environment variables or secret managers
3. **Test Individually**: Verify each MCP server works before integration
4. **Monitor Resources**: Keep an eye on memory usage with multiple servers
5. **Graceful Shutdown**: Always use proper shutdown procedures

## Next Steps

- Explore the [Examples](../examples/langchain_integration_example.py) for more detailed usage
- Check the [MCP Servers Guide](MCP_SERVERS_GUIDE.md) for server-specific configuration
- Review the [Agent Guide](AGENT_GUIDE.md) for agent customization
