from abc import ABC, abstractmethod
from typing import Literal, Annotated, Optional, Collection, List, Dict, Callable, Any
from mcp.server.fastmcp import FastMCP


def require_extras(extra_to_pkg: Dict[str, str]) -> None:
    """Raise an `ImportError` listing the `pip install` command if any package is missing.

    Presets declare `_REQUIRED_EXTRAS = {"PyGithub": "github", ...}` so that
    running without the matching extra produces a clear, actionable error.

    Usage:
        class GithubMCPServer(BaseMCPServer):
            _REQUIRED_EXTRAS = {"PyGithub": "github"}

            def __init__(self, ...):
                require_extras(self._REQUIRED_EXTRAS)
                super().__init__(...)
    """
    missing = [
        (pkg, extra)
        for pkg, extra in extra_to_pkg.items()
        if _missing_module(pkg)
    ]
    if not missing:
        return
    extras = sorted({extra for _, extra in missing})
    extras_str = ",".join(extras)
    pkgs = sorted({pkg for pkg, _ in missing})
    if len(pkgs) == 1:
        pkgs_str = pkgs[0]
    else:
        pkgs_str = ", ".join(pkgs[:-1]) + f" and {pkgs[-1]}"
    cmd = f'pip install "mcp-arena[{extras_str}]"'
    raise ImportError(
        f"{pkgs_str} {'is' if len(pkgs) == 1 else 'are'} required for this MCP server "
        f"but {'is' if len(pkgs) == 1 else 'are'} not installed.\n"
        f"Install it with:    {cmd}\n"
        f"(or use `mcp-arena[{extras_str}]` in your project config)."
    )


def _missing_module(name: str) -> bool:
    """Return True iff `name` cannot be imported."""
    import importlib
    try:
        importlib.import_module(name)
        return False
    except Exception:
        return True


class BaseMCPServer(ABC):
    # Override in subclasses: maps `import_name -> pip-extra-name`.
    # Anything in here is checked at construction and triggers the friendly
    # `pip install mcp-arena[extra]` ImportError if missing.
    _REQUIRED_EXTRAS: Dict[str, str] = {}

    def __init__(
        self,
        name: str,
        description: str,
        host: Annotated[str, "Host on which MCP server runs"] = "127.0.0.1",
        port: Annotated[int, "Port on which MCP server runs"] = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
        mount_path: str = "/",
        sse_path: str = "/sse",
        message_path: str = "/messages/",
        streamable_http_path: str = "/mcp",
        json_response: bool = False,
        stateless_http: bool = False,
        dependencies: Collection[str] = (),
        auto_register_tools: bool = True
    ):
        """Initialize the base MCP server.

        Args:
            name: Server name
            description: Server description/instructions
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            log_level: Logging level
            mount_path: Mount path for HTTP server
            sse_path: SSE endpoint path
            message_path: Message endpoint path
            streamable_http_path: Streamable HTTP endpoint path
            json_response: Enable JSON response mode
            stateless_http: Enable stateless HTTP mode
            dependencies: Additional dependencies
            auto_register_tools: Automatically register tools on initialization
        """
        require_extras(self._REQUIRED_EXTRAS)

        self.name = name
        self.description = description
        self.host = host
        self.port = port
        self.transport = transport
        self.debug = debug
        self.log_level = log_level

        self.mcp_server = FastMCP(
            name=name,
            instructions=description,
            host=host,
            port=port,
            debug=debug,
            log_level=log_level,
            mount_path=mount_path,
            sse_path=sse_path,
            message_path=message_path,
            streamable_http_path=streamable_http_path,
            json_response=json_response,
            stateless_http=stateless_http,
            dependencies=dependencies
        )

        # Store registered tools for agent wrapper compatibility
        self._registered_tools: Dict[str, Callable[..., Any]] = {}

        if auto_register_tools:
            self._register_tools()

        # After registration, sync tools from FastMCP for agent wrapper access
        self._sync_registered_tools()

    @abstractmethod
    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""
        pass
    
    def __getattr__(self, name):
        return getattr(self.mcp_server, name)

    def _sync_registered_tools(self) -> None:
        """Sync registered tools from FastMCP for agent wrapper access."""
        # FastMCP stores tools in _tools dict
        if hasattr(self.mcp_server, '_tools'):
            for name, tool_info in self.mcp_server._tools.items():
                if isinstance(tool_info, dict) and 'fn' in tool_info:
                    self._registered_tools[name] = tool_info['fn']
                else:
                    self._registered_tools[name] = tool_info

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names.

        Returns:
            List of registered tool names
        """
        return list(self._registered_tools.keys())

    def run(self, transport: Optional[Literal['stdio', 'sse', 'streamable-http']] = None) -> None:
        """Run the MCP server.
        
        Args:
            transport: Transport type (uses instance default if not specified)
        """
        transport_to_use = transport or self.transport
        self.mcp_server.run(transport=transport_to_use)
    
    def invoke(self, transport: Optional[Literal['stdio', 'sse', 'streamable-http']] = None) -> None:
        """Run the MCP server (alias for run)."""
        transport_to_use = transport or self.transport
        self.run(transport=transport_to_use)
    
    def __str__(self):
        return f"{self.name} \n {self.description}"

    def __repr__(self):
        return f"MCPServer(name='{self.name}', host='{self.host}', port={self.port})"