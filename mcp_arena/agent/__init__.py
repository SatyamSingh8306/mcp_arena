"""
Agent module with SOLID architecture for built-in agents.

This module provides a comprehensive agent system following SOLID principles:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Extensible through interfaces and inheritance
- Liskov Substitution: Implementations can substitute their interfaces
- Interface Segregation: Focused, cohesive interfaces
- Dependency Inversion: Depend on abstractions, not concretions

Available agents:
- ReflectionAgent: Self-improving through reflection
- ReactAgent: Reasoning + Acting pattern
- PlanningAgent: Goal-oriented planning and execution

Usage:
    from agent import create_agent, agent_registry
    
    # Create a simple reflection agent
    agent = create_agent("reflection", memory_type="conversation")
    response = agent.process("Tell me about AI")
    
    # Use the registry for pre-configured agents
    agent = agent_registry.create_from_config("basic_reflection")
    
    # Use a router for automatic agent selection
    from agent.router import create_default_router
    router = create_default_router()
    response = router.process("Help me plan a project")
"""

from .interfaces import (
    IAgent, IAgentState, IAgentBehavior, IAgentMemory, 
    IAgentTool, IAgentFactory, IAgentPolicy
)

from .base import BaseAgent
from .reflection_agent import ReflectionAgent
from .react_agent import ReactAgent
from .planning_agent import PlanningAgent

from .state import (
    BaseAgentState, ReactAgentState, 
    ReflectionAgentState, PlanningAgentState
)

from .memory import (
    SimpleMemory, ConversationMemory, EpisodicMemory, MemoryFactory
)

from .tools import (
    BaseTool, SearchTool, CalculatorTool, FileSystemTool, 
    WebTool, DataAnalysisTool, ToolRegistry, tool_registry
)

from .policies import (
    BasePolicy, SafetyPolicy, ContentFilterPolicy, RateLimitPolicy,
    LoggingPolicy, PrivacyPolicy, ToolUsagePolicy, PolicyChain,
    create_default_policy_chain, create_restricted_policy_chain
)

from .factory import (
    AgentFactory, AgentBuilder, AgentRegistry,
    agent_registry, create_agent, create_reflection_agent,
    create_react_agent, create_planning_agent
)

from .router import (
    AgentRouter, SmartRouter, MultiAgentOrchestrator,
    ConditionalRouter, create_default_router, create_research_router
)

__version__ = "1.0.0"
__author__ = "MCP Arena Team"

# Export main classes and functions for easy access
__all__ = [
    # Interfaces
    "IAgent", "IAgentState", "IAgentBehavior", "IAgentMemory",
    "IAgentTool", "IAgentFactory", "IAgentPolicy",
    
    # Core Agents
    "BaseAgent", "ReflectionAgent", "ReactAgent", "PlanningAgent",
    
    # State Management
    "BaseAgentState", "ReactAgentState", "ReflectionAgentState", "PlanningAgentState",
    
    # Memory Systems
    "SimpleMemory", "ConversationMemory", "EpisodicMemory", "MemoryFactory",
    
    # Tools
    "BaseTool", "SearchTool", "CalculatorTool", "FileSystemTool",
    "WebTool", "DataAnalysisTool", "ToolRegistry", "tool_registry",
    
    # Policies
    "BasePolicy", "SafetyPolicy", "ContentFilterPolicy", "RateLimitPolicy",
    "LoggingPolicy", "PrivacyPolicy", "ToolUsagePolicy", "PolicyChain",
    "create_default_policy_chain", "create_restricted_policy_chain",
    
    # Factory and Registry
    "AgentFactory", "AgentBuilder", "AgentRegistry", "agent_registry",
    "create_agent", "create_reflection_agent", "create_react_agent", "create_planning_agent",
    
    # Routing
    "AgentRouter", "SmartRouter", "MultiAgentOrchestrator",
    "ConditionalRouter", "create_default_router", "create_research_router",
]


# Convenience functions for quick setup
def setup_basic_agent_system(llm=None):
    """Set up a basic agent system with default configuration"""
    from .factory import AgentRegistry
    from .router import create_default_router
    from .policies import create_default_policy_chain
    
    registry = AgentRegistry()
    
    # Configure agents with LLM if provided
    if llm:
        registry.set_default_config("reflection", {"llm": llm})
        registry.set_default_config("react", {"llm": llm})
        registry.set_default_config("planning", {"llm": llm})
    
    # Create router
    router = create_default_router()
    
    return registry, router


def create_agent_with_tools(agent_type: str, tools: list = None, **config):
    """Create an agent with tools automatically added"""
    agent = create_agent(agent_type, **config)
    
    if tools:
        for tool in tools:
            agent.add_tool(tool)
    else:
        # Add default tools
        default_tools = tool_registry.create_default_tools()
        for tool in default_tools:
            agent.add_tool(tool)
    
    return agent


def create_multi_agent_system():
    """Create a multi-agent system with orchestrator"""
    from .router import MultiAgentOrchestrator
    
    orchestrator = MultiAgentOrchestrator()
    
    # Register different agents
    orchestrator.register_agent("thinker", "reflection", {"memory_type": "conversation"})
    orchestrator.register_agent("doer", "react", {"max_steps": 8})
    orchestrator.register_agent("planner", "planning", {"memory_type": "episodic"})
    
    # Add a sample workflow
    orchestrator.add_workflow("complex_task", [
        {"agent": "planner"},
        {"agent": "thinker"},
        {"agent": "doer"}
    ])
    
    return orchestrator