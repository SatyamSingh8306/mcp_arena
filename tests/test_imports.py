"""Test imports and basic availability of all modules and MCP servers."""

import warnings
import pytest
import importlib


class TestImports:
    """Test that all modules can be imported successfully."""

    def test_core_imports(self):
        """Test core mcp_arena imports."""
        import mcp_arena
        from mcp_arena.mcp.server import BaseMCPServer
        from mcp_arena.agent.react_agent import ReactAgent
        from mcp_arena.agent.reflection_agent import ReflectionAgent
        from mcp_arena.agent.planning_agent import PlanningAgent
        from mcp_arena.agent.router import AgentRouter
        
        assert mcp_arena.__version__ is not None
        assert BaseMCPServer is not None
        assert ReactAgent is not None
        assert ReflectionAgent is not None
        assert PlanningAgent is not None
        assert AgentRouter is not None

    @pytest.mark.parametrize("server_name", [
        "github", "gitlab", "bitbucket", "docker", "postgres", 
        "mongo", "redis", "slack", "jira", "notion", "confluence",
        "aws", "local_operation", "vectordb", "mail", "outlook", "whatsapp"
    ])
    def test_mcp_server_imports(self, server_name):
        """Test that all MCP servers can be imported."""
        try:
            module = importlib.import_module(f"mcp_arena.presents.{server_name}")
            assert module is not None
            
            # Check if there's a server class with conventional naming
            server_class_name = f"{server_name.title().replace('_', '')}MCPServer"
            if hasattr(module, server_class_name):
                server_class = getattr(module, server_class_name)
                assert server_class is not None
            else:
                # Try alternative naming
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (isinstance(attr, type) and 
                        attr_name.endswith('MCPServer') and 
                        attr_name != 'BaseMCPServer'):
                        assert attr is not None
                        break
                else:
                    pytest.skip(f"No MCPServer class found in {server_name}")
                    
        except ImportError as e:
            pytest.fail(f"Failed to import mcp_arena.presents.{server_name}: {e}")

    def test_tools_imports(self):
        """Test that tools modules can be imported."""
        tool_modules = [
            "base", "github", "docker", "postgres", "mongo", 
            "redis", "slack", "jira", "notion"
        ]
        
        for tool_name in tool_modules:
            try:
                importlib.import_module(f"mcp_arena.tools.{tool_name}")
            except ImportError as e:
                # Skip if module doesn't exist
                if "No module named" in str(e):
                    continue
                pytest.fail(f"Failed to import mcp_arena.tools.{tool_name}: {e}")

    def test_wrapper_imports(self):
        """Test wrapper modules."""
        try:
            importlib.import_module("mcp_arena.wrapper.langchain_wrapper")
        except ImportError as e:
            pytest.fail(f"Failed to import langchain wrapper: {e}")

    def test_cli_import(self):
        """Test CLI module import."""
        try:
            from mcp_arena.cli import app
            assert app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import CLI: {e}")


class TestDependencies:
    """Test that required dependencies are available."""

    def test_core_dependencies(self):
        """Test core dependencies."""
        dependencies = {
            "mcp": "mcp",
            "python_dotenv": "dotenv",
            "typing_extensions": "typing_extensions",
            "psutil": "psutil",
            "langchain": "langchain",
            "langchain_core": "langchain_core",
            "typer": "typer",
            "rich": "rich"
        }
        
        for dep_name, import_name in dependencies.items():
            try:
                importlib.import_module(import_name)
            except ImportError:
                pytest.fail(f"Core dependency '{dep_name}' not available")

    def test_communication_dependencies(self):
        """Test communication service dependencies."""
        dependencies = {
            "google.auth": "gmail",
            "msal": "outlook", 
            "slack_sdk": "slack",
            "twilio": "whatsapp"
        }
        
        for module, service in dependencies.items():
            try:
                importlib.import_module(module)
            except ImportError:
                warnings.warn(f"Communication dependency '{module}' for {service} not available")

    def test_database_dependencies(self):
        """Test database dependencies."""
        dependencies = {
            "psycopg2": "postgres",
            "pymongo": "mongo",
            "redis": "redis",
            "docker": "docker"
        }
        
        for module, service in dependencies.items():
            try:
                importlib.import_module(module)
            except ImportError:
                warnings.warn(f"Database dependency '{module}' for {service} not available")

    def test_cloud_dependencies(self):
        """Test cloud service dependencies."""
        dependencies = {
            "boto3": "aws",
            "github": "github",
            "notion_client": "notion"
        }
        
        for module, service in dependencies.items():
            try:
                importlib.import_module(module)
            except ImportError:
                warnings.warn(f"Cloud dependency '{module}' for {service} not available")


class TestModuleStructure:
    """Test module structure and expected attributes."""

    def test_mcp_server_base_class(self):
        """Test BaseMCPServer has required methods."""
        from mcp_arena.mcp.server import BaseMCPServer
        
        required_methods = [
            "_register_tools",
            "get_registered_tools", 
            "run",
            "invoke"
        ]
        
        for method in required_methods:
            assert hasattr(BaseMCPServer, method), f"BaseMCPServer missing method: {method}"

    def test_agent_base_classes(self):
        """Test agent base classes have required methods."""
        from mcp_arena.agent.react_agent import ReactAgent
        from mcp_arena.agent.reflection_agent import ReflectionAgent
        
        agent_classes = [ReactAgent, ReflectionAgent]
        
        for agent_class in agent_classes:
            # Check for common agent methods
            common_methods = ["__init__", "run", "process"]
            for method in common_methods:
                assert hasattr(agent_class, method), f"{agent_class.__name__} missing method: {method}"
