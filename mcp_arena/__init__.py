"""
mcp_arena - An opinionated Python library for building MCP servers
"""
from dotenv import load_dotenv
load_dotenv()

__version__ = "0.1.0"
__author__ = "Satyam Singh"
__license__ = "MIT"

from mcp_arena.mcp.server import BaseMCPServer
from mcp_arena.agent.base import BaseAgent

__all__ = [
    "BaseMCPServer",
    "BaseAgent",
]
