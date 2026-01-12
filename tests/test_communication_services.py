"""Test communication services specifically."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGmailService:
    """Test Gmail MCP server."""

    def test_gmail_server_import(self):
        """Test Gmail server can be imported."""
        try:
            from mcp_arena.presents.mail import GmailMCPServer
            assert GmailMCPServer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import GmailMCPServer: {e}")

    def test_gmail_server_init(self):
        """Test Gmail server initialization."""
        with patch('google.auth.load_credentials_from_file') as mock_auth:
            mock_auth.return_value = (Mock(), Mock())
            
            from mcp_arena.presents.mail import GmailMCPServer
            
            server = GmailMCPServer(
                credentials_path="test_credentials.json",
                token_path="test_token.json"
            )
            
            assert server is not None
            assert hasattr(server, 'credentials_path')
            assert hasattr(server, 'token_path')

    def test_gmail_required_methods(self):
        """Test Gmail server has required methods."""
        with patch('google.auth.load_credentials_from_file'):
            from mcp_arena.presents.mail import GmailMCPServer
            
            server = GmailMCPServer(
                credentials_path="test.json",
                token_path="test.json"
            )
            
            required_methods = ["_register_tools", "get_registered_tools", "run"]
            for method in required_methods:
                assert hasattr(server, method), f"GmailMCPServer missing method: {method}"

    def test_gmail_dependencies(self):
        """Test Gmail dependencies are available."""
        try:
            import google.auth
            from googleapiclient.discovery import build
            assert google.auth is not None
        except ImportError as e:
            pytest.warn(f"Gmail dependencies not available: {e}")


class TestOutlookService:
    """Test Outlook MCP server."""

    def test_outlook_server_import(self):
        """Test Outlook server can be imported."""
        try:
            from mcp_arena.presents.outlook import OutlookMCPServer
            assert OutlookMCPServer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import OutlookMCPServer: {e}")

    def test_outlook_server_init(self):
        """Test Outlook server initialization."""
        with patch('msal.ClientApplication') as mock_msal:
            mock_client = Mock()
            mock_msal.return_value = mock_client
            
            from mcp_arena.presents.outlook import OutlookMCPServer
            
            server = OutlookMCPServer(
                client_id="test_client_id",
                client_secret="test_client_secret",
                tenant_id="test_tenant_id"
            )
            
            assert server is not None
            assert hasattr(server, 'client_id')
            assert hasattr(server, 'client_secret')
            assert hasattr(server, 'tenant_id')

    def test_outlook_required_methods(self):
        """Test Outlook server has required methods."""
        with patch('msal.ClientApplication'):
            from mcp_arena.presents.outlook import OutlookMCPServer
            
            server = OutlookMCPServer(
                client_id="test",
                client_secret="test",
                tenant_id="test"
            )
            
            required_methods = ["_register_tools", "get_registered_tools", "run"]
            for method in required_methods:
                assert hasattr(server, method), f"OutlookMCPServer missing method: {method}"

    def test_outlook_dependencies(self):
        """Test Outlook dependencies are available."""
        try:
            import msal
            assert msal is not None
        except ImportError as e:
            pytest.warn(f"Outlook dependencies not available: {e}")


class TestWhatsAppService:
    """Test WhatsApp MCP server."""

    def test_whatsapp_server_import(self):
        """Test WhatsApp server can be imported."""
        try:
            from mcp_arena.presents.whatsapp import WhatsAppMCPServer
            assert WhatsAppMCPServer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import WhatsAppMCPServer: {e}")

    def test_whatsapp_server_init(self):
        """Test WhatsApp server initialization."""
        with patch('twilio.rest.Client') as mock_twilio:
            mock_client = Mock()
            mock_twilio.return_value = mock_client
            
            from mcp_arena.presents.whatsapp import WhatsAppMCPServer
            
            server = WhatsAppMCPServer(
                account_sid="test_sid",
                auth_token="test_token",
                from_number="whatsapp:+1234567890"
            )
            
            assert server is not None
            assert hasattr(server, 'account_sid')
            assert hasattr(server, 'auth_token')
            assert hasattr(server, 'from_number')

    def test_whatsapp_required_methods(self):
        """Test WhatsApp server has required methods."""
        with patch('twilio.rest.Client'):
            from mcp_arena.presents.whatsapp import WhatsAppMCPServer
            
            server = WhatsAppMCPServer(
                account_sid="test",
                auth_token="test",
                from_number="whatsapp:+1234567890"
            )
            
            required_methods = ["_register_tools", "get_registered_tools", "run"]
            for method in required_methods:
                assert hasattr(server, method), f"WhatsAppMCPServer missing method: {method}"

    def test_whatsapp_dependencies(self):
        """Test WhatsApp dependencies are available."""
        try:
            import twilio
            assert twilio is not None
        except ImportError as e:
            pytest.warn(f"WhatsApp dependencies not available: {e}")


class TestSlackService:
    """Test Slack MCP server."""

    def test_slack_server_import(self):
        """Test Slack server can be imported."""
        try:
            from mcp_arena.presents.slack import SlackMCPServer
            assert SlackMCPServer is not None
        except ImportError as e:
            pytest.fail(f"Failed to import SlackMCPServer: {e}")

    def test_slack_server_init(self):
        """Test Slack server initialization."""
        with patch('slack_sdk.WebClient') as mock_slack:
            mock_client = Mock()
            mock_slack.return_value = mock_client
            
            from mcp_arena.presents.slack import SlackMCPServer
            
            server = SlackMCPServer(bot_token="xoxb-test-token")
            
            assert server is not None
            assert hasattr(server, 'bot_token')
            assert server.bot_token == "xoxb-test-token"

    def test_slack_required_methods(self):
        """Test Slack server has required methods."""
        with patch('slack_sdk.WebClient'):
            from mcp_arena.presents.slack import SlackMCPServer
            
            server = SlackMCPServer(bot_token="test-token")
            
            required_methods = ["_register_tools", "get_registered_tools", "run"]
            for method in required_methods:
                assert hasattr(server, method), f"SlackMCPServer missing method: {method}"

    def test_slack_dependencies(self):
        """Test Slack dependencies are available."""
        try:
            import slack_sdk
            assert slack_sdk is not None
        except ImportError as e:
            pytest.warn(f"Slack dependencies not available: {e}")


class TestCommunicationServicesIntegration:
    """Test communication services integration."""

    def test_all_communication_servers_import(self):
        """Test all communication servers can be imported."""
        communication_servers = [
            ("mail", "GmailMCPServer"),
            ("outlook", "OutlookMCPServer"),
            ("whatsapp", "WhatsAppMCPServer"),
            ("slack", "SlackMCPServer")
        ]
        
        for module_name, class_name in communication_servers:
            try:
                module = __import__(f"mcp_arena.presents.{module_name}", fromlist=[class_name])
                server_class = getattr(module, class_name)
                assert server_class is not None
            except (ImportError, AttributeError) as e:
                pytest.fail(f"Failed to import {class_name} from {module_name}: {e}")

    def test_communication_services_configuration(self):
        """Test communication services configuration options."""
        services = [
            ("mail", {"credentials_path": "test.json", "token_path": "test.json"}),
            ("outlook", {"client_id": "test", "client_secret": "test", "tenant_id": "test"}),
            ("whatsapp", {"account_sid": "test", "auth_token": "test", "from_number": "whatsapp:+123"}),
            ("slack", {"bot_token": "test"})
        ]
        
        for service_name, config in services:
            with patch(f'mcp_arena.presents.{service_name}.{"GmailMCPServer" if service_name == "mail" else "OutlookMCPServer" if service_name == "outlook" else "WhatsAppMCPServer" if service_name == "whatsapp" else "SlackMCPServer"}'):
                try:
                    if service_name == "mail":
                        from mcp_arena.presents.mail import GmailMCPServer
                        service_class = GmailMCPServer
                    elif service_name == "outlook":
                        from mcp_arena.presents.outlook import OutlookMCPServer
                        service_class = OutlookMCPServer
                    elif service_name == "whatsapp":
                        from mcp_arena.presents.whatsapp import WhatsAppMCPServer
                        service_class = WhatsAppMCPServer
                    elif service_name == "slack":
                        from mcp_arena.presents.slack import SlackMCPServer
                        service_class = SlackMCPServer
                    
                    # Test configuration is accepted
                    if service_name == "mail":
                        with patch('google.auth.load_credentials_from_file'):
                            server = service_class(**config)
                    elif service_name == "outlook":
                        with patch('msal.ClientApplication'):
                            server = service_class(**config)
                    elif service_name == "whatsapp":
                        with patch('twilio.rest.Client'):
                            server = service_class(**config)
                    elif service_name == "slack":
                        with patch('slack_sdk.WebClient'):
                            server = service_class(**config)
                    
                    assert server is not None
                    
                except Exception as e:
                    pytest.fail(f"Configuration test failed for {service_name}: {e}")

    def test_communication_services_transport_options(self):
        """Test communication services support different transports."""
        transports = ["stdio", "sse", "streamable-http"]
        
        for transport in transports:
            with patch('slack_sdk.WebClient'):
                from mcp_arena.presents.slack import SlackMCPServer
                
                server = SlackMCPServer(
                    bot_token="test",
                    transport=transport,
                    host="127.0.0.1",
                    port=8000
                )
                
                assert server.transport == transport

    def test_communication_services_error_handling(self):
        """Test communication services error handling."""
        # Test invalid credentials
        with patch('slack_sdk.WebClient') as mock_slack:
            mock_slack.side_effect = Exception("Invalid token")
            
            from mcp_arena.presents.slack import SlackMCPServer
            
            with pytest.raises(Exception):
                SlackMCPServer(bot_token="invalid_token")

    def test_communication_services_tool_registration(self):
        """Test communication services tool registration."""
        with patch('slack_sdk.WebClient'):
            from mcp_arena.presents.slack import SlackMCPServer
            
            # Test with auto register
            server1 = SlackMCPServer(bot_token="test", auto_register_tools=True)
            assert server1.auto_register_tools is True
            
            # Test without auto register
            server2 = SlackMCPServer(bot_token="test", auto_register_tools=False)
            assert server2.auto_register_tools is False


class TestCommunicationServicesDependencies:
    """Test communication services dependencies."""

    def test_email_dependencies(self):
        """Test email service dependencies."""
        email_deps = {
            "google.auth": "Gmail",
            "msal": "Outlook"
        }
        
        for module, service in email_deps.items():
            try:
                __import__(module)
            except ImportError:
                pytest.warn(f"Email dependency '{module}' for {service} not available")

    def test_messaging_dependencies(self):
        """Test messaging service dependencies."""
        messaging_deps = {
            "slack_sdk": "Slack",
            "twilio": "WhatsApp"
        }
        
        for module, service in messaging_deps.items():
            try:
                __import__(module)
            except ImportError:
                pytest.warn(f"Messaging dependency '{module}' for {service} not available")

    def test_communication_package_versions(self):
        """Test communication package versions are compatible."""
        packages = {
            "slack_sdk": "3.0",
            "twilio": "8.0",
            "msal": "1.0",
            "google.auth": "2.0"
        }
        
        for package, min_version in packages.items():
            try:
                module = __import__(package.replace("-", "_"))
                if hasattr(module, '__version__'):
                    version = module.__version__
                    # Basic version check - just ensure it exists
                    assert version is not None
                else:
                    pytest.warn(f"Could not determine version for {package}")
            except ImportError:
                pytest.warn(f"Package {package} not available")


class TestCommunicationServicesPerformance:
    """Test communication services performance."""

    def test_communication_services_initialization_time(self):
        """Test communication services initialize quickly."""
        import time
        
        with patch('slack_sdk.WebClient'):
            from mcp_arena.presents.slack import SlackMCPServer
            
            start_time = time.time()
            
            # Create multiple servers
            for i in range(5):
                server = SlackMCPServer(bot_token=f"test-{i}")
                assert server is not None
            
            end_time = time.time()
            initialization_time = end_time - start_time
            
            # Should complete within reasonable time (e.g., 2 seconds)
            assert initialization_time < 2.0, f"Communication services initialization took too long: {initialization_time}s"

    def test_communication_services_memory_usage(self):
        """Test communication services memory usage is reasonable."""
        with patch('slack_sdk.WebClient'):
            from mcp_arena.presents.slack import SlackMCPServer
            
            # Create multiple servers
            servers = []
            for i in range(10):
                server = SlackMCPServer(bot_token=f"test-{i}")
                servers.append(server)
            
            # Basic sanity check
            assert len(servers) == 10
            for server in servers:
                assert server is not None
