from mcp_arena.mcp.server import BaseMCPServer
from typing import List

class MyGreetingServer(BaseMCPServer):
    def _register_tools(self) -> None:
        """
        Required by BaseMCPServer. 
        In this case, we are adding a resource instead of a tool,
        so we can leave this method empty.
        """
        pass

# 1. Initialize the server instance
# BaseMCPServer sets up the internal FastMCP instance for us
server = MyGreetingServer(
    name="GreetingServer",
    description="A server that provides dynamic greetings via MCP resources"
)

# 2. FIX: Use @server.mcp_server.resource
# We must reference the 'mcp_server' attribute of our 'server' object
@server.mcp_server.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    # This will start the server using the default transport (stdio)
    server.run()
