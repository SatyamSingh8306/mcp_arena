"""
01_hello_server.py — Minimal MCP Server with One Tool

This is the simplest possible MCP server using mcp_arena.
It registers a single "greet" tool that returns a greeting message.

Usage:
    python 01_hello_server.py

What it demonstrates:
    - Subclassing BaseMCPServer
    - Registering a tool with @self.mcp_server.tool()
    - Running the server with stdio transport
"""

from mcp_arena import BaseMCPServer


class HelloServer(BaseMCPServer):
    """A minimal MCP server with one tool."""

    def __init__(self):
        super().__init__(
            name="hello-server",
            description="A minimal MCP server that greets users",
            transport="stdio",  # Use stdio for local development
        )

    def _register_tools(self) -> None:
        """Register all tools with the MCP server."""

        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Greet a user by name.

            Args:
                name: The name of the person to greet.

            Returns:
                A friendly greeting message.
            """
            return f"Hello, {name}! Welcome to mcp_arena."

        # Track registered tools
        self._registered_tools.append("greet")


# --- Entry Point ---
if __name__ == "__main__":
    server = HelloServer()

    print(f"Server: {server.name}")
    print(f"Tools:  {server.get_registered_tools()}")
    print("Starting server on stdio transport...")

    server.run()
