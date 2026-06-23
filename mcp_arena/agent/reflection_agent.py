from typing import Any, Dict, List, Optional
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.graph import START, END
from langgraph.types import Command
from .base import BaseAgent
from .interfaces import IAgent, IAgentTool, IAgentMemory, IAgentPolicy
from .state import ReflectionAgentState
from .memory import MemoryFactory


class ReflectionAgent(BaseAgent, IAgent):
    """Agent that uses reflection to improve responses"""
    
    def __init__(self, llm=None, memory_type: str = "conversation", **kwargs):
        state_schema = ReflectionAgentState
        super().__init__(state_schema, **kwargs)
        self.llm = llm
        self.tools: List[IAgentTool] = []
        self.memory: Optional[IAgentMemory] = None
        self.policies: List[IAgentPolicy] = []
        self.config: Dict[str, Any] = {}
        
        # Initialize memory
        if memory_type:
            self.memory = MemoryFactory.create_memory(memory_type)
        
        # Build the graph
        self._build_graph()
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent with configuration"""
        self.config = config
        
        # Set up LLM if provided in config
        if "llm" in config:
            self.llm = config["llm"]
        
        # Configure reflection parameters
        if "max_reflections" in config:
            self.add_node("configure_max_reflections", 
                         lambda state: self._configure_max_reflections(state, config["max_reflections"]))

    def run(self, input_data: Any) -> Any:
        """Run the agent with input data.

        This is the primary execution method that provides a consistent API.
        It delegates to process() for the actual execution logic.

        Args:
            input_data: The input to process (typically a string).

        Returns:
            The agent's response (refined or initial response).
        """
        return self.process(input_data)

    def process(self, input_data: Any) -> Any:
        """Process input and return response."""
        if isinstance(input_data, str):
            # Create initial state
            initial_state = ReflectionAgentState()
            initial_state.add_message({"type": "user", "content": input_data})
            
            # Run the graph
            result = self.get_compiled_graph().invoke(initial_state)
            
            # Return the final response
            return result.refined_response or result.initial_response
        
        return None

    def get_compiled_graph(self) -> CompiledStateGraph:
        """Get the compiled LangGraph."""
        return self.compile()

    def add_tool(self, tool: IAgentTool) -> None:
        """Add a tool to the agent."""
        self.tools.append(tool)
    
    def set_memory(self, memory: IAgentMemory) -> None:
        """Set the memory system"""
        self.memory = memory
    
    def add_policy(self, policy: IAgentPolicy) -> None:
        """Add a policy to the agent"""
        self.policies.append(policy)
    
    def _build_graph(self) -> None:
        """Build the reflection graph"""
        
        # Add nodes
        self.add_node("generate_initial", self._generate_initial_response)
        self.add_node("reflect", self._reflect_on_response)
        self.add_node("refine", self._refine_response)
        self.add_node("should_continue", self._should_continue_reflection)
        
        # Add edges
        self.add_edge(START, "generate_initial")
        self.add_edge("generate_initial", "reflect")
        self.add_edge("reflect", "refine")
        self.add_edge("refine", "should_continue")
        self.add_conditional_edges(
            "should_continue",
            self._reflection_decision,
            {
                "continue": "reflect",
                "end": END
            }
        )
    
    def _generate_initial_response(self, state: ReflectionAgentState) -> Dict[str, Any]:
        """Generate initial response"""
        if not self.llm:
            return {"initial_response": "LLM not configured"}
        
        # Get context from memory
        context = ""
        if self.memory:
            recent_context = self.memory.retrieve("recent_context")
            if recent_context:
                context = f"\n\nRecent context:\n{recent_context}"
        
        # Get the user's message
        user_message = ""
        for message in reversed(state.get_messages()):
            if message.get("type") == "user":
                user_message = message.get("content", "")
                break
        
        # Generate initial response
        prompt = f"""You are a helpful assistant. Please respond to the user's message thoughtfully and accurately.

User message: {user_message}{context}

Provide a comprehensive response:"""
        
        try:
            response = self.llm.invoke(prompt)
            initial_response = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            initial_response = f"Error generating response: {str(e)}"
        
        # Apply policies
        for policy in self.policies:
            initial_response = policy.filter_response(initial_response)
        
        # Store in memory
        if self.memory:
            self.memory.store("last_user_message", user_message)
            self.memory.store("last_response", initial_response)
        
        return {"initial_response": initial_response}
    
    def _reflect_on_response(self, state: ReflectionAgentState) -> Dict[str, Any]:
        """Reflect on the current response"""
        if not self.llm:
            return {"reflection": "LLM not configured for reflection"}
        
        response_to_reflect = state.refined_response or state.initial_response
        
        prompt = f"""Please reflect on the following response and identify areas for improvement. 
Consider:
1. Accuracy and correctness
2. Completeness 
3. Clarity and organization
4. Potential misunderstandings
5. Missing important information

Original response:
{response_to_reflect}

Provide your reflection:"""
        
        try:
            reflection_result = self.llm.invoke(prompt)
            reflection = reflection_result.content if hasattr(reflection_result, 'content') else str(reflection_result)
        except Exception as e:
            reflection = f"Error in reflection: {str(e)}"
        
        return {"reflection": reflection}
    
    def _refine_response(self, state: ReflectionAgentState) -> Dict[str, Any]:
        """Refine the response based on reflection"""
        if not self.llm:
            return {"refined_response": state.initial_response}
        
        current_response = state.refined_response or state.initial_response
        
        prompt = f"""Based on the reflection below, please refine and improve the original response.

Original response:
{current_response}

Reflection:
{state.reflection}

Please provide an improved response that addresses the points raised in the reflection:"""
        
        try:
            refined_result = self.llm.invoke(prompt)
            refined_response = refined_result.content if hasattr(refined_result, 'content') else str(refined_result)
        except Exception as e:
            refined_response = current_response  # Fall back to original response
        
        # Apply policies
        for policy in self.policies:
            refined_response = policy.filter_response(refined_response)
        
        return {"refined_response": refined_response}
    
    def _should_continue_reflection(self, state: ReflectionAgentState) -> Dict[str, Any]:
        """Decide whether to continue reflecting"""
        return {"continue_reflection": state.can_reflect_more()}
    
    def _reflection_decision(self, state: ReflectionAgentState) -> str:
        """Make decision about continuing reflection"""
        return "continue" if state.can_reflect_more() else "end"
    
    def _configure_max_reflections(self, state: ReflectionAgentState, max_reflections: int) -> Dict[str, Any]:
        """Configure maximum number of reflections"""
        return {"max_reflections": max_reflections}
