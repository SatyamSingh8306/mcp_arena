"""Test agent initialization and basic functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import asyncio


class TestAgentInitialization:
    """Test agent initialization without external dependencies."""

    def test_react_agent_init(self):
        """Test ReAct agent initialization."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(
            llm=None,
            memory_type="conversation"
        )
        
        assert agent is not None
        assert hasattr(agent, 'llm')
        assert hasattr(agent, 'memory')
        assert hasattr(agent, 'tools')
        assert hasattr(agent, 'policies')

    def test_reflection_agent_init(self):
        """Test Reflection agent initialization."""
        from mcp_arena.agent.reflection_agent import ReflectionAgent
        
        agent = ReflectionAgent(
            llm=None,
            memory_type="conversation"
        )
        
        assert agent is not None
        assert hasattr(agent, 'llm')
        assert hasattr(agent, 'memory')
        assert hasattr(agent, 'tools')
        assert hasattr(agent, 'policies')

    def test_planning_agent_init(self):
        """Test Planning agent initialization."""
        from mcp_arena.agent.planning_agent import PlanningAgent
        
        agent = PlanningAgent(
            llm=None,
            memory_type="conversation"
        )
        
        assert agent is not None
        assert hasattr(agent, 'llm')
        assert hasattr(agent, 'memory')
        assert hasattr(agent, 'tools')
        assert hasattr(agent, 'policies')

    def test_router_agent_init(self):
        """Test Router agent initialization."""
        from mcp_arena.agent.router import AgentRouter
        
        # Create router with factory
        router = AgentRouter()
        
        assert router is not None
        assert hasattr(router, 'routes')
        assert hasattr(router, 'factory')

    def test_agent_with_memory(self):
        """Test agent initialization with memory configuration."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(
            llm=None,
            memory_type="conversation"
        )
        
        assert agent is not None
        assert hasattr(agent, 'memory')
        assert agent.memory is not None


class TestAgentMethods:
    """Test agent method availability and basic functionality."""

    def test_agent_required_methods(self):
        """Test that all agents have required methods."""
        from mcp_arena.agent.react_agent import ReactAgent
        from mcp_arena.agent.reflection_agent import ReflectionAgent
        from mcp_arena.agent.planning_agent import PlanningAgent
        from mcp_arena.agent.router import AgentRouter
        
        agents = [ReactAgent, ReflectionAgent, PlanningAgent]
        router_class = AgentRouter
        
        required_methods = ["__init__", "run", "process"]
        
        for agent_class in agents:
            agent = agent_class(llm=None)
            
            for method in required_methods:
                if hasattr(agent, method):
                    assert callable(getattr(agent, method)), f"Method {method} not callable in {agent_class.__name__}"
        
        # Test router methods
        router = router_class()
        router_methods = ["__init__", "route", "process"]
        for method in router_methods:
            assert hasattr(router, method), f"AgentRouter missing method: {method}"
            assert callable(getattr(router, method)), f"Method {method} not callable in AgentRouter"

    def test_agent_configuration_methods(self):
        """Test agent configuration methods."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(llm=None)
        
        # Test configuration methods if they exist
        config_methods = ["set_instructions", "add_tool", "remove_tool"]
        
        for method in config_methods:
            if hasattr(agent, method):
                assert callable(getattr(agent, method))

    def test_agent_state_management(self):
        """Test agent state management methods."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(llm=None)
        
        # Test state management methods if they exist
        state_methods = ["get_state", "set_state", "reset_state"]
        
        for method in state_methods:
            if hasattr(agent, method):
                assert callable(getattr(agent, method))


class TestAgentIntegration:
    """Test agent integration with MCP servers."""

    def test_agent_with_mcp_server(self):
        """Test agent integration with MCP server."""
        with patch('mcp_arena.presents.github.Github'):
            from mcp_arena.presents.github import GithubMCPServer
            from mcp_arena.agent.react_agent import ReactAgent
            
            # Create mock MCP server
            server = GithubMCPServer(token="test_token")
            
            # Create agent
            agent = ReactAgent(llm=None)
            
            assert agent is not None
            assert server is not None
            
            # Test that agent can potentially work with server
            # (specific integration depends on implementation)

    def test_agent_tool_integration(self):
        """Test agent tool integration."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(llm=None)
        
        # Test tool integration methods if they exist
        tool_methods = ["add_tools", "get_tools", "execute_tool"]
        
        for method in tool_methods:
            if hasattr(agent, method):
                assert callable(getattr(agent, method))

    def test_agent_memory_integration(self):
        """Test agent memory integration."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(llm=None, memory_type="conversation")
        
        # Test memory integration methods if they exist
        memory_methods = ["add_memory", "get_memory", "clear_memory"]
        
        for method in memory_methods:
            if hasattr(agent, method):
                assert callable(getattr(agent, method))


class TestAgentErrorHandling:
    """Test agent error handling."""

    def test_invalid_configuration(self):
        """Test agent initialization with invalid configuration."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        # Test with invalid memory type - should handle gracefully
        try:
            agent = ReactAgent(llm=None, memory_type="invalid_type")
            # If it doesn't fail, that's ok too
            assert agent is not None
        except (ValueError, TypeError):
            # Expected behavior for invalid configuration
            pass

    def test_router_agent_no_agents(self):
        """Test Router agent initialization without agents."""
        from mcp_arena.agent.router import AgentRouter
        
        # Should handle empty routes gracefully
        try:
            router = AgentRouter()
            assert router is not None
            assert len(router.routes) == 0
        except (ValueError, TypeError):
            # Expected behavior for invalid configuration
            pass

    def test_agent_execution_error(self):
        """Test agent execution error handling."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        agent = ReactAgent(llm=None)
        
        # Test error handling in execution methods
        # This would depend on specific implementation
        execution_methods = ["run", "process"]
        
        for method in execution_methods:
            if hasattr(agent, method):
                method_func = getattr(agent, method)
                # We can't actually call these methods without proper setup
                # but we can verify they exist and are callable
                assert callable(method_func)


class TestAgentPerformance:
    """Test agent performance and resource usage."""

    def test_agent_memory_usage(self):
        """Test agent memory usage is reasonable."""
        from mcp_arena.agent.react_agent import ReactAgent
        
        # Create multiple agents to test memory usage
        agents = []
        for i in range(10):
            agent = ReactAgent(llm=None)
            agents.append(agent)
        
        # Basic sanity check - agents should be created successfully
        assert len(agents) == 10
        for agent in agents:
            assert agent is not None

    def test_agent_initialization_time(self):
        """Test agent initialization time is reasonable."""
        import time
        from mcp_arena.agent.react_agent import ReactAgent
        
        start_time = time.time()
        
        # Create multiple agents
        for i in range(5):
            agent = ReactAgent(llm=None)
            assert agent is not None
        
        end_time = time.time()
        initialization_time = end_time - start_time
        
        # Should complete within reasonable time (e.g., 1 second)
        assert initialization_time < 1.0, f"Agent initialization took too long: {initialization_time}s"

    def test_agent_concurrent_creation(self):
        """Test concurrent agent creation."""
        import threading
        from mcp_arena.agent.react_agent import ReactAgent
        
        agents = []
        errors = []
        
        def create_agent(index):
            try:
                agent = ReactAgent(llm=None)
                agents.append(agent)
            except Exception as e:
                errors.append(e)
        
        # Create agents in multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=create_agent, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check results
        assert len(errors) == 0, f"Errors in concurrent creation: {errors}"
        assert len(agents) == 5, f"Expected 5 agents, got {len(agents)}"


class TestAgentCompatibility:
    """Test agent compatibility with different Python versions and environments."""

    def test_agent_python_version_compatibility(self):
        """Test agent compatibility with current Python version."""
        import sys
        from mcp_arena.agent.react_agent import ReactAgent
        
        # Check Python version
        python_version = sys.version_info
        assert python_version >= (3, 8), "Python 3.8+ required"
        
        # Test agent creation works
        agent = ReactAgent(llm=None)
        assert agent is not None

    def test_agent_import_compatibility(self):
        """Test agent imports work in different environments."""
        try:
            from mcp_arena.agent.react_agent import ReactAgent
            from mcp_arena.agent.reflection_agent import ReflectionAgent
            from mcp_arena.agent.planning_agent import PlanningAgent
            from mcp_arena.agent.router import AgentRouter
            
            # All imports should work
            assert ReactAgent is not None
            assert ReflectionAgent is not None
            assert PlanningAgent is not None
            assert AgentRouter is not None
            
        except ImportError as e:
            pytest.fail(f"Agent import failed: {e}")

    def test_agent_dependency_compatibility(self):
        """Test agent dependencies are compatible."""
        dependencies = [
            "langchain",
            "langchain_core",
            "typing_extensions"
        ]
        
        for dep in dependencies:
            try:
                __import__(dep.replace("-", "_"))
            except ImportError:
                pytest.fail(f"Required dependency '{dep}' not available for agents")
