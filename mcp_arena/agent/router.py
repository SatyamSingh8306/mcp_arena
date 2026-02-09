from typing import Any, Dict, List, Optional, Callable
from .interfaces import IAgent, IRouter
from .factory import AgentFactory


class BaseRouter(IRouter):
    """Base class for all routers.

    Provides a consistent API with run() as the primary execution method.
    Subclasses should implement the route() method and optionally override
    run() or process() for custom behavior.

    This follows the Template Method pattern where:
    - run() is the public API (template method)
    - process() contains the algorithm skeleton
    - route() is the hook method subclasses must implement
    """

    def __init__(self, factory: AgentFactory = None):
        """Initialize the router with an optional agent factory.

        Args:
            factory: The agent factory to use for creating agents.
                    If None, a default AgentFactory is created.
        """
        self.factory = factory or AgentFactory()

    def run(self, input_text: str) -> Any:
        """Run the router with input text.

        This is the primary execution method that provides a consistent API.
        It delegates to process() by default.

        Args:
            input_text: The input text to process.

        Returns:
            The response from the routed agent.
        """
        return self.process(input_text)

    def process(self, input_text: str) -> Any:
        """Process input using the routed agent.

        Routes the input and processes it through the selected agent.
        Can be overridden by subclasses for custom behavior.

        Args:
            input_text: The input text to process.

        Returns:
            The response from the agent.
        """
        agent = self.route(input_text)
        return agent.process(input_text)


class AgentRouter(BaseRouter):
    """Router for directing requests to appropriate agents.

    Supports rule-based routing with conditions and a default fallback agent.
    """

    def __init__(self, factory: AgentFactory = None):
        super().__init__(factory)
        self.routes: List[Dict[str, Any]] = []
        self.default_agent: Optional[IAgent] = None

    def add_route(self, condition: Callable[[str], bool], agent_type: str, config: Dict[str, Any] = None) -> None:
        """Add a routing rule.

        Args:
            condition: A function that returns True if this route should handle the input.
            agent_type: The type of agent to create for this route.
            config: Optional configuration for the agent.
        """
        self.routes.append({
            "condition": condition,
            "agent_type": agent_type,
            "config": config or {}
        })

    def set_default_agent(self, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Set the default agent for unmatched requests."""
        self.default_agent = self.factory.create_agent(agent_type, config or {})

    def route(self, input_text: str) -> IAgent:
        """Route input to the appropriate agent."""
        # Check routes in order
        for route in self.routes:
            if route["condition"](input_text):
                return self.factory.create_agent(route["agent_type"], route["config"])

        # Return default agent if no routes match
        if self.default_agent:
            return self.default_agent

        # Create a basic reflection agent as fallback
        return self.factory.create_agent("reflection")


class SmartRouter(AgentRouter):
    """Smart router that uses LLM-based routing decisions."""

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


class MultiAgentOrchestrator(BaseRouter):
    """Orchestrator that can coordinate multiple agents for complex tasks.

    This router coordinates workflows across multiple registered agents,
    supporting both sequential and parallel execution patterns.
    """

    def __init__(self, factory: AgentFactory = None):
        super().__init__(factory)
        self.agents: Dict[str, IAgent] = {}
        self.workflows: List[Dict[str, Any]] = []
        self._default_workflow: Optional[str] = None

    def register_agent(self, name: str, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Register an agent with a name."""
        agent = self.factory.create_agent(agent_type, config or {})
        self.agents[name] = agent

    def add_workflow(self, name: str, steps: List[Dict[str, Any]], is_default: bool = False) -> None:
        """Add a workflow that coordinates multiple agents.

        Args:
            name: The workflow name.
            steps: List of workflow steps, each containing 'agent' key.
            is_default: If True, this workflow is used by run().
        """
        self.workflows.append({
            "name": name,
            "steps": steps
        })
        if is_default:
            self._default_workflow = name

    def route(self, input_text: str) -> IAgent:
        """Route to the first agent in the default workflow.

        For orchestrator, routing is less meaningful - use run() or
        execute_workflow() instead for proper workflow execution.
        """
        if self._default_workflow:
            for wf in self.workflows:
                if wf["name"] == self._default_workflow and wf["steps"]:
                    first_agent_name = wf["steps"][0]["agent"]
                    if first_agent_name in self.agents:
                        return self.agents[first_agent_name]

        # Return first registered agent or create a fallback
        if self.agents:
            return next(iter(self.agents.values()))
        return self.factory.create_agent("reflection")

    def run(self, input_text: str, workflow_name: str = None) -> Any:
        """Run the orchestrator with input text.

        Args:
            input_text: The input to process.
            workflow_name: Optional workflow to execute. If None, uses default.

        Returns:
            Workflow results if a workflow is executed, otherwise process() result.
        """
        target_workflow = workflow_name or self._default_workflow
        if target_workflow:
            return self.execute_workflow(target_workflow, input_text)
        return self.process(input_text)
    
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


class ConditionalRouter(BaseRouter):
    """Router that uses conditional logic with priority-based routing decisions."""

    def __init__(self, factory: AgentFactory = None):
        super().__init__(factory)
        self.conditions: List[Dict[str, Any]] = []
        self.default_route: Optional[Dict[str, Any]] = None

    def add_condition(self,
                     condition: Callable[[str], bool],
                     agent_type: str,
                     config: Dict[str, Any] = None,
                     priority: int = 0) -> None:
        """Add a conditional routing rule with priority."""
        self.conditions.append({
            "condition": condition,
            "agent_type": agent_type,
            "config": config or {},
            "priority": priority
        })

        # Sort by priority (higher priority first)
        self.conditions.sort(key=lambda x: x["priority"], reverse=True)

    def set_default(self, agent_type: str, config: Dict[str, Any] = None) -> None:
        """Set the default route."""
        self.default_route = {
            "agent_type": agent_type,
            "config": config or {}
        }

    def route(self, input_text: str) -> IAgent:
        """Route based on conditions."""
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