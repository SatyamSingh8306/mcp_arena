from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from mcp_arena.agent.interfaces import IAgent
from mcp_arena.agent.factory import AgentBuilder

class AgentTemplate(ABC):
    """
    Base class for agent templates.
    Templates define pre-configured agent structures for specific use cases.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the template (e.g., 'support-bot', 'code-reviewer')"""
        pass
        
    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this template does"""
        pass
    
    @property
    def parameters(self) -> List[str]:
        """List of required parameters for this template"""
        return []
        
    @abstractmethod
    def build(self, **kwargs) -> IAgent:
        """
        Build and return the configured agent.
        
        Args:
            **kwargs: Configuration parameters specific to the template
            
        Returns:
            IAgent: A fully configured agent ready to run
        """
        pass

    def get_info(self) -> Dict[str, Any]:
        """Return template metadata"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }
