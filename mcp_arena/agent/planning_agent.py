from typing import Any, Dict, List, Optional, Tuple
from langgraph.graph.state import CompiledStateGraph, StateGraph
from langgraph.graph import START, END
from langgraph.types import Command
from .base import BaseAgent
from .interfaces import IAgent, IAgentTool, IAgentMemory, IAgentPolicy
from .state import PlanningAgentState
from .memory import MemoryFactory


class PlanningAgent(BaseAgent, IAgent):
    """Agent that creates and executes plans to achieve goals"""
    
    def __init__(self, llm=None, memory_type: str = "conversation", **kwargs):
        state_schema = PlanningAgentState
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
    
    def process(self, input_data: Any) -> Any:
        """Process input and return response"""
        if isinstance(input_data, str):
            # Create initial state
            initial_state = PlanningAgentState()
            initial_state.add_message({"type": "user", "content": input_data})
            
            # Run the graph
            result = self.get_compiled_graph().invoke(initial_state)
            
            # Return the final result
            return self._format_final_response(result)
        
        return None
    
    def get_compiled_graph(self) -> CompiledStateGraph:
        """Get the compiled LangGraph"""
        return self.compile()
    
    def add_tool(self, tool: IAgentTool) -> None:
        """Add a tool to the agent"""
        self.tools.append(tool)
    
    def set_memory(self, memory: IAgentMemory) -> None:
        """Set the memory system"""
        self.memory = memory
    
    def add_policy(self, policy: IAgentPolicy) -> None:
        """Add a policy to the agent"""
        self.policies.append(policy)
    
    def _build_graph(self) -> None:
        """Build the planning graph"""
        
        # Add nodes
        self.add_node("understand_goal", self._understand_goal)
        self.add_node("create_plan", self._create_plan)
        self.add_node("execute_step", self._execute_step)
        self.add_node("evaluate_progress", self._evaluate_progress)
        self.add_node("should_continue_plan", self._should_continue_plan)
        
        # Add edges
        self.add_edge(START, "understand_goal")
        self.add_edge("understand_goal", "create_plan")
        self.add_edge("create_plan", "execute_step")
        self.add_edge("execute_step", "evaluate_progress")
        self.add_edge("evaluate_progress", "should_continue_plan")
        self.add_conditional_edges(
            "should_continue_plan",
            self._plan_decision,
            {
                "continue": "execute_step",
                "replan": "create_plan",
                "end": END
            }
        )
    
    def _understand_goal(self, state: PlanningAgentState) -> Dict[str, Any]:
        """Understand and clarify the user's goal"""
        if not self.llm:
            return {"goal": "LLM not configured"}
        
        # Get the user's message
        user_message = ""
        for message in reversed(state.get_messages()):
            if message.get("type") == "user":
                user_message = message.get("content", "")
                break
        
        prompt = f"""Please analyze the user's request and extract a clear, specific goal. 
If the request is ambiguous, identify what clarification might be needed.

User request: {user_message}

Provide a clear goal statement:"""
        
        try:
            goal_result = self.llm.invoke(prompt)
            goal = goal_result.content if hasattr(goal_result, 'content') else str(goal_result)
        except Exception as e:
            goal = f"Error understanding goal: {str(e)}"
        
        # Apply policies
        for policy in self.policies:
            goal = policy.filter_response(goal)
        
        return {"goal": goal}
    
    def _create_plan(self, state: PlanningAgentState) -> Dict[str, Any]:
        """Create a plan to achieve the goal"""
        if not self.llm:
            return {"plan": ["No LLM configured for planning"]}
        
        # Get context
        context = self._get_planning_context(state)
        
        # Get available tools
        tools_description = self._get_tools_description()
        
        prompt = f"""Create a detailed step-by-step plan to achieve the following goal:

Goal: {state.goal}

{context}

Available tools:
{tools_description}

Please break down the goal into specific, actionable steps. Each step should be something that can be executed using the available tools or reasoning.

Format your response as a numbered list of steps:"""
        
        try:
            plan_result = self.llm.invoke(prompt)
            plan_text = plan_result.content if hasattr(plan_result, 'content') else str(plan_result)
            
            # Parse the plan into a list
            plan_steps = self._parse_plan_steps(plan_text)
        except Exception as e:
            plan_steps = [f"Error creating plan: {str(e)}"]
        
        return {"plan": plan_steps}
    
    def _execute_step(self, state: PlanningAgentState) -> Dict[str, Any]:
        """Execute the current step in the plan"""
        current_step = state.get_current_step()
        
        if not current_step:
            return {"step_result": "No current step to execute"}
        
        # Try to execute using available tools
        step_result = self._execute_with_tools(current_step)
        
        # If no tool can handle it, use LLM reasoning
        if step_result is None and self.llm:
            step_result = self._execute_with_reasoning(current_step, state)
        
        if step_result is None:
            step_result = f"Executed step: {current_step}"
        
        # Store in memory
        if self.memory:
            self.memory.store(f"step_{state.current_step}_result", step_result)
        
        return {"step_result": step_result}
    
    def _evaluate_progress(self, state: PlanningAgentState) -> Dict[str, Any]:
        """Evaluate progress toward the goal"""
        if not self.llm:
            return {"progress_assessment": "LLM not configured"}
        
        # Get context including completed steps
        context = self._get_planning_context(state)
        
        prompt = f"""Evaluate the progress made toward the goal:

Goal: {state.goal}

Completed steps:
{chr(10).join([f"- {step}" for step in state.completed_steps])}

Current step result: {getattr(state, 'step_result', 'No result')}

Remaining steps:
{chr(10).join([f"- {step}" for i, step in enumerate(state.plan or []) if i >= state.current_step])}

Assess the progress and determine if:
1. The goal has been achieved
2. The plan is working well and should continue
3. The plan needs to be revised

Your assessment:"""
        
        try:
            assessment_result = self.llm.invoke(prompt)
            assessment = assessment_result.content if hasattr(assessment_result, 'content') else str(assessment_result)
        except Exception as e:
            assessment = f"Error evaluating progress: {str(e)}"
        
        return {"progress_assessment": assessment}
    
    def _should_continue_plan(self, state: PlanningAgentState) -> Dict[str, Any]:
        """Decide whether to continue the current plan"""
        assessment = getattr(state, 'progress_assessment', '')
        assessment_lower = assessment.lower()
        
        # Simple heuristic-based decision
        if 'goal achieved' in assessment_lower or 'completed' in assessment_lower:
            decision = "end"
        elif 'replan' in assessment_lower or 'revise' in assessment_lower or 'failed' in assessment_lower:
            decision = "replan"
        elif state.is_plan_complete():
            decision = "end"
        else:
            decision = "continue"
        
        return {"plan_decision": decision}
    
    def _plan_decision(self, state: PlanningAgentState) -> str:
        """Make decision about plan execution"""
        return getattr(state, 'plan_decision', 'end')
    
    def _get_planning_context(self, state: PlanningAgentState) -> str:
        """Get context for planning"""
        context_parts = []
        
        # Add previous context from memory
        if self.memory:
            recent_context = self.memory.retrieve("recent_context")
            if recent_context:
                context_parts.append(f"Recent context:\n{recent_context}")
        
        # Add completed steps
        if state.completed_steps:
            context_parts.append("Completed steps:")
            for step in state.completed_steps:
                context_parts.append(f"- {step}")
        
        return "\n\n".join(context_parts)
    
    def _get_tools_description(self) -> str:
        """Get description of available tools"""
        if not self.tools:
            return "No tools available."
        
        descriptions = []
        for tool in self.tools:
            descriptions.append(f"- {tool.get_description()}")
        
        return "\n".join(descriptions)
    
    def _parse_plan_steps(self, plan_text: str) -> List[str]:
        """Parse plan steps from LLM response"""
        lines = plan_text.strip().split('\n')
        steps = []
        
        for line in lines:
            line = line.strip()
            # Look for numbered lines or bullet points
            if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                # Remove numbering/bullets and clean up
                clean_step = line
                if line[0].isdigit():
                    # Remove "1.", "2)", etc.
                    import re
                    clean_step = re.sub(r'^\d+[\.\)]\s*', '', line)
                elif line.startswith('-') or line.startswith('*'):
                    clean_step = line[1:].strip()
                
                if clean_step:
                    steps.append(clean_step)
        
        return steps if steps else [plan_text.strip()]
    
    def _execute_with_tools(self, step: str) -> Optional[str]:
        """Try to execute a step using available tools"""
        step_lower = step.lower()
        
        for tool in self.tools:
            tool_desc = tool.get_description().lower()
            # Simple matching - in real implementation would be more sophisticated
            if any(keyword in tool_desc for keyword in step_lower.split()[:3]):
                try:
                    result = tool.execute(step)
                    return str(result)
                except Exception as e:
                    return f"Tool execution error: {str(e)}"
        
        return None
    
    def _execute_with_reasoning(self, step: str, state: PlanningAgentState) -> Optional[str]:
        """Execute a step using LLM reasoning"""
        prompt = f"""Execute the following step using reasoning:

Step: {step}

Goal: {state.goal}

Context: {self._get_planning_context(state)}

Provide the result of executing this step:"""
        
        try:
            result = self.llm.invoke(prompt)
            return result.content if hasattr(result, 'content') else str(result)
        except Exception:
            return None
    
    def _format_final_response(self, state: PlanningAgentState) -> str:
        """Format the final response"""
        response_parts = []
        
        if state.goal:
            response_parts.append(f"Goal: {state.goal}")
        
        if state.completed_steps:
            response_parts.append("\nCompleted steps:")
            for step in state.completed_steps:
                response_parts.append(f"✓ {step}")
        
        if hasattr(state, 'progress_assessment'):
            response_parts.append(f"\nFinal assessment: {state.progress_assessment}")
        
        return "\n".join(response_parts)
