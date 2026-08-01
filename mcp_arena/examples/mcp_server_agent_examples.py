"""
Examples demonstrating how to use MCP servers with LangChain agents.

Each example follows the same pattern:
1. Pick one or more MCP-server presets.
2. Build a LangChain agent with `make_mcp_agent(llm, servers, ...)`.
3. Invoke the agent.

Prerequisites:
    pip install mcp-arena[agents] langchain-openai
    pip install "mcp-arena[browser,video,pdf,webscraping,qrcode,spreadsheet]"
"""
import asyncio
import os

from langchain_openai import ChatOpenAI

from mcp_arena.agent import make_mcp_agent


def get_llm(model: str = "gpt-4o", **kwargs):
    """Return a default OpenAI chat model."""
    return ChatOpenAI(
        model=model,
        temperature=kwargs.get("temperature", 0),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
    )


async def example_1_browser_agent():
    """Browser automation + LLM."""
    from mcp_arena.presents.browser import BrowserMCPServer

    agent = await make_mcp_agent(
        get_llm(),
        [BrowserMCPServer(headless=True, viewport_width=1920, viewport_height=1080)],
        system_prompt=(
            "You are a browser-automation assistant. Use the tools to navigate, "
            "fill forms, take screenshots, and extract data."
        ),
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user", "content": "Go to example.com and tell me the page title."
    }]})
    print(out["messages"][-1].content)


async def example_2_video_editing_agent():
    """Video editing + LLM."""
    from mcp_arena.presents.video import VideoMCPServer

    agent = await make_mcp_agent(
        get_llm(),
        [VideoMCPServer(default_output_dir="./video_output")],
        system_prompt="You are a video editing assistant.",
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user", "content": "How do I trim a video to keep only the first 30 seconds?"
    }]})
    print(out["messages"][-1].content)


async def example_3_pdf_agent():
    """PDF processing + LLM."""
    from mcp_arena.presents.pdf import PDFMCPServer

    agent = await make_mcp_agent(
        get_llm(),
        [PDFMCPServer(default_output_dir="./pdf_output")],
        system_prompt="You are a PDF processing assistant.",
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user", "content": "What tools are available for extracting text from PDFs?"
    }]})
    print(out["messages"][-1].content)


async def example_4_multi_server_agent():
    """Combine browser, PDF, and web-scraping into one agent."""
    from mcp_arena.presents.browser import BrowserMCPServer
    from mcp_arena.presents.pdf import PDFMCPServer
    from mcp_arena.presents.webscraping import WebScrapingMCPServer

    agent = await make_mcp_agent(
        get_llm(),
        [BrowserMCPServer(headless=True), PDFMCPServer(), WebScrapingMCPServer()],
        system_prompt=(
            "You are a research assistant with browser, PDF, and web-scraping tools. "
            "Plan the work step by step, then execute each tool."
        ),
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user",
        "content": (
            "Find a Wikipedia article on climate change, take a screenshot, "
            "and extract the text into a PDF."
        ),
    }]})
    print(out["messages"][-1].content)


async def example_5_filter_tools():
    """Use `ToolRegistry` to narrow the tool list before the agent sees it."""
    from mcp_arena.agent import ToolRegistry
    from mcp_arena.presents.qrcode import QRCodeMCPServer

    server = QRCodeMCPServer()
    reg = ToolRegistry().register_server(server)
    print("All tools on the server:", reg.names())
    reg.keep("generate_qrcode")  # only let the agent generate, never decode

    agent = await make_mcp_agent(
        get_llm(),
        [server],
        system_prompt="You only generate QR codes; you never decode arbitrary input.",
        names=reg.names(),
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user", "content": "Generate a QR code that links to https://example.com."
    }]})
    print(out["messages"][-1].content)


async def example_6_custom_tool_with_mcp():
    """Add a non-MCP `BaseTool` on top of an MCP server."""
    from mcp_arena.agent import BaseTool
    from mcp_arena.presents.spreadsheet import SpreadsheetMCPServer

    class PreviewTool(BaseTool):
        def __init__(self):
            super().__init__(name="preview", description="Return the first 100 chars of a string")
        def execute(self, s: str) -> str:
            return s[:100]

    agent = await make_mcp_agent(
        get_llm(),
        [SpreadsheetMCPServer()],
        system_prompt="You can read spreadsheets and preview long strings.",
        extra_tools=[PreviewTool()],
    )
    out = await agent.ainvoke({"messages": [{
        "role": "user",
        "content": "Show me what tools are available for reading and writing spreadsheets.",
    }]})
    print(out["messages"][-1].content)


async def example_7_sync_wrapper():
    """Synchronous flavor — `make_mcp_agent_sync`."""
    from mcp_arena.agent import make_mcp_agent_sync
    from mcp_arena.presents.qrcode import QRCodeMCPServer

    agent = make_mcp_agent_sync(
        get_llm(),
        [QRCodeMCPServer()],
        system_prompt="You generate QR codes.",
    )
    out = agent.invoke({"messages": [{
        "role": "user", "content": "Generate a QR code for https://example.com."
    }]})
    print(out["messages"][-1].content)


async def run_all_examples():
    print("=" * 60)
    print("MCP server + LangChain agent examples (make_mcp_agent)")
    print("=" * 60 + "\n")

    examples = [
        example_1_browser_agent,
        example_2_video_editing_agent,
        example_3_pdf_agent,
        example_4_multi_server_agent,
        example_5_filter_tools,
        example_6_custom_tool_with_mcp,
        example_7_sync_wrapper,
    ]
    for i, example in enumerate(examples, 1):
        try:
            await example()
        except Exception as e:
            print(f"Example {i} failed: {e}\n")
        print("-" * 60 + "\n")


if __name__ == "__main__":
    # os.environ["OPENAI_API_KEY"] = "sk-…"  # if not already in env
    asyncio.run(run_all_examples())
