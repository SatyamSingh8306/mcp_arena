"""
mcp_arena wrapper modules for external integrations.

This package provides wrappers and integrations for using mcp_arena
MCP servers with external frameworks and tools.
"""

try:
    from .langchain_integration import MCPLangChainIntegration, AsyncMCPLangChainIntegration
    from .agent_wrapper import AgentWrapper
    
    # Try to import langchain wrapper, but handle gracefully if dependencies are missing
    try:
        from .langchain_wrapper import MCPLangChainWrapper
        _all_exports = [
            "MCPLangChainIntegration",
            "AsyncMCPLangChainIntegration", 
            "MCPLangChainWrapper",
            "AgentWrapper"
        ]
    except ImportError as e:
        MCPLangChainWrapper = None
        _all_exports = [
            "MCPLangChainIntegration",
            "AsyncMCPLangChainIntegration",
            "AgentWrapper"
        ]
        print(f"Warning: LangChain wrapper not available: {e}")
    
    __all__ = _all_exports
    
except ImportError as e:
    print(f"Warning: Some wrapper modules not available: {e}")
    MCPLangChainIntegration = None
    AsyncMCPLangChainIntegration = None
    MCPLangChainWrapper = None
    AgentWrapper = None
    __all__ = []
