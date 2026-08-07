"""
03_agent_flow.py — Full End-to-End: Server → Agent → Tool Execution

This example shows the complete mcp_arena pipeline:
  1. Create an MCP server with custom tools
  2. Wrap the server tools for agent use
  3. Create an agent (ReAct or Reflection)
  4. Process a user query through the agent

Usage:
    python 03_agent_flow.py

What it demonstrates:
    - Building a custom MCP server with tools
    - Using MCPAgentWrapper to bridge server tools to agents
    - Creating agents with AgentFactory / AgentBuilder
    - Processing queries through the agent pipeline
"""

from mcp_arena import BaseMCPServer
from mcp_arena.agent.factory import AgentFactory, AgentBuilder
from mcp_arena.agent.tools import CalculatorTool
from mcp_arena.wrapper.agent_wrapper import MCPAgentWrapper


# ─── Step 1: Define a Custom MCP Server ──────────────────────────────────────

class MathServer(BaseMCPServer):
    """MCP server with a simple math tool."""

    def __init__(self):
        super().__init__(
            name="math-server",
            description="A minimal math server for the agent flow example",
            transport="stdio",
        )

    def _register_tools(self) -> None:
        """Register math tools."""

        @self.mcp_server.tool()
        def add(a: int, b: int) -> int:
            """Add two numbers together.

            Args:
                a: First number.
                b: Second number.

            Returns:
                The sum of a and b.
            """
            return a + b

        @self.mcp_server.tool()
        def multiply(a: int, b: int) -> int:
            """Multiply two numbers.

            Args:
                a: First number.
                b: Second number.

            Returns:
                The product of a and b.
            """
            return a * b

        self._registered_tools.extend(["add", "multiply"])


# ─── Step 2: Wrap Server Tools for Agent Use ─────────────────────────────────

def wrap_server_tools():
    """Create an MCP server and wrap its tools for agent consumption."""
    server = MathServer()

    # MCPAgentWrapper bridges MCP tools → agent-compatible tools
    wrapper = MCPAgentWrapper(server)

    print(f"Server '{server.name}' has {len(wrapper.tools)} wrapped tools:")
    for tool in wrapper.tools:
        print(f"  - {tool.name}: {tool.description}")

    return wrapper


# ─── Step 3: Create an Agent ─────────────────────────────────────────────────

def create_agent_with_factory():
    """Create a ReAct agent using the AgentFactory."""
    factory = AgentFactory()

    # List available agent types
    print(f"Available agent types: {factory.list_agent_types()}")

    # Create a ReAct agent (Reasoning + Acting)
    agent = factory.create_agent("react", config={
        "memory_type": "conversation",
        "max_steps": 5,
    })

    return agent


def create_agent_with_builder():
    """Create a ReAct agent using the Builder pattern."""
    agent = (
        AgentBuilder("react")
        .with_memory("conversation", max_history=20)
        .with_tool(CalculatorTool())
        .with_config(max_steps=5)
        .build()
    )

    return agent


# ─── Step 4: Run the Full Pipeline ──────────────────────────────────────────

def run_full_pipeline():
    """Demonstrate the complete server → agent → tool flow."""

    print("=" * 60)
    print(" mcp_arena: Minimal End-to-End Example")
    print("=" * 60)

    # 1. Create the MCP server
    print("\n--- Step 1: Create MCP Server ---")
    server = MathServer()
    print(f"Created server: {server.name}")
    print(f"Registered tools: {server.get_registered_tools()}")

    # 2. Wrap tools for agent use
    print("\n--- Step 2: Wrap Tools ---")
    wrapper = MCPAgentWrapper(server)
    print(f"Wrapped {len(wrapper.tools)} tools for agent use")

    # 3. Create an agent
    print("\n--- Step 3: Create Agent ---")
    agent = create_agent_with_builder()
    print(f"Created agent: {type(agent).__name__}")

    # 4. Process a query
    print("\n--- Step 4: Process Query ---")
    query = "What is 15 + 27?"
    print(f"Query: {query}")

    response = agent.process(query)
    print(f"Response: {response}")

    print("\n" + "=" * 60)
    print(" Pipeline complete!")
    print("=" * 60)


# --- Entry Point ---
if __name__ == "__main__":
    run_full_pipeline()
