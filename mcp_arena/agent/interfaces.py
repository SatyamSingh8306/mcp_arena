from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command


class IAgentState(ABC):
    """Interface for agent state management"""
    
    @abstractmethod
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get conversation messages"""
        pass
    
    @abstractmethod
    def add_message(self, message: Dict[str, Any]) -> None:
        """Add a message to the state"""
        pass
    
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        """Get agent context"""
        pass


class IAgentBehavior(ABC):
    """Interface for agent behavior strategies"""
    
    @abstractmethod
    def execute(self, state: IAgentState, context: Dict[str, Any]) -> Command:
        """Execute the agent behavior"""
        pass
    
    @abstractmethod
    def can_handle(self, state: IAgentState) -> bool:
        """Check if this behavior can handle the current state"""
        pass


class IAgentMemory(ABC):
    """Interface for agent memory management"""
    
    @abstractmethod
    def store(self, key: str, value: Any) -> None:
        """Store a value in memory"""
        pass
    
    @abstractmethod
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve a value from memory"""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all memory"""
        pass


class IAgentTool(ABC):
    """Interface for agent tools"""
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get tool description"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        pass


class IAgentFactory(ABC):
    """Interface for agent factory"""
    
    @abstractmethod
    def create_agent(self, agent_type: str, config: Dict[str, Any]) -> 'IAgent':
        """Create an agent instance"""
        pass
    
    @abstractmethod
    def register_agent_type(self, agent_type: str, agent_class: type) -> None:
        """Register a new agent type"""
        pass


class IAgent(ABC):
    """Main interface for agents"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent"""
        pass
    
    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input and return response"""
        pass
    
    @abstractmethod
    def get_compiled_graph(self) -> CompiledStateGraph:
        """Get the compiled LangGraph"""
        pass
    
    @abstractmethod
    def add_tool(self, tool: IAgentTool) -> None:
        """Add a tool to the agent"""
        pass
    
    @abstractmethod
    def set_memory(self, memory: IAgentMemory) -> None:
        """Set the memory system"""
        pass


class IAgentPolicy(ABC):
    """Interface for agent policies"""

    @abstractmethod
    def validate_action(self, action: Dict[str, Any]) -> bool:
        """Validate an action before execution"""
        pass

    @abstractmethod
    def filter_response(self, response: Any) -> Any:
        """Filter/rate-limit responses"""
        pass


class IRouter(ABC):
    """Base interface for all routers.

    This provides a consistent API across all router types. The run() method
    serves as the primary execution entry point, while route() determines
    which agent handles the request.

    All router implementations should inherit from this interface.
    """

    @abstractmethod
    def route(self, input_text: str) -> 'IAgent':
        """Route input to the appropriate agent.

        Args:
            input_text: The input text to route.

        Returns:
            The agent that should handle this input.
        """
        pass

    @abstractmethod
    def run(self, input_text: str) -> Any:
        """Run the router with input text.

        This is the primary execution method that provides a consistent API.
        It routes the input and processes it through the selected agent.

        Args:
            input_text: The input text to process.

        Returns:
            The response from the routed agent.
        """
        pass

    @abstractmethod
    def process(self, input_text: str) -> Any:
        """Process input using the routed agent.

        Args:
            input_text: The input text to process.

        Returns:
            The response from the agent.
        """
        pass
