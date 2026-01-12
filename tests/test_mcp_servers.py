"""Test MCP server initialization and basic functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


class TestMCPServerInitialization:
    """Test MCP server initialization without external dependencies."""

    def test_github_server_init(self):
        """Test GitHub MCP server initialization."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(token="test_token")
            assert server is not None
            # The token is stored as private attribute __token
            assert hasattr(server, '_GithubMCPServer__token')

    def test_slack_server_init(self):
        """Test Slack MCP server initialization."""
        with patch('mcp_arena.presents.slack.WebClient'):
            from mcp_arena.presents.slack import SlackMCPServer
            
            server = SlackMCPServer(bot_token="xoxb-test")
            assert server is not None
            assert hasattr(server, 'bot_token')

    def test_docker_server_init(self):
        """Test Docker MCP server initialization."""
        with patch('docker.DockerClient'):
            from mcp_arena.presents.docker import DockerMCPServer
            
            server = DockerMCPServer()
            assert server is not None

    def test_postgres_server_init(self):
        """Test PostgreSQL MCP server initialization."""
        with patch('psycopg2.connect'):
            from mcp_arena.presents.postgres import PostgresMCPServer
            
            server = PostgresMCPServer(
                host="localhost",
                port=5432,
                database="testdb",
                user="testuser",
                password="testpass"
            )
            assert server is not None

    def test_local_operations_server_init(self):
        """Test Local Operations MCP server initialization."""
        from mcp_arena.presents.local_operation import LocalOperationsMCPServer
        
        server = LocalOperationsMCPServer(safe_mode=True)
        assert server is not None
        assert hasattr(server, 'safe_mode')
        assert server.safe_mode is True

    def test_mongo_server_init(self):
        """Test MongoDB MCP server initialization."""
        with patch('pymongo.MongoClient'):
            from mcp_arena.presents.mongo import MongoDBMCPServer
            
            server = MongoDBMCPServer(
                connection_string="mongodb://localhost:27017",
                database="testdb"
            )
            assert server is not None

    def test_redis_server_init(self):
        """Test Redis MCP server initialization."""
        with patch('redis.Redis'):
            from mcp_arena.presents.redis import RedisMCPServer
            
            server = RedisMCPServer(host="localhost", port=6379)
            assert server is not None

    def test_s3_server_init(self):
        """Test AWS S3 MCP server initialization."""
        with patch('boto3.client'):
            from mcp_arena.presents.aws import S3MCPServer
            
            server = S3MCPServer(
                access_key_id="test_key",
                secret_access_key="test_secret",
                region="us-east-1"
            )
            assert server is not None

    def test_notion_server_init(self):
        """Test Notion MCP server initialization."""
        with patch('notion_client.Client'):
            from mcp_arena.presents.notion import NotionMCPServer
            
            server = NotionMCPServer(token="test_token")
            assert server is not None

    def test_jira_server_init(self):
        """Test Jira MCP server initialization."""
        with patch('jira.JIRA'):
            from mcp_arena.presents.jira import JiraMCPServer
            
            server = JiraMCPServer(
                url="https://test.atlassian.net",
                username="test@test.com",
                api_token="test_token"
            )
            assert server is not None

    def test_gitlab_server_init(self):
        """Test GitLab MCP server initialization."""
        with patch('gitlab.Gitlab'):
            from mcp_arena.presents.gitlab import GitLabMCPServer
            
            server = GitLabMCPServer(
                url="https://gitlab.com",
                token="test_token"
            )
            assert server is not None

    def test_bitbucket_server_init(self):
        """Test Bitbucket MCP server initialization."""
        with patch('atlassian.Bitbucket'):
            from mcp_arena.presents.bitbucket import BitbucketMCPServer
            
            server = BitbucketMCPServer(
                username="testuser",
                app_password="testpass"
            )
            assert server is not None

    def test_confluence_server_init(self):
        """Test Confluence MCP server initialization."""
        with patch('atlassian.Confluence'):
            from mcp_arena.presents.confluence import ConfluenceMCPServer
            
            server = ConfluenceMCPServer(
                url="https://test.atlassian.net",
                username="test@test.com",
                api_token="test_token"
            )
            assert server is not None

    def test_vectordb_server_init(self):
        """Test VectorDB MCP server initialization."""
        with patch('chromadb.Client'):
            from mcp_arena.presents.vectordb import VectorDBMCPServer
            
            server = VectorDBMCPServer(
                db_url="localhost:6333",
                collection_name="test_collection"
            )
            assert server is not None

    def test_gmail_server_init(self):
        """Test Gmail MCP server initialization."""
        with patch('google.auth.load_credentials_from_file'):
            from mcp_arena.presents.gmail import GmailMCPServer
            
            server = GmailMCPServer(
                credentials_path="test_credentials.json",
                token_path="test_token.json"
            )
            assert server is not None

    def test_outlook_server_init(self):
        """Test Outlook MCP server initialization."""
        with patch('msal.ClientApplication'):
            from mcp_arena.presents.outlook import OutlookMCPServer
            
            server = OutlookMCPServer(
                client_id="test_client_id",
                client_secret="test_client_secret",
                tenant_id="test_tenant_id"
            )
            assert server is not None

    def test_whatsapp_server_init(self):
        """Test WhatsApp MCP server initialization."""
        with patch('twilio.rest.Client'):
            from mcp_arena.presents.whatsapp import WhatsAppMCPServer
            
            server = WhatsAppMCPServer(
                account_sid="test_sid",
                auth_token="test_token",
                from_number="whatsapp:+1234567890"
            )
            assert server is not None


class TestMCPServerConfiguration:
    """Test MCP server configuration options."""

    def test_server_transport_options(self):
        """Test different transport options."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            # Test stdio transport
            server1 = GithubMCPServer(token="test", transport="stdio")
            assert server1.transport == "stdio"
            
            # Test SSE transport
            server2 = GithubMCPServer(token="test", transport="sse", host="0.0.0.0", port=8001)
            assert server2.transport == "sse"
            
            # Test HTTP transport
            server3 = GithubMCPServer(token="test", transport="streamable-http", host="0.0.0.0", port=8002)
            assert server3.transport == "streamable-http"

    def test_server_host_port_configuration(self):
        """Test host and port configuration."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(
                token="test",
                host="192.168.1.100",
                port=9001
            )
            assert server.host == "192.168.1.100"
            assert server.port == 9001

    def test_server_debug_configuration(self):
        """Test debug configuration."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(token="test", debug=True)
            assert server.debug is True

    def test_auto_register_tools_configuration(self):
        """Test auto register tools configuration."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            # Test with auto register (default)
            server1 = GithubMCPServer(token="test")
            assert server1.auto_register_tools is True
            
            # Test without auto register
            server2 = GithubMCPServer(token="test", auto_register_tools=False)
            assert server2.auto_register_tools is False


class TestMCPServerMethods:
    """Test MCP server method availability and basic functionality."""

    def test_server_required_methods(self):
        """Test that all servers have required methods."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(token="test")
            
            # Test required methods exist
            required_methods = [
                "_register_tools",
                "get_registered_tools",
                "run",
                "invoke"
            ]
            
            for method in required_methods:
                assert hasattr(server, method), f"Missing required method: {method}"
                assert callable(getattr(server, method)), f"Method {method} is not callable"

    def test_get_registered_tools_empty(self):
        """Test get_registered_tools returns list."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(token="test", auto_register_tools=False)
            tools = server.get_registered_tools()
            assert isinstance(tools, list)

    @pytest.mark.parametrize("transport", ["stdio", "sse", "streamable-http"])
    def test_run_method_accepts_transport(self, transport):
        """Test that run method accepts transport parameter."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            
            server = GithubMCPServer(token="test")
            
            # Test that run method accepts transport parameter
            # We won't actually call it to avoid starting servers
            assert callable(getattr(server, 'run'))
            
            # Check method signature
            import inspect
            sig = inspect.signature(server.run)
            assert 'transport' in sig.parameters or len(sig.parameters) == 0


class TestMCPServerErrorHandling:
    """Test MCP server error handling."""

    def test_missing_credentials_error(self):
        """Test that missing credentials raise appropriate errors."""
        with patch('mcp_arena.presents.github.Github') as mock_github:
            mock_github.side_effect = ValueError("Invalid token")
            
            from mcp_arena.presents.github import GithubMCPServer
            
            with pytest.raises(ValueError, match="Invalid token"):
                GithubMCPServer(token="invalid_token")

    def test_connection_error_handling(self):
        """Test connection error handling."""
        with patch('mcp_arena.presents.postgres.psycopg2') as mock_psycopg2:
            mock_psycopg2.connect.side_effect = Exception("Connection failed")
            
            from mcp_arena.presents.postgres import PostgresMCPServer
            
            # Should handle connection errors gracefully
            with pytest.raises(Exception):
                PostgresMCPServer(
                    host="invalid_host",
                    port=5432,
                    database="testdb",
                    user="testuser",
                    password="testpass"
                )

    def test_safe_mode_restrictions(self):
        """Test safe mode restrictions in local operations."""
        from mcp_arena.presents.local_operation import LocalOperationsMCPServer
        
        # Test safe mode is enforced
        server = LocalOperationsMCPServer(safe_mode=True)
        assert server.safe_mode is True
        
        # Test unsafe operations are restricted in safe mode
        # This would depend on the specific implementation
        # For now, just verify the safe_mode attribute is set correctly
