"""
Examples demonstrating how to use MCP servers with LangChain agents.

This file shows how to:
1. Connect MCP servers to LangChain agents
2. Use the new browser, video, and other MCP servers with agents
3. Create powerful AI agents with tool access
"""

import asyncio
import os

from langchain_openai import ChatOpenAI
from mcp_arena.wrapper.langchain_wrapper import MCPLangChainWrapper


def get_llm(model: str = "gpt-4-turbo", **kwargs):
    """Get a LangChain LLM instance from environment."""
    return ChatOpenAI(
        model=model,
        temperature=kwargs.get("temperature", 0),
        openai_api_key=os.getenv("OPENAI_API_KEY")
    )


async def example_1_browser_agent():
    """Example 1: Create an agent with browser automation tools."""
    print("=== Example 1: Browser Automation Agent ===\n")

    try:
        from mcp_arena.presents.browser import BrowserMCPServer

        # Create browser MCP server
        browser_server = BrowserMCPServer(
            headless=True,
            viewport_width=1920,
            viewport_height=1080
        )

        # Create wrapper with browser server
        wrapper = MCPLangChainWrapper(
            servers={"browser": browser_server},
            auto_start=True
        )

        # Connect and create agent
        await wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} browser tools: {[t.name for t in tools]}\n")

        # Create agent with proper LLM instance
        agent = wrapper.create_agent(
            llm=get_llm(),
            system_prompt="You are a helpful browser automation assistant. Use the tools to navigate websites, fill forms, take screenshots, and extract data."
        )

        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "Go to example.com and tell me what the page title is"
        )
        print(f"Agent Response: {response}\n")

        await wrapper.disconnect()
        print("Browser agent example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Install browser dependencies: pip install mcp-arena[browser]\n")


async def example_2_video_editing_agent():
    """Example 2: Create an agent with video editing tools."""
    print("=== Example 2: Video Editing Agent ===\n")

    try:
        from mcp_arena.presents.video import VideoMCPServer

        # Create video MCP server
        video_server = VideoMCPServer(
            default_output_dir="./video_output"
        )

        # Create wrapper with video server
        wrapper = MCPLangChainWrapper(
            servers={"video": video_server},
            auto_start=True
        )

        # Connect and create agent
        await wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} video tools: {[t.name for t in tools]}\n")

        # Create agent with proper LLM instance
        agent = wrapper.create_agent(
            llm=get_llm(),
            system_prompt="You are a helpful video editing assistant. Use the tools to trim, merge, add effects to videos, and convert formats."
        )

        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "How would I trim a video to keep only the first 30 seconds?"
        )
        print(f"Agent Response: {response}\n")

        await wrapper.disconnect()
        print("Video agent example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Install video dependencies: pip install mcp-arena[video]\n")


async def example_3_pdf_agent():
    """Example 3: Create an agent with PDF processing tools."""
    print("=== Example 3: PDF Processing Agent ===\n")

    try:
        from mcp_arena.presents.pdf import PDFMCPServer

        # Create PDF MCP server
        pdf_server = PDFMCPServer(
            default_output_dir="./pdf_output"
        )

        # Create wrapper with PDF server
        wrapper = MCPLangChainWrapper(
            servers={"pdf": pdf_server},
            auto_start=True
        )

        # Connect and create agent
        await wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} PDF tools: {[t.name for t in tools]}\n")

        # Create agent with proper LLM instance
        agent = wrapper.create_agent(
            llm=get_llm(),
            system_prompt="You are a helpful PDF processing assistant. Use the tools to extract text, merge PDFs, add watermarks, and convert formats."
        )

        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "What tools are available for extracting text from PDFs?"
        )
        print(f"Agent Response: {response}\n")

        await wrapper.disconnect()
        print("PDF agent example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}")
        print("Install PDF dependencies: pip install mcp-arena[pdf]\n")


async def example_4_multi_server_agent():
    """Example 4: Create an agent with multiple MCP servers."""
    print("=== Example 4: Multi-Server Agent ===\n")

    try:
        from mcp_arena.presents.browser import BrowserMCPServer
        from mcp_arena.presents.pdf import PDFMCPServer
        from mcp_arena.presents.web_scraping import WebScrapingMCPServer

        # Create multiple MCP servers
        browser_server = BrowserMCPServer(headless=True)
        pdf_server = PDFMCPServer()
        web_server = WebScrapingMCPServer()

        # Create wrapper with all servers
        wrapper = MCPLangChainWrapper(
            servers={
                "browser": browser_server,
                "pdf": pdf_server,
                "web": web_server
            },
            auto_start=True
        )

        # Connect and create agent
        await wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} total tools\n")

        # Create agent with proper LLM instance
        agent = wrapper.create_agent(
            llm=get_llm(),
            system_prompt="""You are a powerful research assistant with access to:
            - Browser automation (navigate websites, take screenshots, fill forms)
            - PDF processing (extract text, merge, split, convert)
            - Web scraping (extract data from websites)

            Use these tools to help users with their research tasks."""
        )

        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "I need to research climate change. First, find a relevant Wikipedia article, take a screenshot, and then extract the text to a PDF."
        )
        print(f"Agent Response: {response}\n")

        await wrapper.disconnect()
        print("Multi-server agent example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}\n")


async def example_5_synchronous_wrapper():
    """Example 5: Using the synchronous wrapper for simpler use cases."""
    print("=== Example 5: Synchronous Wrapper ===\n")

    try:
        from mcp_arena.presents.qrcode import QRCodeMCPServer

        # Create QR code server
        qr_server = QRCodeMCPServer()

        # Use synchronous wrapper
        wrapper = MCPLangChainWrapper(
            servers={"qrcode": qr_server},
            auto_start=True
        )

        # Connect (synchronous via wrapper)
        wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} QR code tools: {[t.name for t in tools]}\n")

        # Create agent with proper LLM instance
        agent = wrapper.create_agent(
            llm=get_llm(),
            system_prompt="You are a QR code assistant. Use tools to generate QR codes."
        )

        # Use agent
        response = wrapper.invoke_agent(
            agent,
            "Generate a QR code that links to https://example.com"
        )
        print(f"Agent Response: {response}\n")

        wrapper.disconnect()
        print("Synchronous wrapper example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}\n")


async def example_6_custom_agent_with_llm():
    """Example 6: Using custom LLM with MCP servers."""
    print("=== Example 6: Custom LLM Integration ===\n")

    try:
        from mcp_arena.presents.spreadsheet import SpreadsheetMCPServer

        # Initialize custom LLM
        llm = ChatOpenAI(
            model="gpt-4-turbo",
            temperature=0.7,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Create spreadsheet server
        spreadsheet_server = SpreadsheetMCPServer()

        # Create wrapper
        wrapper = MCPLangChainWrapper(
            servers={"spreadsheet": spreadsheet_server},
            auto_start=True
        )

        # Connect with custom LLM
        await wrapper.connect()
        tools = wrapper.get_tools()
        print(f"Loaded {len(tools)} spreadsheet tools\n")

        # Create agent with custom LLM
        agent = wrapper.create_agent(
            llm=llm,  # Use custom LLM instance
            system_prompt="You are a data analysis assistant. Use spreadsheet tools to help analyze and process data."
        )

        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "Show me what tools are available for reading and writing spreadsheets"
        )
        print(f"Agent Response: {response}\n")

        await wrapper.disconnect()
        print("Custom LLM example completed!\n")

    except ImportError as e:
        print(f"Import error: {e}\n")


async def run_all_examples():
    """Run all examples."""
    print("=" * 60)
    print("MCP Server + LangChain Agent Examples")
    print("=" * 60 + "\n")

    examples = [
        example_1_browser_agent,
        example_2_video_editing_agent,
        example_3_pdf_agent,
        example_4_multi_server_agent,
        example_5_synchronous_wrapper,
        example_6_custom_agent_with_llm
    ]

    for i, example in enumerate(examples, 1):
        try:
            await example()
        except Exception as e:
            print(f"Example {i} failed: {str(e)}\n")
        print("-" * 60 + "\n")

    print("\nAll examples completed!")


if __name__ == "__main__":
    # Set your OpenAI API key as environment variable
    # os.environ["OPENAI_API_KEY"] = "your-api-key"

    # Run examples
    asyncio.run(run_all_examples())
