from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from .interfaces import IAgentState


@dataclass
class BaseAgentState(IAgentState):
    """Base implementation of agent state"""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def get_messages(self) -> List[Dict[str, Any]]:
        return self.messages.copy()
    
    def add_message(self, message: Dict[str, Any]) -> None:
        self.messages.append(message)
    
    def get_context(self) -> Dict[str, Any]:
        return self.context.copy()
    
    def update_context(self, updates: Dict[str, Any]) -> None:
        self.context.update(updates)
    
    def clear_messages(self) -> None:
        self.messages.clear()


@dataclass
class ReactAgentState(BaseAgentState):
    """State for ReAct (Reasoning + Acting) agents"""
    thought: Optional[str] = None
    action: Optional[str] = None
    observation: Optional[str] = None
    step_count: int = 0
    max_steps: int = 10
    
    def add_thought(self, thought: str) -> None:
        self.thought = thought
        self.add_message({"type": "thought", "content": thought})
    
    def add_action(self, action: str) -> None:
        self.action = action
        self.add_message({"type": "action", "content": action})
    
    def add_observation(self, observation: str) -> None:
        self.observation = observation
        self.add_message({"type": "observation", "content": observation})
    
    def increment_step(self) -> None:
        self.step_count += 1
    
    def is_max_steps_reached(self) -> bool:
        return self.step_count >= self.max_steps


@dataclass
class ReflectionAgentState(BaseAgentState):
    """State for Reflection agents"""
    initial_response: Optional[str] = None
    reflection: Optional[str] = None
    refined_response: Optional[str] = None
    reflection_count: int = 0
    max_reflections: int = 3
    
    def set_initial_response(self, response: str) -> None:
        self.initial_response = response
        self.add_message({"type": "initial_response", "content": response})
    
    def add_reflection(self, reflection: str) -> None:
        self.reflection = reflection
        self.reflection_count += 1
        self.add_message({"type": "reflection", "content": reflection})
    
    def set_refined_response(self, response: str) -> None:
        self.refined_response = response
        self.add_message({"type": "refined_response", "content": response})
    
    def can_reflect_more(self) -> bool:
        return self.reflection_count < self.max_reflections


@dataclass
class PlanningAgentState(BaseAgentState):
    """State for Planning agents"""
    plan: Optional[List[str]] = None
    current_step: int = 0
    completed_steps: List[str] = field(default_factory=list)
    goal: Optional[str] = None
    
    def set_plan(self, plan: List[str]) -> None:
        self.plan = plan
        self.add_message({"type": "plan", "content": plan})
    
    def set_goal(self, goal: str) -> None:
        self.goal = goal
        self.add_message({"type": "goal", "content": goal})
    
    def get_current_step(self) -> Optional[str]:
        if self.plan and self.current_step < len(self.plan):
            return self.plan[self.current_step]
        return None
    
    def complete_current_step(self) -> None:
        if self.get_current_step():
            self.completed_steps.append(self.plan[self.current_step])
            self.current_step += 1
    
    def is_plan_complete(self) -> bool:
        return self.plan and self.current_step >= len(self.plan)
