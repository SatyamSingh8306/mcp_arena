"""
Main entry point for mcp_arena library.
"""

def main():
    """Main entry point for the mcp_arena CLI."""
    print("mcp_arena - MCP Server Library")
    print("Use this library to build MCP servers with ready-to-use presets.")
    print("\nQuick start:")
    print("  from mcp_arena.presets.github import GithubMCPServer")
    print("  server = GithubMCPServer(token='your_token')")
    print("  server.run()")


if __name__ == "__main__":
    main()
