from ..presents import *

class RegistryMCP:
    def __init__(self):
        self.registry = [S3MCPServer,GithubMCPServer,LocalOperationsMCPServer,
                        VectorDBMCPServer,MongoDBMCPServer,NotionMCPServer,PostgresMCPServer,
                        SlackMCPServer]
    
    def list_avail_mcp(self):
        for mcp in self.registry:
            print(mcp,end=f"\n{'--'*20}\n")
    def __str__(self):
        return "RegistryMCP"
