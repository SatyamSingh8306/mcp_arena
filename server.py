from mcp_arena.presents import LocalOperationsMCPServer
# from mcp_arena.presents.browser import BrowserMCPServer

mcp_server = LocalOperationsMCPServer()
if __name__ == "__main__":
    mcp_server.run(transport="streamable-http")