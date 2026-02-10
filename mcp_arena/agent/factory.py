from typing import Any, Dict, List, Type, Optional

from cv2 import sort
from .interfaces import IAgent, IAgentFactory, IAgentTool, IAgentMemory, IAgentPolicy
from .reflection_agent import ReflectionAgent
from .react_agent import ReactAgent
from .planning_agent import PlanningAgent
from .memory import MemoryFactory
from .tools import tool_registry


class AgentFactory(IAgentFactory):
    """Factory for creating different types of agents"""
    
    def __init__(self):
        self._agent_types: Dict[str, Type[IAgent]] = {}
        self._default_config: Dict[str, Dict[str, Any]] = {}
        
        # Register built-in agent types
        self._register_builtin_agents()
    
    def create_agent(self, agent_type: str, config: Dict[str, Any] = None) -> IAgent:
        """Create an agent instance"""
        if agent_type not in self._agent_types:
            raise ValueError(f"Unknown agent type: {agent_type}")
        
        # Merge with default config
        final_config = self._default_config.get(agent_type, {}).copy()
        if config:
            final_config.update(config)
        
        # Create agent instance
        agent_class = self._agent_types[agent_type]
        agent = agent_class(**final_config)
        
        # Initialize if possible
        if hasattr(agent, 'initialize'):
            agent.initialize(final_config)
        
        return agent
    
    def register_agent_type(self, agent_type: str, agent_class: Type[IAgent]) -> None:
        """Register a new agent type"""
        self._agent_types[agent_type] = agent_class
    
    def set_default_config(self, agent_type: str, config: Dict[str, Any]) -> None:
        """Set default configuration for an agent type"""
        self._default_config[agent_type] = config
    

        def list_agent_types(
        self,
        filter_prefix: Optional[str] = None,
        sort: bool = False
    ) -> List[str]:
         """
        List all registered agent types with optional filtering and sorting.

        :param filter_prefix: Only include agent types starting with this prefix
        :param sort: Whether to sort agent types alphabetically
        """
        agent_types = list(self._agent_types.keys())

        if filter_prefix:
            agent_types = [
                a for a in agent_types
                if a.startswith(filter_prefix)
            ]

        if sort:
            agent_types.sort()

        return agent_types


    
    def _register_builtin_agents(self) -> None:
        """Register built-in agent types"""
        self.register_agent_type("reflection", ReflectionAgent)
        self.register_agent_type("react", ReactAgent)
        self.register_agent_type("planning", PlanningAgent)
        
        # Set default configurations
        self._default_config["reflection"] = {
            "memory_type": "conversation",
            "max_reflections": 3
        }
        
        self._default_config["react"] = {
            "memory_type": "conversation",
            "max_steps": 10
        }
        
        self._default_config["planning"] = {
            "memory_type": "episodic"
        }


class AgentBuilder:
    """Builder pattern for creating configured agents"""
    
    def __init__(self, agent_type: str, factory: AgentFactory = None):
        self.agent_type = agent_type
        self.factory = factory or AgentFactory()
        self.config: Dict[str, Any] = {}
        self.tools: List[IAgentTool] = []
        self.memory_type: Optional[str] = None
        self.policies: List[IAgentPolicy] = []
    
    def with_config(self, **kwargs) -> 'AgentBuilder':
        """Add configuration parameters"""
        self.config.update(kwargs)
        return self
    
    def with_tool(self, tool: IAgentTool) -> 'AgentBuilder':
        """Add a tool to the agent"""
        self.tools.append(tool)
        return self
    
    def with_tools(self, tools: List[IAgentTool]) -> 'AgentBuilder':
        """Add multiple tools to the agent"""
        self.tools.extend(tools)
        return self.with_config(tools=tools)
    
    def with_memory(self, memory_type: str, **memory_config) -> 'AgentBuilder':
        """Set memory type and configuration"""
        self.memory_type = memory_type
        if memory_config:
            self.config.update(memory_config)
        return self
    
    def with_policy(self, policy: IAgentPolicy) -> 'AgentBuilder':
        """Add a policy to the agent"""
        self.policies.append(policy)
        return self
    
    def with_llm(self, llm) -> 'AgentBuilder':
        """Set the LLM for the agent"""
        return self.with_config(llm=llm)
    
    def build(self) -> IAgent:
        """Build the configured agent"""
        # Set memory type if specified
        if self.memory_type:
            self.config["memory_type"] = self.memory_type
        
        # Create the agent
        agent = self.factory.create_agent(self.agent_type, self.config)
        
        # Add tools
        for tool in self.tools:
            agent.add_tool(tool)
        
        # Add policies
        for policy in self.policies:
            if hasattr(agent, 'add_policy'):
                agent.add_policy(policy)
        
        return agent


class AgentRegistry:
    """Registry for managing agent configurations and instances"""
    
    def __init__(self):
        self.factory = AgentFactory()
        self._named_configs: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, IAgent] = {}
    
    def register_config(self, name: str, agent_type: str, config: Dict[str, Any]) -> None:
        """Register a named agent configuration"""
        self._named_configs[name] = {
            "agent_type": agent_type,
            "config": config
        }
    
    def create_from_config(self, name: str) -> IAgent:
        """Create an agent from a registered configuration"""
        if name not in self._named_configs:
            raise ValueError(f"No configuration registered for: {name}")
        
        config_data = self._named_configs[name]
        agent = self.factory.create_agent(
            config_data["agent_type"], 
            config_data["config"]
        )
        
        self._instances[name] = agent
        return agent
    
    def get_instance(self, name: str) -> Optional[IAgent]:
        """Get an existing agent instance"""
        return self._instances.get(name)
    
    def list_configs(self) -> List[str]:
        """List all registered configuration names"""
        return list(self._named_configs.keys())
    
    def create_builder(self, agent_type: str) -> AgentBuilder:
        """Create an AgentBuilder for the specified type"""
        return AgentBuilder(agent_type, self.factory)
    
    def setup_default_configs(self) -> None:
        """Set up default agent configurations"""
        # Basic reflection agent
        self.register_config("basic_reflection", "reflection", {
            "memory_type": "conversation",
            "max_reflections": 2
        })
        
        # Tool-enabled ReAct agent
        self.register_config("tool_react", "react", {
            "memory_type": "conversation",
            "max_steps": 8
        })
        
        # Advanced planning agent
        self.register_config("advanced_planning", "planning", {
            "memory_type": "episodic"
        })
        
        # Research agent (ReAct + search tools)
        self.register_config("research", "react", {
            "memory_type": "episodic",
            "max_steps": 15
        })


# Global registry instance
agent_registry = AgentRegistry()

# Setup default configurations
agent_registry.setup_default_configs()


def create_agent(agent_type: str, **config) -> IAgent:
    """Convenience function to create an agent"""
    factory = AgentFactory()
    return factory.create_agent(agent_type, config)


def create_reflection_agent(**config) -> ReflectionAgent:
    """Convenience function to create a reflection agent"""
    return create_agent("reflection", **config)


def create_react_agent(**config) -> ReactAgent:
    """Convenience function to create a ReAct agent"""
    return create_agent("react", **config)


def create_planning_agent(**config) -> PlanningAgent:
    """Convenience function to create a planning agent"""
    return create_agent("planning", **config)
