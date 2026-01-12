"""
LangChain Integration Wrapper for mcp_arena MCP servers.

This module provides a simple interface to integrate mcp_arena MCP servers
with LangChain agents, handling server lifecycle, tool extraction, and agent creation.
"""

import asyncio
import subprocess
import sys
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading
import time

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain.agents import create_agent
from langchain_core.language_models import BaseLanguageModel

from mcp_arena.mcp.server import BaseMCPServer


class MCPLangChainIntegration:
    """
    Integration class for mcp_arena MCP servers with LangChain agents.
    
    This class handles:
    - MCP server lifecycle management
    - Automatic tool extraction from MCP servers
    - LangChain agent creation with MCP tools
    - Concurrent server execution
    - Clean shutdown of resources
    """
    
    def __init__(self, llm: BaseLanguageModel, default_transport: str = "stdio"):
        """
        Initialize the integration wrapper.
        
        Args:
            llm: LangChain language model to use with agents
            default_transport: Default transport protocol for MCP servers
        """
        self.llm = llm
        self.default_transport = default_transport
        self.servers: Dict[str, BaseMCPServer] = {}
        self.server_processes: Dict[str, subprocess.Popen] = {}
        self.client: Optional[MultiServerMCPClient] = None
        self.agent = None
        self.tools: List[Any] = []
        self.executor = ThreadPoolExecutor(max_workers=10)
        self._shutdown_event = threading.Event()
        
    def add_mcp_server(self, name: str, server: BaseMCPServer, **kwargs) -> 'MCPLangChainIntegration':
        """
        Add an MCP server instance to the integration.
        
        Args:
            name: Unique name for the server
            server: MCP server instance
            **kwargs: Additional configuration for the server
            
        Returns:
            Self for method chaining
        """
        self.servers[name] = server
        return self
    
    def add_github_server(self, token: str, name: str = "github", **kwargs) -> 'MCPLangChainIntegration':
        """
        Convenience method to add GitHub MCP server.
        
        Args:
            token: GitHub personal access token
            name: Server name (default: "github")
            **kwargs: Additional server configuration
            
        Returns:
            Self for method chaining
        """
        from mcp_arena.presents.github import GithubMCPServer
        
        server = GithubMCPServer(token=token, **kwargs)
        return self.add_mcp_server(name, server)
    
    def add_slack_server(self, bot_token: str, name: str = "slack", **kwargs) -> 'MCPLangChainIntegration':
        """
        Convenience method to add Slack MCP server.
        
        Args:
            bot_token: Slack bot token
            name: Server name (default: "slack")
            **kwargs: Additional server configuration
            
        Returns:
            Self for method chaining
        """
        from mcp_arena.presents.slack import SlackMCPServer
        
        server = SlackMCPServer(bot_token=bot_token, **kwargs)
        return self.add_mcp_server(name, server)
    
    def add_gmail_server(self, credentials_path: str, token_path: str, name: str = "gmail", **kwargs) -> 'MCPLangChainIntegration':
        """
        Convenience method to add Gmail MCP server.
        
        Args:
            credentials_path: Path to Google credentials JSON
            token_path: Path to token JSON file
            name: Server name (default: "gmail")
            **kwargs: Additional server configuration
            
        Returns:
            Self for method chaining
        """
        from mcp_arena.presents.mail import GmailMCPServer
        
        server = GmailMCPServer(
            credentials_path=credentials_path,
            token_path=token_path,
            **kwargs
        )
        return self.add_mcp_server(name, server)
    
    def _create_server_script(self, server: BaseMCPServer, name: str) -> str:
        """Create a Python script to run the MCP server."""
        script_content = f"""
import sys
import os

# Add the mcp_arena package to Python path
sys.path.insert(0, r'{Path(__file__).parent.parent}')

from mcp_arena.presents.{server.__class__.__module__.split('.')[-1]} import {server.__class__.__name__}

# Recreate the server with the same configuration
server = {server.__class__.__name__}(
    transport="{server.transport}",
    host="{server.host}",
    port={server.port},
    debug={getattr(server, 'debug', False)},
    auto_register_tools={getattr(server, 'auto_register_tools', True)}
)

# Add any additional configuration
{self._get_server_config_code(server)}

# Run the server
try:
    server.run()
except KeyboardInterrupt:
    print(f"Shutting down {name} server...")
except Exception as e:
    print(f"Error in {name} server: {{e}}")
    sys.exit(1)
"""
        return script_content
    
    def _get_server_config_code(self, server: BaseMCPServer) -> str:
        """Extract configuration code for server recreation."""
        config_lines = []
        
        # Common configurations
        if hasattr(server, '_GithubMCPServer__token'):
            config_lines.append(f"server._GithubMCPServer__token = '{server._GithubMCPServer__token}'")
        
        if hasattr(server, 'bot_token'):
            config_lines.append(f"server.bot_token = '{server.bot_token}'")
            
        # Add more server-specific configurations as needed
        
        return '\n'.join(config_lines)
    
    async def start_servers(self) -> None:
        """Start all MCP servers in background processes."""
        print(f"Starting {len(self.servers)} MCP servers...")
        
        for name, server in self.servers.items():
            if server.transport == "stdio":
                # For stdio transport, we need to run in subprocess
                await self._start_stdio_server(name, server)
            elif server.transport in ["sse", "streamable-http"]:
                # For HTTP transports, we can connect directly
                await self._start_http_server(name, server)
            else:
                print(f"Warning: Unsupported transport {server.transport} for server {name}")
    
    async def _start_stdio_server(self, name: str, server: BaseMCPServer) -> None:
        """Start a stdio MCP server in subprocess."""
        # Create temporary script file
        script_path = Path(f"temp_{name}_server.py")
        script_content = self._create_server_script(server, name)
        
        try:
            script_path.write_text(script_content)
            
            # Start the subprocess
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.server_processes[name] = process
            print(f"Started {name} server (PID: {process.pid})")
            
            # Give the server a moment to start
            await asyncio.sleep(1)
            
        except Exception as e:
            print(f"Failed to start {name} server: {e}")
            if script_path.exists():
                script_path.unlink()
    
    async def _start_http_server(self, name: str, server: BaseMCPServer) -> None:
        """Start an HTTP MCP server."""
        def run_server():
            try:
                server.run()
            except Exception as e:
                print(f"Error in {name} server: {e}")
        
        # Run HTTP server in background thread
        self.executor.submit(run_server)
        print(f"Started {name} HTTP server on {server.host}:{server.port}")
        
        # Give the server a moment to start
        await asyncio.sleep(1)
    
    async def create_client(self) -> MultiServerMCPClient:
        """Create and configure the MultiServerMCPClient."""
        client_config = {}
        
        for name, server in self.servers.items():
            if server.transport == "stdio" and name in self.server_processes:
                # Configure stdio transport
                script_path = Path(f"temp_{name}_server.py")
                client_config[name] = {
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [str(script_path.absolute())]
                }
            elif server.transport in ["sse", "streamable-http"]:
                # Configure HTTP transport
                url = f"http://{server.host}:{server.port}"
                if server.transport == "sse":
                    url += "/sse"
                else:
                    url += "/mcp"
                
                client_config[name] = {
                    "transport": server.transport,
                    "url": url
                }
        
        self.client = MultiServerMCPClient(client_config)
        return self.client
    
    async def initialize(self) -> None:
        """
        Initialize the complete integration.
        
        This method:
        1. Starts all MCP servers
        2. Creates the MCP client
        3. Extracts tools from all servers
        4. Creates the LangChain agent
        
        Must be called before using the agent.
        """
        print("Initializing MCP-LangChain integration...")
        
        # Start all servers
        await self.start_servers()
        
        # Create client and connect
        self.client = await self.create_client()
        
        # Extract tools
        self.tools = await self.client.get_tools()
        print(f"Extracted {len(self.tools)} tools from {len(self.servers)} MCP servers")
        
        # Create agent
        self.agent = create_agent(self.llm, self.tools)
        print("LangChain agent created successfully!")
    
    async def invoke(self, message: str, **kwargs) -> str:
        """
        Invoke the agent with a message.
        
        Args:
            message: The message to send to the agent
            **kwargs: Additional arguments for agent invocation
            
        Returns:
            Agent response
        """
        if not self.agent:
            raise RuntimeError("Integration not initialized. Call await initialize() first.")
        
        response = await self.agent.ainvoke({
            "messages": [{"role": "user", "content": message}],
            **kwargs
        })
        
        return response.content if hasattr(response, 'content') else str(response)
    
    async def shutdown(self) -> None:
        """Clean shutdown of all resources."""
        print("Shutting down MCP-LangChain integration...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop server processes
        for name, process in self.server_processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"Stopped {name} server")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"Force killed {name} server")
            except Exception as e:
                print(f"Error stopping {name} server: {e}")
        
        # Clean up temporary files
        for name in self.servers.keys():
            script_path = Path(f"temp_{name}_server.py")
            if script_path.exists():
                try:
                    script_path.unlink()
                except Exception as e:
                    print(f"Error cleaning up {script_path}: {e}")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        print("Shutdown complete!")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        # Note: For async context managers, use async with
        if exc_type is None:
            # Try to shutdown synchronously if possible
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If loop is already running, we can't wait
                    loop.create_task(self.shutdown())
                else:
                    loop.run_until_complete(self.shutdown())
            except Exception as e:
                print(f"Error during shutdown: {e}")


class AsyncMCPLangChainIntegration(MCPLangChainIntegration):
    """Async context manager version of MCPLangChainIntegration."""
    
    async def __aenter__(self):
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()


# Convenience function for quick setup
async def create_github_agent(token: str, llm: BaseLanguageModel, **kwargs) -> AsyncMCPLangChainIntegration:
    """
    Quick setup for a GitHub-focused agent.
    
    Args:
        token: GitHub personal access token
        llm: LangChain language model
        **kwargs: Additional configuration
        
    Returns:
        Configured integration ready to use
    """
    integration = AsyncMCPLangChainIntegration(llm)
    integration.add_github_server(token, **kwargs)
    
    async with integration:
        return integration


# Example usage:
"""
from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_integration import MCPLangChainIntegration

# Initialize LLM
llm = ChatOpenAI(model="gpt-4")

# Create integration
integration = MCPLangChainIntegration(llm)

# Add servers
integration.add_github_server(token="your_github_token")
integration.add_slack_server(bot_token="your_slack_token")

# Initialize (in async context)
await integration.initialize()

# Use the agent
response = await integration.invoke("List my GitHub repositories and their star counts")
print(response)

# Clean shutdown
await integration.shutdown()

# Or use as context manager:
async with AsyncMCPLangChainIntegration(llm) as integration:
    integration.add_github_server(token="your_github_token")
    response = await integration.invoke("What are my latest GitHub activities?")
    print(response)
"""
