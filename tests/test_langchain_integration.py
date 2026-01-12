"""Test the LangChain integration wrapper."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from mcp_arena.wrapper.langchain_integration import MCPLangChainIntegration, AsyncMCPLangChainIntegration


class TestMCPLangChainIntegration:
    """Test the LangChain integration wrapper."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock language model."""
        llm = Mock()
        return llm
    
    @pytest.fixture
    def integration(self, mock_llm):
        """Create integration instance."""
        return MCPLangChainIntegration(mock_llm)
    
    def test_init(self, mock_llm):
        """Test integration initialization."""
        integration = MCPLangChainIntegration(mock_llm)
        
        assert integration.llm == mock_llm
        assert integration.default_transport == "stdio"
        assert integration.servers == {}
        assert integration.agent is None
        assert integration.tools == []
    
    def test_add_mcp_server(self, integration):
        """Test adding MCP server."""
        mock_server = Mock()
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8000
        mock_server.debug = False
        mock_server.auto_register_tools = True
        mock_server.__class__.__name__ = "TestServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.test"
        
        result = integration.add_mcp_server("test", mock_server)
        
        assert result is integration  # Returns self for chaining
        assert "test" in integration.servers
        assert integration.servers["test"] == mock_server
    
    @patch('mcp_arena.presents.github.GithubMCPServer')
    def test_add_github_server(self, mock_github_class, integration):
        """Test adding GitHub server."""
        mock_server = Mock()
        mock_github_class.return_value = mock_server
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8001
        mock_server.debug = False
        mock_server.auto_register_tools = True
        mock_server.__class__.__name__ = "GithubMCPServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.github"
        
        result = integration.add_github_server("test_token")
        
        assert result is integration
        assert "github" in integration.servers
        mock_github_class.assert_called_once_with(token="test_token")
    
    @patch('mcp_arena.presents.slack.SlackMCPServer')
    def test_add_slack_server(self, mock_slack_class, integration):
        """Test adding Slack server."""
        mock_server = Mock()
        mock_slack_class.return_value = mock_server
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8002
        mock_server.debug = False
        mock_server.auto_register_tools = True
        mock_server.__class__.__name__ = "SlackMCPServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.slack"
        
        result = integration.add_slack_server("xoxb-test-token")
        
        assert result is integration
        assert "slack" in integration.servers
        mock_slack_class.assert_called_once_with(bot_token="xoxb-test-token")
    
    @patch('mcp_arena.presents.mail.GmailMCPServer')
    def test_add_gmail_server(self, mock_gmail_class, integration):
        """Test adding Gmail server."""
        mock_server = Mock()
        mock_gmail_class.return_value = mock_server
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8003
        mock_server.debug = False
        mock_server.auto_register_tools = True
        mock_server.__class__.__name__ = "GmailMCPServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.mail"
        
        result = integration.add_gmail_server(
            credentials_path="creds.json",
            token_path="token.json"
        )
        
        assert result is integration
        assert "gmail" in integration.servers
        mock_gmail_class.assert_called_once_with(
            credentials_path="creds.json",
            token_path="token.json"
        )
    
    def test_create_server_script(self, integration):
        """Test server script creation."""
        mock_server = Mock()
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8000
        mock_server.debug = False
        mock_server.auto_register_tools = True
        mock_server.__class__.__name__ = "TestServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.test"
        
        script = integration._create_server_script(mock_server, "test")
        
        assert "TestServer" in script
        assert "transport='stdio'" in script
        assert "host='127.0.0.1'" in script
        assert "port=8000" in script
    
    @pytest.mark.asyncio
    async def test_create_client_empty(self, integration):
        """Test client creation with no servers."""
        client = await integration.create_client()
        
        assert client is not None
        assert len(client.servers) == 0
    
    @pytest.mark.asyncio
    async def test_create_client_with_stdio_server(self, integration):
        """Test client creation with stdio server."""
        mock_server = Mock()
        mock_server.transport = "stdio"
        mock_server.host = "127.0.0.1"
        mock_server.port = 8000
        mock_server.__class__.__name__ = "TestServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.test"
        
        integration.add_mcp_server("test", mock_server)
        
        # Mock the subprocess process
        with patch('subprocess.Popen') as mock_popen:
            mock_process = Mock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process
            
            client = await integration.create_client()
            
            assert "test" in client.servers
            assert client.servers["test"]["transport"] == "stdio"
    
    @pytest.mark.asyncio
    async def test_create_client_with_http_server(self, integration):
        """Test client creation with HTTP server."""
        mock_server = Mock()
        mock_server.transport = "sse"
        mock_server.host = "0.0.0.0"
        mock_server.port = 8000
        mock_server.__class__.__name__ = "TestServer"
        mock_server.__class__.__module__ = "mcp_arena.presents.test"
        
        integration.add_mcp_server("test", mock_server)
        
        client = await integration.create_client()
        
        assert "test" in client.servers
        assert client.servers["test"]["transport"] == "sse"
        assert client.servers["test"]["url"] == "http://0.0.0.0:8000/sse"
    
    @pytest.mark.asyncio
    async def test_invoke_without_initialization(self, integration):
        """Test that invoke raises error when not initialized."""
        with pytest.raises(RuntimeError, match="Integration not initialized"):
            await integration.invoke("test message")
    
    @pytest.mark.asyncio
    async def test_shutdown(self, integration):
        """Test shutdown process."""
        # Add a mock server process
        mock_process = Mock()
        integration.server_processes["test"] = mock_process
        
        await integration.shutdown()
        
        mock_process.terminate.assert_called_once()


class TestAsyncMCPLangChainIntegration:
    """Test the async context manager version."""
    
    @pytest.fixture
    def mock_llm(self):
        """Mock language model."""
        return Mock()
    
    @pytest.mark.asyncio
    async def test_context_manager(self, mock_llm):
        """Test async context manager functionality."""
        with patch.object(AsyncMCPLangChainIntegration, 'initialize') as mock_init, \
             patch.object(AsyncMCPLangChainIntegration, 'shutdown') as mock_shutdown:
            
            async with AsyncMCPLangChainIntegration(mock_llm) as integration:
                assert integration is not None
                mock_init.assert_called_once()
            
            mock_shutdown.assert_called_once()


class TestIntegrationExamples:
    """Test integration examples and convenience functions."""
    
    @pytest.mark.asyncio
    @patch('mcp_arena.wrapper.langchain_integration.AsyncMCPLangChainIntegration')
    @patch('mcp_arena.presents.github.GithubMCPServer')
    async def test_create_github_agent(self, mock_github_class, mock_integration_class, mock_llm):
        """Test the convenience function for GitHub agent."""
        from mcp_arena.wrapper.langchain_integration import create_github_agent
        
        mock_integration = AsyncMock()
        mock_integration_class.return_value = mock_integration
        mock_llm = Mock()
        
        result = await create_github_agent("test_token", mock_llm)
        
        assert result == mock_integration
        mock_integration_class.assert_called_once_with(mock_llm)
        mock_integration.add_github_server.assert_called_once_with("test_token")


if __name__ == "__main__":
    pytest.main([__file__])
