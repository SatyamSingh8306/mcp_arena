from typing import Any, Dict, List, Optional, Callable
from .interfaces import IAgent, IAgentBehavior, IAgentState
from .factory import AgentFactory


class AgentRouter:
    """Router for directing requests to appropriate agents"""
    
    def __init__(self, factory: AgentFactory = None):
        self.factory = factory or AgentFactory()
        self.routes: List[Dict[str, Any]] = []
        self.default_agent: Optional[IAgent] = None
    
    def add_route(self, condition: Callable[[str], bool], agent_type: str, config: Dict[str, Any] = None) -> None:
        """Add a routing rule"""
        self.routes.append({
            "condition": condition,
            "agent_type": agent_type,
            "config": config or {}
        })
    
    def set_default_agent(self, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Set the default agent for unmatched requests"""
        self.default_agent = self.factory.create_agent(agent_type, config or {})
    
    def route(self, input_text: str) -> IAgent:
        """Route input to the appropriate agent"""
        # Check routes in order
        for route in self.routes:
            if route["condition"](input_text):
                return self.factory.create_agent(route["agent_type"], route["config"])
        
        # Return default agent if no routes match
        if self.default_agent:
            return self.default_agent
        
        # Create a basic reflection agent as fallback
        return self.factory.create_agent("reflection")
    
    def process(self, input_text: str) -> Any:
        """Process input using the routed agent"""
        agent = self.route(input_text)
        return agent.process(input_text)
    
    def run(self, input_text: str) -> Any:
        """Run the router with given input and return response.
        
        This is the primary method for executing the router. It routes
        the input to the appropriate agent and returns the response.
        
        Args:
            input_text: The input text to process
            
        Returns:
            The response from the routed agent
        """
        return self.process(input_text)


class SmartRouter(AgentRouter):
    """Smart router that uses LLM-based routing decisions"""
    
    def __init__(self, factory: AgentFactory = None, llm=None):
        super().__init__(factory)
        self.llm = llm
    
    def intelligent_route(self, input_text: str) -> str:
        """Use LLM to determine the best agent type"""
        if not self.llm:
            return "reflection"  # Default fallback
        
        prompt = f"""Analyze the following request and determine which type of agent would be best suited to handle it.

Available agent types:
- reflection: For thoughtful, self-improving responses
- react: For tasks requiring reasoning and action
- planning: For complex goals that need step-by-step planning

Request: {input_text}

Respond with just the agent type name (reflection, react, or planning):"""
        
        try:
            result = self.llm.invoke(prompt)
            agent_type = result.content if hasattr(result, 'content') else str(result)
            agent_type = agent_type.strip().lower()
            
            # Validate the response
            if agent_type in ["reflection", "react", "planning"]:
                return agent_type
            else:
                return "reflection"  # Default if invalid response
        except Exception:
            return "reflection"  # Default on error
    
    def route(self, input_text: str) -> IAgent:
        """Route using intelligent decision making"""
        # First check explicit routes
        for route in self.routes:
            if route["condition"](input_text):
                return self.factory.create_agent(route["agent_type"], route["config"])
        
        # Use intelligent routing
        agent_type = self.intelligent_route(input_text)
        return self.factory.create_agent(agent_type)
    
    def run(self, input_text: str) -> Any:
        """Run the smart router with given input and return response.
        
        This method uses LLM-based intelligent routing to select the
        best agent for the given input.
        
        Args:
            input_text: The input text to process
            
        Returns:
            The response from the intelligently routed agent
        """
        return self.process(input_text)


class MultiAgentOrchestrator:
    """Orchestrator that can coordinate multiple agents for complex tasks"""
    
    def __init__(self, factory: AgentFactory = None):
        self.factory = factory or AgentFactory()
        self.agents: Dict[str, IAgent] = {}
        self.workflows: List[Dict[str, Any]] = []
    
    def register_agent(self, name: str, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Register an agent with a name"""
        agent = self.factory.create_agent(agent_type, config or {})
        self.agents[name] = agent
    
    def add_workflow(self, name: str, steps: List[Dict[str, Any]]) -> None:
        """Add a workflow that coordinates multiple agents"""
        self.workflows.append({
            "name": name,
            "steps": steps
        })
    
    def execute_workflow(self, workflow_name: str, initial_input: Any) -> Dict[str, Any]:
        """Execute a workflow across multiple agents"""
        workflow = None
        for wf in self.workflows:
            if wf["name"] == workflow_name:
                workflow = wf
                break
        
        if not workflow:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        results = {}
        current_input = initial_input
        
        for step in workflow["steps"]:
            agent_name = step["agent"]
            agent = self.agents.get(agent_name)
            
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not found")
            
            # Execute the step
            step_result = agent.process(current_input)
            results[f"{agent_name}_output"] = step_result
            
            # Prepare input for next step
            if "transform" in step:
                current_input = step["transform"](step_result, results)
            else:
                current_input = step_result
        
        return results
    
    def parallel_execute(self, agent_names: List[str], inputs: List[Any]) -> List[Any]:
        """Execute multiple agents in parallel"""
        import concurrent.futures
        
        def execute_agent(agent_name, input_data):
            agent = self.agents.get(agent_name)
            if not agent:
                raise ValueError(f"Agent '{agent_name}' not found")
            return agent.process(input_data)
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(execute_agent, name, inp) 
                for name, inp in zip(agent_names, inputs)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        return results
    
    def run(self, workflow_name: str, initial_input: Any) -> Dict[str, Any]:
        """Run a workflow with given input and return results.
        
        This is the primary method for executing the orchestrator.
        It delegates to execute_workflow for the actual execution.
        
        Args:
            workflow_name: The name of the workflow to execute
            initial_input: The initial input for the workflow
            
        Returns:
            Dictionary containing outputs from all agents in the workflow
        """
        return self.execute_workflow(workflow_name, initial_input)


class ConditionalRouter:
    """Router that uses conditional logic for routing decisions"""
    
    def __init__(self, factory: AgentFactory = None):
        self.factory = factory or AgentFactory()
        self.conditions: List[Dict[str, Any]] = []
        self.default_route: Optional[Dict[str, Any]] = None
    
    def add_condition(self, 
                     condition: Callable[[str], bool], 
                     agent_type: str, 
                     config: Dict[str, Any] = None,
                     priority: int = 0) -> None:
        """Add a conditional routing rule"""
        self.conditions.append({
            "condition": condition,
            "agent_type": agent_type,
            "config": config or {},
            "priority": priority
        })
        
        # Sort by priority (higher priority first)
        self.conditions.sort(key=lambda x: x["priority"], reverse=True)
    
    def set_default(self, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Set the default route"""
        self.default_route = {
            "agent_type": agent_type,
            "config": config or {}
        }
    
    def route(self, input_text: str) -> IAgent:
        """Route based on conditions"""
        for condition in self.conditions:
            if condition["condition"](input_text):
                return self.factory.create_agent(
                    condition["agent_type"], 
                    condition["config"]
                )
        
        if self.default_route:
            return self.factory.create_agent(
                self.default_route["agent_type"], 
                self.default_route["config"]
            )
        
        # Fallback to reflection agent
        return self.factory.create_agent("reflection")
    
    def process(self, input_text: str) -> Any:
        """Process input using the routed agent"""
        agent = self.route(input_text)
        return agent.process(input_text)
    
    def run(self, input_text: str) -> Any:
        """Run the conditional router with given input and return response.
        
        This method uses priority-based conditional routing to select
        the best agent for the given input.
        
        Args:
            input_text: The input text to process
            
        Returns:
            The response from the conditionally routed agent
        """
        return self.process(input_text)


# Pre-built routing configurations
def create_default_router() -> AgentRouter:
    """Create a router with sensible default routing rules"""
    router = AgentRouter()
    
    # Route planning requests
    router.add_route(
        lambda text: any(keyword in text.lower() for keyword in ["plan", "step", "goal", "how to"]),
        "planning"
    )
    
    # Route action-oriented requests
    router.add_route(
        lambda text: any(keyword in text.lower() for keyword in ["do", "execute", "run", "perform", "search"]),
        "react"
    )
    
    # Default to reflection
    router.set_default_agent("reflection")
    
    return router


def create_research_router() -> SmartRouter:
    """Create a router optimized for research tasks"""
    router = SmartRouter()
    
    # Route complex research to planning
    router.add_route(
        lambda text: any(keyword in text.lower() for keyword in ["research", "analyze", "investigate", "study"]),
        "planning",
        {"memory_type": "episodic"}
    )
    
    # Route simple queries to react
    router.add_route(
        lambda text: any(keyword in text.lower() for keyword in ["find", "search", "look up", "what is"]),
        "react",
        {"max_steps": 5}
    )
    
    return router