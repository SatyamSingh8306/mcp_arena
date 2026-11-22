"""
mcp_arena - An opinionated Python library for building MCP servers
"""
import sys
import types

try:
    import jira  # noqa: F401
except ImportError:
    try:
        from atlassian import Jira as _Jira
        _jira_mod = types.ModuleType("jira")
        _jira_mod.JIRA = _Jira
        sys.modules.setdefault("jira", _jira_mod)
    except ImportError:
        pass

from dotenv import load_dotenv
load_dotenv()

__version__ = "0.5.0"
__author__ = "Satyam Singh"
__license__ = "MIT"

from mcp_arena.mcp.server import BaseMCPServer

__all__ = ["BaseMCPServer"]