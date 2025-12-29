from mcp_arena.presents.aws import S3MCPServer
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.local_operation import LocalOperationsMCPServer
from mcp_arena.presents.vectordb import VectorDBMCPServer
from mcp_arena.presents.mongo import MongoDBMCPServer
from mcp_arena.presents.notion import NotionMCPServer
from mcp_arena.presents.postgres import PostgresMCPServer
from mcp_arena.presents.slack import SlackMCPServer
from mcp_arena.presents.bitbucket import BitbucketMCPServer
from mcp_arena.presents.confluence import ConfluenceMCPServer
from mcp_arena.presents.docker import DockerMCPServer
from mcp_arena.presents.gitlab import GitLabMCPServer
from mcp_arena.presents.jira import JiraMCPServer
from mcp_arena.presents.redis import RedisMCPServer

class RegistryMCP:
    def __init__(self):
        self.registry = [S3MCPServer, GithubMCPServer, LocalOperationsMCPServer,
                        VectorDBMCPServer, MongoDBMCPServer, NotionMCPServer, PostgresMCPServer,
                        SlackMCPServer, BitbucketMCPServer, ConfluenceMCPServer, DockerMCPServer,
                        GitLabMCPServer, JiraMCPServer, RedisMCPServer]
    
    def list_avail_mcp(self):
        for mcp in self.registry:
            print(mcp,end=f"\n{'--'*20}\n")
    def __str__(self):
        return f"RegistryMCP\n{self.list_avail_mcp()}"
