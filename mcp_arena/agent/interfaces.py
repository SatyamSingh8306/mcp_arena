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
    def run(self, input_data: Any) -> Any:
        """Run the agent with given input and return response.
        
        This is the primary method for executing an agent. It serves as
        a convenience wrapper that provides a consistent interface across
        all agent implementations.
        
        Args:
            input_data: The input to process (typically a string query)
            
        Returns:
            The agent's response after processing the input
        """
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
