"""
02_prompt_and_tool.py — MCP Server with a Tool and a Prompt

Builds on the hello server by adding a reusable prompt template.
Prompts let you define structured instruction templates that clients
can retrieve and fill in with arguments.

Usage:
    python 02_prompt_and_tool.py

What it demonstrates:
    - Registering a tool with @self.mcp_server.tool()
    - Registering a prompt with @self.mcp_server.prompt()
    - Combining tools and prompts in one server
"""

from mcp_arena import BaseMCPServer


class PromptToolServer(BaseMCPServer):
    """MCP server with a tool and a prompt template."""

    def __init__(self):
        super().__init__(
            name="prompt-tool-server",
            description="MCP server demonstrating tools and prompts together",
            transport="stdio",
        )

    def _register_tools(self) -> None:
        """Register tools and prompts."""

        # --- Tool: Summarize text ---
        @self.mcp_server.tool()
        def summarize(text: str, max_words: int = 50) -> str:
            """Summarize a piece of text.

            Args:
                text: The text to summarize.
                max_words: Maximum number of words in the summary.

            Returns:
                A shortened version of the text.
            """
            words = text.split()
            if len(words) <= max_words:
                return text
            return " ".join(words[:max_words]) + "..."

        self._registered_tools.append("summarize")

        # --- Prompt: Summary request template ---
        @self.mcp_server.prompt()
        def summary_prompt(topic: str) -> str:
            """Generate a prompt asking for a summary of a topic.

            Args:
                topic: The topic to summarize.

            Returns:
                A formatted prompt string.
            """
            return (
                f"Please provide a concise summary of the following topic: {topic}. "
                f"Focus on the key points and keep it brief."
            )


# --- Entry Point ---
if __name__ == "__main__":
    server = PromptToolServer()

    print(f"Server: {server.name}")
    print(f"Tools:  {server.get_registered_tools()}")
    print("Starting server on stdio transport...")

    server.run()
