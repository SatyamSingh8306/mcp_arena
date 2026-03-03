from abc import ABC, abstractmethod
from typing import Literal, Annotated, Optional, Collection, List, Callable, Any, Dict
from mcp.server.fastmcp import FastMCP
import logging
import inspect

logger = logging.getLogger("mcp_arena.server")


class ToolRegistrationError(Exception):
    """Raised when a tool fails to register with the MCP server."""
    pass


class BaseMCPServer(ABC):
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
        
        # Store registered tools for reference
        self._registered_tools: List[str] = []
        # Store tool metadata for introspection
        self._tool_metadata: Dict[str, Dict[str, Any]] = {}

        if auto_register_tools:
            self._register_tools()
            tool_count = len(self._registered_tools)
            if tool_count > 0:
                logger.info(
                    "Server '%s' registered %d tool(s): %s",
                    self.name,
                    tool_count,
                    ", ".join(self._registered_tools),
                )
            else:
                logger.warning(
                    "Server '%s' completed _register_tools() but no tools were registered. "
                    "Ensure tools are registered using @self.mcp_server.tool() or self.register_tool().",
                    self.name,
                )

    @abstractmethod
    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""
        pass

    # ------------------------------------------------------------------
    # Tool registration helpers
    # ------------------------------------------------------------------

    def tool(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> Callable:
        """Decorator to register a tool with the MCP server.

        This wraps FastMCP's ``tool()`` decorator while tracking tool names
        in ``_registered_tools`` and providing clear error messages when
        registration fails.

        Args:
            name: Optional name for the tool (defaults to function name).
            description: Optional description of the tool.
            **kwargs: Additional keyword arguments forwarded to FastMCP.tool().

        Returns:
            A decorator that registers the wrapped function as a tool.

        Raises:
            ToolRegistrationError: If the function is not callable or
                registration with FastMCP fails.

        Example::

            server = MyMCPServer()

            @server.tool()
            def greet(name: str) -> str:
                return f"Hello, {name}!"
        """

        def decorator(fn: Callable) -> Callable:
            tool_name = name or getattr(fn, "__name__", str(fn))
            self.register_tool(fn, name=name, description=description, **kwargs)
            return fn

        return decorator

    def register_tool(
        self,
        fn: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Register a single tool function with the MCP server.

        This is the imperative (non-decorator) counterpart of :meth:`tool`.
        It validates the function, delegates to FastMCP, tracks the tool
        in ``_registered_tools``, and logs the result.

        Args:
            fn: The callable to register as a tool.
            name: Optional name (defaults to ``fn.__name__``).
            description: Optional description.
            **kwargs: Additional keyword arguments forwarded to ``FastMCP.add_tool``.

        Returns:
            The resolved tool name.

        Raises:
            ToolRegistrationError: If *fn* is not callable or FastMCP rejects
                the tool.
        """
        tool_name = name or getattr(fn, "__name__", None)

        # --- validation ---
        if not callable(fn):
            msg = f"Cannot register tool '{tool_name}': the object is not callable."
            logger.error(msg)
            raise ToolRegistrationError(msg)

        if tool_name is None:
            msg = (
                "Cannot register tool: unable to determine a name. "
                "Pass an explicit 'name' argument."
            )
            logger.error(msg)
            raise ToolRegistrationError(msg)

        if tool_name in self._registered_tools:
            logger.warning(
                "Tool '%s' is already registered on server '%s'. "
                "Overwriting the previous registration.",
                tool_name,
                self.name,
            )
            # Remove the old entry so we can re-add cleanly
            self._registered_tools.remove(tool_name)

        # --- delegate to FastMCP ---
        try:
            self.mcp_server.add_tool(fn, name=name, description=description, **kwargs)
        except Exception as exc:
            msg = (
                f"Failed to register tool '{tool_name}' on server '{self.name}': {exc}"
            )
            logger.error(msg)
            raise ToolRegistrationError(msg) from exc

        # --- bookkeeping ---
        self._registered_tools.append(tool_name)
        self._tool_metadata[tool_name] = {
            "name": tool_name,
            "description": description or (fn.__doc__ or "").strip().split("\n")[0],
            "function": fn.__qualname__,
            "module": getattr(fn, "__module__", None),
        }
        logger.debug("Registered tool '%s' on server '%s'.", tool_name, self.name)
        return tool_name

    def validate_tools(self) -> Dict[str, Any]:
        """Validate that all tracked tools are present in the FastMCP registry.

        Returns:
            A dict with keys ``valid`` (bool), ``registered`` (list of tracked
            tool names), ``missing`` (tools tracked but absent from FastMCP),
            and ``untracked`` (tools in FastMCP but not tracked here).
        """
        tracked = set(self._registered_tools)

        # FastMCP stores tools in _tool_manager._tools
        try:
            fastmcp_tools = set(self.mcp_server._tool_manager._tools.keys())
        except AttributeError:
            # Fallback: if internal API changes, report what we can
            logger.warning(
                "Could not introspect FastMCP tool registry for server '%s'.",
                self.name,
            )
            return {
                "valid": None,
                "registered": sorted(tracked),
                "missing": [],
                "untracked": [],
            }

        missing = sorted(tracked - fastmcp_tools)
        untracked = sorted(fastmcp_tools - tracked)

        if missing:
            logger.error(
                "Server '%s': tools tracked but missing from FastMCP registry: %s",
                self.name,
                ", ".join(missing),
            )
        if untracked:
            logger.warning(
                "Server '%s': tools in FastMCP registry but not tracked: %s. "
                "Use server.tool() or server.register_tool() to register tools "
                "so they are properly tracked.",
                self.name,
                ", ".join(untracked),
            )

        return {
            "valid": len(missing) == 0,
            "registered": sorted(tracked),
            "missing": missing,
            "untracked": untracked,
        }
    
    def __getattr__(self, name):
        # Prevent __getattr__ from silently forwarding tool() to FastMCP
        # which would bypass our tracking. All other attributes still
        # delegate to the underlying FastMCP server.
        if name == "tool":
            raise AttributeError(
                f"Use '{type(self).__name__}.tool()' decorator or "
                f"'{type(self).__name__}.register_tool()' to register tools. "
                f"Direct access to the underlying FastMCP tool() decorator "
                f"bypasses tool tracking and validation."
            )
        return getattr(self.mcp_server, name)

    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names.
        
        Returns:
            List of registered tool names
        """
        return self._registered_tools.copy()

    def get_tool_metadata(self) -> Dict[str, Dict[str, Any]]:
        """Get metadata for all registered tools.

        Returns:
            A dict mapping tool names to their metadata (name, description,
            function, module).
        """
        return {k: dict(v) for k, v in self._tool_metadata.items()}

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