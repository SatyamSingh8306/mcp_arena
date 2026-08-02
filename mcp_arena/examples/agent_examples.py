"""Examples of building a LangChain agent from mcp_arena MCP servers."""
import asyncio


def example_1_single_server():
    """One MCP server, one LLM, one call to make_mcp_agent."""
    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import make_mcp_agent
    from mcp_arena.presents.audio import AudioMCPServer

    llm = ChatOpenAI(model="gpt-4o")
    agent = asyncio.run(make_mcp_agent(
        llm,
        [AudioMCPServer()],
        system_prompt="You can process audio files.",
    ))
    result = agent.invoke({"messages": [{"role": "user", "content": "List my audio tools"}]})
    print(result["messages"][-1].content)


def example_2_multiple_servers():
    """Combine tools from multiple MCP servers into a single agent."""
    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import make_mcp_agent
    from mcp_arena.presents.audio import AudioMCPServer
    from mcp_arena.presents.image import ImageMCPServer

    llm = ChatOpenAI(model="gpt-4o")
    agent = asyncio.run(make_mcp_agent(
        llm,
        [AudioMCPServer(), ImageMCPServer()],
        system_prompt="You can edit audio and images.",
    ))
    print(agent)


def example_3_filter_tools():
    """Expose only the tools the agent should use, drop the rest."""
    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import make_mcp_agent, ToolRegistry
    from mcp_arena.presents.audio import AudioMCPServer

    llm = ChatOpenAI(model="gpt-4o")
    server = AudioMCPServer()
    reg = ToolRegistry().register_server(server)
    print("available before filter:", reg.names())
    reg.keep("get_audio_info", "convert_audio")

    agent = asyncio.run(make_mcp_agent(
        llm,
        [server],
        system_prompt="Only audio info + conversion.",
        names=reg.names(),
    ))
    print(agent)


def example_4_custom_non_mcp_tool():
    """Add a custom BaseTool alongside MCP-server tools."""
    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import BaseTool, make_mcp_agent
    from mcp_arena.presents.audio import AudioMCPServer

    class ShoutTool(BaseTool):
        def __init__(self):
            super().__init__(name="shout", description="Uppercase a string")
        def execute(self, text: str) -> str:
            return text.upper()

    llm = ChatOpenAI(model="gpt-4o")
    agent = asyncio.run(make_mcp_agent(
        llm,
        [AudioMCPServer()],
        extra_tools=[ShoutTool()],
    ))
    print(agent)


def example_5_forward_create_agent_kwargs():
    """Anything create_agent accepts is forwarded: state_schema, checkpointer, etc."""
    from langchain_openai import ChatOpenAI
    from mcp_arena.agent import make_mcp_agent
    from mcp_arena.presents.audio import AudioMCPServer
    from langgraph.checkpoint.memory import InMemorySaver

    llm = ChatOpenAI(model="gpt-4o")
    agent = asyncio.run(make_mcp_agent(
        llm,
        [AudioMCPServer()],
        system_prompt="Always confirm before editing.",
        checkpointer=InMemorySaver(),
        interrupt_before=["tools"],
        name="audio_agent",
    ))
    print(agent)


if __name__ == "__main__":
    example_1_single_server()
    example_2_multiple_servers()
    example_3_filter_tools()
    example_4_custom_non_mcp_tool()
    example_5_forward_create_agent_kwargs()
