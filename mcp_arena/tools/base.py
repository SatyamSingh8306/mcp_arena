from mcp_arena.mcp.server import BaseMCPServer
from typing import List
from mcp.types import Tool

class BaseMCPTool:
    def __init__(self,mcp_server : BaseMCPServer):
        self.server = mcp_server
    
    def get_list_of_tools(self)->List[Tool]:
        github_tools = self.server.mcp_server.list_tools()
        return github_tools
    
    def remove_tool(self,name :str):
        return self.server.mcp_server.remove_tool(name)
    
    def call_tool(self,name : str):
        return self.server.mcp_server.call_tool(name)
