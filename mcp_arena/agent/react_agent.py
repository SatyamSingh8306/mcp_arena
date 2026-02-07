from typing import Any, Dict, List, Optional, Callable
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.graph import START, END
from langgraph.types import Command
from langgraph.prebuilt import ToolNode
from .base import BaseAgent
from .interfaces import IAgent, IAgentTool, IAgentMemory, IAgentPolicy
from .state import ReactAgentState
from .memory import MemoryFactory


class ReactAgent(BaseAgent, IAgent):
    """ReAct (Reasoning + Acting) Agent implementation"""
    
    def __init__(self, llm=None, memory_type: str = "conversation", **kwargs):
        state_schema = ReactAgentState
        super().__init__(state_schema, **kwargs)
        self.llm = llm
        self.tools: List[IAgentTool] = []
        self.memory: Optional[IAgentMemory] = None
        self.policies: List[IAgentPolicy] = []
        self.config: Dict[str, Any] = {}
        self.tool_node: Optional[ToolNode] = None
        
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
        
        # Configure max steps
        if "max_steps" in config:
            self.add_node("configure_max_steps", 
                         lambda state: self._configure_max_steps(state, config["max_steps"]))
    
    def run(self, input_data: Any) -> Any:
        """Run the agent with given input and return response.
        
        This is the primary method for executing the ReAct agent.
        It delegates to process() for the actual execution.
        
        Args:
            input_data: The input to process (typically a string query)
            
        Returns:
            The agent's response after reasoning and acting
        """
        return self.process(input_data)
    
    def process(self, input_data: Any) -> Any:
        """Process input and return response"""
        if isinstance(input_data, str):
            # Create initial state
            initial_state = ReactAgentState()
            initial_state.add_message({"type": "user", "content": input_data})
            
            # Run the graph
            result = self.get_compiled_graph().invoke(initial_state)
            
            # Return the final observation or thought
            return result.observation or result.thought
        
        return None
    
    def get_compiled_graph(self) -> CompiledStateGraph:
        """Get the compiled LangGraph"""
        return self.compile()
    
    def add_tool(self, tool: IAgentTool) -> None:
        """Add a tool to the agent"""
        self.tools.append(tool)
        self._update_tool_node()
    
    def set_memory(self, memory: IAgentMemory) -> None:
        """Set the memory system"""
        self.memory = memory
    
    def add_policy(self, policy: IAgentPolicy) -> None:
        """Add a policy to the agent"""
        self.policies.append(policy)
    
    def _build_graph(self) -> None:
        """Build the ReAct graph"""
        
        # Add nodes
        self.add_node("think", self._think)
        self.add_node("act", self._act)
        self.add_node("observe", self._observe)
        self.add_node("should_continue", self._should_continue)
        
        # Add edges
        self.add_edge(START, "think")
        self.add_edge("think", "act")
        self.add_edge("act", "observe")
        self.add_edge("observe", "should_continue")
        self.add_conditional_edges(
            "should_continue",
            self._continue_decision,
            {
                "continue": "think",
                "end": END
            }
        )
    
    def _think(self, state: ReactAgentState) -> Dict[str, Any]:
        """Reason about what to do next"""
        if not self.llm:
            return {"thought": "LLM not configured"}
        
        # Get context
        context = self._get_context(state)
        
        # Get available tools
        tools_description = self._get_tools_description()
        
        prompt = f"""You are a helpful assistant that thinks step by step. 

{context}

Available tools:
{tools_description}

Think about what you need to do to answer the user's question. 
If you need to use a tool, specify the tool name and parameters.
If you have enough information to answer, provide your final answer.

Your thought:"""
        
        try:
            thought_result = self.llm.invoke(prompt)
            thought = thought_result.content if hasattr(thought_result, 'content') else str(thought_result)
        except Exception as e:
            thought = f"Error in thinking: {str(e)}"
        
        # Apply policies
        for policy in self.policies:
            thought = policy.filter_response(thought)
        
        return {"thought": thought}
    
    def _act(self, state: ReactAgentState) -> Dict[str, Any]:
        """Execute an action based on the thought"""
        thought = state.thought or ""
        
        # Parse the thought to determine if we need to use a tool
        action = self._parse_action_from_thought(thought)
        
        if action and self.tool_node:
            # Execute the tool
            try:
                tool_result = self.tool_node.invoke({"messages": [{"role": "assistant", "content": action}]})
                observation = str(tool_result)
            except Exception as e:
                observation = f"Error executing tool: {str(e)}"
        else:
            # No tool needed, use the thought as the final answer
            observation = thought
        
        return {"action": action, "observation": observation}
    
    def _observe(self, state: ReactAgentState) -> Dict[str, Any]:
        """Process the observation and update state"""
        # Store the observation
        observation = state.observation or ""
        
        # Store in memory
        if self.memory:
            self.memory.store("last_observation", observation)
            
            # Add to conversation history if it's a final answer
            if not self._needs_tool(state.thought or ""):
                user_msg = ""
                for message in reversed(state.get_messages()):
                    if message.get("type") == "user":
                        user_msg = message.get("content", "")
                        break
                
                if hasattr(self.memory, 'add_conversation_turn'):
                    self.memory.add_conversation_turn(user_msg, observation)
        
        return {}
    
    def _should_continue(self, state: ReactAgentState) -> Dict[str, Any]:
        """Decide whether to continue the ReAct loop"""
        thought = state.thought or ""
        
        # Continue if we need to use a tool and haven't reached max steps
        should_continue = (
            self._needs_tool(thought) and 
            not state.is_max_steps_reached()
        )
        
        return {"should_continue": should_continue}
    
    def _continue_decision(self, state: ReactAgentState) -> str:
        """Make decision about continuing"""
        thought = state.thought or ""
        
        if self._needs_tool(thought) and not state.is_max_steps_reached():
            return "continue"
        else:
            return "end"
    
    def _get_context(self, state: ReactAgentState) -> str:
        """Get context for reasoning"""
        context_parts = []
        
        # Add user message
        for message in reversed(state.get_messages()):
            if message.get("type") == "user":
                context_parts.append(f"User: {message.get('content', '')}")
                break
        
        # Add recent conversation history from memory
        if self.memory and hasattr(self.memory, 'get_recent_context'):
            recent_context = self.memory.get_recent_context(3)
            if recent_context:
                context_parts.append(f"Recent conversation:\n{recent_context}")
        
        # Add step information
        if state.step_count > 0:
            context_parts.append(f"Current step: {state.step_count}")
            
            # Add previous thought/action/observation
            if state.thought:
                context_parts.append(f"Previous thought: {state.thought}")
            if state.action:
                context_parts.append(f"Previous action: {state.action}")
            if state.observation:
                context_parts.append(f"Previous observation: {state.observation}")
        
        return "\n\n".join(context_parts)
    
    def _get_tools_description(self) -> str:
        """Get description of available tools"""
        if not self.tools:
            return "No tools available."
        
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.get_description()}")
        
        return "\n".join(descriptions)
    
    def _parse_action_from_thought(self, thought: str) -> Optional[str]:
        """Parse action from thought - simplified implementation"""
        thought_lower = thought.lower()
        
        # Look for tool usage patterns
        for tool in self.tools:
            tool_name = tool.get_description().split(':')[0].strip().lower()
            if tool_name in thought_lower:
                # Simple extraction - in real implementation, would be more sophisticated
                return thought
        
        return None
    
    def _needs_tool(self, thought: str) -> bool:
        """Check if the thought indicates a need for tool usage"""
        tool_indicators = ["use", "search", "calculate", "find", "look up", "check"]
        
        for indicator in tool_indicators:
            if indicator in thought.lower():
                return True
        
        # Also check if any tool name is mentioned
        for tool in self.tools:
            tool_name = tool.get_description().split(':')[0].strip().lower()
            if tool_name in thought.lower():
                return True
        
        return False
    
    def _update_tool_node(self) -> None:
        """Update the tool node when tools are added"""
        if self.tools:
            # Convert tools to LangGraph format
            langgraph_tools = []
            for tool in self.tools:
                # Create a wrapper function for each tool
                def make_tool_wrapper(t):
                    def tool_wrapper(*args, **kwargs):
                        return t.execute(*args, **kwargs)
                    tool_wrapper.name = t.get_description().split(':')[0].strip()
                    tool_wrapper.description = t.get_description()
                    tool_wrapper.args = t.get_schema()
                    return tool_wrapper
                
                langgraph_tools.append(make_tool_wrapper(tool))
            
            self.tool_node = ToolNode(langgraph_tools)
    
    def _configure_max_steps(self, state: ReactAgentState, max_steps: int) -> Dict[str, Any]:
        """Configure maximum number of steps"""
        return {"max_steps": max_steps}
