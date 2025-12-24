"""
Examples demonstrating the SOLID agent architecture usage.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import (
    create_agent, create_reflection_agent, create_react_agent, create_planning_agent,
    agent_registry, tool_registry, create_default_router,
    ReflectionAgent, ReactAgent, PlanningAgent,
    CalculatorTool, FileSystemTool, SafetyPolicy, 
    create_default_policy_chain, AgentBuilder
)


def example_1_basic_reflection_agent():
    """Example 1: Basic reflection agent usage"""
    print("=== Example 1: Basic Reflection Agent ===")
    
    # Create a reflection agent
    agent = create_reflection_agent(
        memory_type="conversation",
        max_reflections=2
    )
    
    # Process a simple query
    response = agent.process("Explain the concept of machine learning")
    print(f"Response: {response}\n")


def example_2_react_agent_with_tools():
    """Example 2: ReAct agent with tools"""
    print("=== Example 2: ReAct Agent with Tools ===")
    
    # Create a ReAct agent with tools
    agent = create_react_agent(
        memory_type="conversation",
        max_steps=8
    )
    
    # Add tools
    calculator = CalculatorTool()
    filesystem = FileSystemTool()
    
    agent.add_tool(calculator)
    agent.add_tool(filesystem)
    
    # Process a calculation request
    response = agent.process("Calculate (15 * 8) + 32")
    print(f"Response: {response}\n")


def example_3_planning_agent():
    """Example 3: Planning agent for complex tasks"""
    print("=== Example 3: Planning Agent ===")
    
    # Create a planning agent
    agent = create_planning_agent(
        memory_type="episodic"
    )
    
    # Process a planning request
    response = agent.process("Help me plan a software development project")
    print(f"Response: {response}\n")


def example_4_agent_builder_pattern():
    """Example 4: Using the Agent Builder pattern"""
    print("=== Example 4: Agent Builder Pattern ===")
    
    # Use builder pattern for complex configuration
    agent = (AgentBuilder("react")
             .with_memory("conversation", max_history=50)
             .with_tool(CalculatorTool())
             .with_tool(FileSystemTool())
             .with_config(max_steps=12)
             .build())
    
    response = agent.process("Calculate the area of a circle with radius 5")
    print(f"Response: {response}\n")


def example_5_agent_registry():
    """Example 5: Using the agent registry"""
    print("=== Example 5: Agent Registry ===")
    
    # Use pre-configured agent from registry
    agent = agent_registry.create_from_config("basic_reflection")
    
    response = agent.process("What are the benefits of clean code?")
    print(f"Response: {response}\n")


def example_6_router_usage():
    """Example 6: Using the intelligent router"""
    print("=== Example 6: Intelligent Router ===")
    
    # Create a router
    router = create_default_router()
    
    # Test different types of requests
    requests = [
        "Tell me about artificial intelligence",
        "Calculate 25 * 17",
        "Help me plan a vacation"
    ]
    
    for request in requests:
        response = router.process(request)
        print(f"Request: {request}")
        print(f"Response: {response}\n")


def example_7_policies():
    """Example 7: Using policies for safety and filtering"""
    print("=== Example 7: Agent Policies ===")
    
    # Create agent with policies
    agent = create_reflection_agent()
    
    # Add policies
    safety_policy = SafetyPolicy()
    content_filter = ContentFilterPolicy(max_length=500)
    
    agent.add_policy(safety_policy)
    agent.add_policy(content_filter)
    
    response = agent.process("Explain computer programming concepts")
    print(f"Response: {response}\n")


def example_8_multi_agent_system():
    """Example 8: Multi-agent orchestration"""
    print("=== Example 8: Multi-Agent System ===")
    
    from agent.router import MultiAgentOrchestrator
    
    # Create orchestrator
    orchestrator = MultiAgentOrchestrator()
    
    # Register agents
    orchestrator.register_agent("planner", "planning", {"memory_type": "episodic"})
    orchestrator.register_agent("thinker", "reflection", {"memory_type": "conversation"})
    orchestrator.register_agent("doer", "react", {"max_steps": 5})
    
    # Add workflow
    orchestrator.add_workflow("analyze_problem", [
        {"agent": "planner"},
        {"agent": "thinker"},
        {"agent": "doer"}
    ])
    
    # Execute workflow
    results = orchestrator.execute_workflow("analyze_problem", "Analyze the problem of climate change")
    print("Workflow Results:")
    for key, value in results.items():
        print(f"{key}: {value}\n")


def example_9_custom_tool():
    """Example 9: Creating and using custom tools"""
    print("=== Example 9: Custom Tools ===")
    
    from agent.tools import BaseTool
    
    class WeatherTool(BaseTool):
        def __init__(self):
            super().__init__(
                name="weather",
                description="Get weather information for a city",
                schema={"city": "string"}
            )
        
        def execute(self, city: str, **kwargs):
            # Simulate weather data
            weather_data = {
                "New York": "72°F, Sunny",
                "London": "65°F, Cloudy",
                "Tokyo": "78°F, Rainy"
            }
            return weather_data.get(city, f"Weather data not available for {city}")
    
    # Create agent with custom tool
    agent = create_react_agent()
    agent.add_tool(WeatherTool())
    
    response = agent.process("What's the weather like in New York?")
    print(f"Response: {response}\n")


def example_10_memory_types():
    """Example 10: Different memory types"""
    print("=== Example 10: Memory Types ===")
    
    from agent.memory import SimpleMemory, ConversationMemory, EpisodicMemory
    
    # Simple memory
    agent1 = create_reflection_agent()
    agent1.set_memory(SimpleMemory())
    
    # Conversation memory
    agent2 = create_reflection_agent()
    agent2.set_memory(ConversationMemory(max_history=20))
    
    # Episodic memory
    agent3 = create_planning_agent()
    agent3.set_memory(EpisodicMemory())
    
    print("Agents created with different memory types\n")


def run_all_examples():
    """Run all examples"""
    examples = [
        example_1_basic_reflection_agent,
        example_2_react_agent_with_tools,
        example_3_planning_agent,
        example_4_agent_builder_pattern,
        example_5_agent_registry,
        example_6_router_usage,
        example_7_policies,
        example_8_multi_agent_system,
        example_9_custom_tool,
        example_10_memory_types
    ]
    
    for i, example in enumerate(examples, 1):
        try:
            example()
        except Exception as e:
            print(f"Example {i} failed: {str(e)}\n")
    
    print("All examples completed!")


if __name__ == "__main__":
    run_all_examples()
