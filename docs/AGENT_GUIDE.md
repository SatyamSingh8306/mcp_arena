# MCPForge Agent System: Comprehensive Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [Agent Types](#agent-types)
3. [Core Architecture](#core-architecture)
4. [How to Use Agents](#how-to-use-agents)
5. [Configuration & Memory](#configuration--memory)
6. [Tools System](#tools-system)
7. [Best Practices](#best-practices)

---

## Overview

The MCPForge agent system is a flexible, modular framework built on **LangGraph** that allows you to create intelligent agents with different reasoning and execution strategies. It follows **SOLID principles** and provides a clean interface-based architecture for extensibility.

### Key Features
- **Multiple Agent Types**: Different reasoning strategies for different problems
- **Memory Management**: Multiple memory backends (simple, conversation, episodic)
- **Tool Integration**: Extensible tool system for agent capabilities
- **Policy System**: Safety and validation policies for agent actions
- **Factory Pattern**: Easy agent creation and configuration
- **State Management**: Type-safe state handling per agent type

---

## Agent Types

### 1. **Reflection Agent** - Self-Improvement Through Iteration

The **Reflection Agent** generates an initial response, then reflects on it to identify improvements, and refines the response iteratively. This is perfect for tasks requiring high-quality, well-thought-out answers.

#### Use Cases:
- Generating articles or documentation
- Writing code with quality assurance
- Complex decision-making
- Content creation requiring accuracy
- Problem-solving with validation

#### How It Works:
```
Generate Initial Response 
        ↓
    Reflect on Response 
        ↓
    Refine Response 
        ↓
    Should Continue? → Yes → Reflect Again
        ↓ No
    Return Final Response
```

#### State Components:
- `initial_response`: First generated answer
- `reflection`: Critical analysis of the response
- `refined_response`: Improved answer after reflection
- `reflection_count`: Tracks reflection iterations
- `max_reflections`: Limits reflection depth

#### Example Usage:
```python
from mcp_arena.agent import create_reflection_agent

# Create agent with configuration
agent = create_reflection_agent(
    memory_type="conversation",      # Track conversation history
    max_reflections=3                 # Stop after 3 reflection cycles
)

# Process a request
response = agent.process(
    "Explain quantum computing concepts clearly for beginners"
)

print(response)  # Returns refined, well-thought response
```

---

### 2. **ReAct Agent** - Reasoning + Acting Loop

The **ReAct Agent** implements the "Reasoning + Acting" paradigm. It cycles through thinking about what to do, executing actions (using tools), and observing results until it solves the problem.

#### Use Cases:
- Tool usage and execution (calculations, file operations, API calls)
- Step-by-step problem solving
- Data gathering and processing
- Interactive task execution
- Questions requiring research and computation

#### How It Works:
```
Think (Reason about what to do)
        ↓
    Act (Execute action/use tool)
        ↓
    Observe (Get results)
        ↓
    Should Continue? → Yes → Think Again
        ↓ No
    Return Final Observation
```

#### State Components:
- `thought`: Current reasoning about next action
- `action`: The action to execute
- `observation`: Result from executing action
- `step_count`: Tracks number of iterations
- `max_steps`: Maximum iterations allowed

#### Example Usage:
```python
from mcp_arena.agent import create_react_agent, CalculatorTool, SearchTool

# Create agent with tools
agent = create_react_agent(
    memory_type="conversation",
    max_steps=10                      # Max 10 think-act-observe cycles
)

# Add tools for agent to use
agent.add_tool(CalculatorTool())
agent.add_tool(SearchTool(your_search_function))

# Process complex request requiring tools
response = agent.process(
    "What is the population of France? Multiply it by 2 and tell me the result"
)

# Agent will:
# 1. Think: "I need to search for France's population"
# 2. Act: Call SearchTool with "France population"
# 3. Observe: Gets population data
# 4. Think: "Now I need to multiply this by 2"
# 5. Act: Call CalculatorTool with multiplication
# 6. Observe: Gets result
# 7. Return final answer
```

---

### 3. **Planning Agent** - Goal-Oriented Execution

The **Planning Agent** understands a goal, creates a detailed plan, executes each step, and evaluates progress. It's ideal for complex, multi-step objectives.

#### Use Cases:
- Project planning and management
- Complex workflow orchestration
- Goal decomposition
- Sequential task execution
- Strategy development
- Software development planning

#### How It Works:
```
Understand Goal
        ↓
    Create Plan (Break into steps)
        ↓
    Execute Step
        ↓
    Evaluate Progress
        ↓
    Should Continue? → Yes → Execute Next Step
        ↓ No or Replan
    Return Results
```

#### State Components:
- `goal`: The high-level objective
- `plan`: List of steps to achieve goal
- `current_step`: Which step we're on
- `completed_steps`: Steps finished so far
- `context`: Contextual information

#### Example Usage:
```python
from mcp_arena.agent import create_planning_agent

# Create agent with episodic memory (better for long-term planning)
agent = create_planning_agent(
    memory_type="episodic"            # Remembers past episodes/plans
)

# Process a complex goal
response = agent.process(
    "Plan a complete software development project for a web application. " +
    "Include architecture, tech stack selection, development phases, " +
    "testing strategy, and deployment approach"
)

# Agent will:
# 1. Understand the goal clearly
# 2. Break it into phases: Design, Development, Testing, Deployment
# 3. Execute each phase step by step
# 4. Track progress and adjust if needed
```

---

## Core Architecture

### Interface-Based Design

The system uses interfaces to define contracts for extensibility:

#### `IAgent` - Main Agent Interface
```python
class IAgent(ABC):
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize agent with configuration"""
    
    def process(self, input_data: Any) -> Any:
        """Process input and return response"""
    
    def get_compiled_graph(self) -> CompiledStateGraph:
        """Get the LangGraph workflow"""
    
    def add_tool(self, tool: IAgentTool) -> None:
        """Add tools to agent"""
    
    def set_memory(self, memory: IAgentMemory) -> None:
        """Configure memory system"""
```

#### `IAgentState` - State Management
```python
class IAgentState(ABC):
    def get_messages(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
    
    def add_message(self, message: Dict[str, Any]) -> None:
        """Add message to state"""
    
    def get_context(self) -> Dict[str, Any]:
        """Get contextual information"""
```

#### `IAgentTool` - Tool Abstraction
```python
class IAgentTool(ABC):
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with given arguments"""
    
    def get_description(self) -> str:
        """Describe what this tool does"""
    
    def get_schema(self) -> Dict[str, Any]:
        """Define input schema for the tool"""
```

#### `IAgentMemory` - Memory Backend
```python
class IAgentMemory(ABC):
    def store(self, key: str, value: Any) -> None:
        """Store data in memory"""
    
    def retrieve(self, key: str) -> Optional[Any]:
        """Retrieve data from memory"""
    
    def clear(self) -> None:
        """Clear all memory"""
```

### Class Hierarchy
```
BaseAgent (extends StateGraph from LangGraph)
    ├── ReflectionAgent (implements IAgent)
    ├── ReactAgent (implements IAgent)
    └── PlanningAgent (implements IAgent)

All agents maintain:
    - tools: List of available tools
    - memory: Memory backend
    - policies: Safety/validation policies
    - config: Configuration dictionary
```

---

## How to Use Agents

### Method 1: Direct Creation with Helper Functions

```python
from mcp_arena.agent import (
    create_reflection_agent,
    create_react_agent,
    create_planning_agent
)

# Reflection Agent
reflection_agent = create_reflection_agent(
    memory_type="conversation",
    max_reflections=2
)
result = reflection_agent.process("Your prompt here")

# ReAct Agent
react_agent = create_react_agent(
    memory_type="conversation",
    max_steps=10
)
result = react_agent.process("Your prompt here")

# Planning Agent
planning_agent = create_planning_agent(
    memory_type="episodic"
)
result = planning_agent.process("Your prompt here")
```

### Method 2: Using Factory Pattern

The `AgentFactory` provides a centralized way to create and configure agents:

```python
from mcp_arena.agent.factory import AgentFactory, AgentBuilder

# Initialize factory
factory = AgentFactory()

# List available agent types
available_agents = factory.list_agent_types()
# Returns: ["reflection", "react", "planning"]

# Create agent via factory
agent = factory.create_agent(
    "react",
    config={
        "memory_type": "conversation",
        "max_steps": 15
    }
)

result = agent.process("Your query")
```

### Method 3: Builder Pattern (Recommended for Complex Setups)

The `AgentBuilder` provides a fluent API for clean configuration:

```python
from mcp_arena.agent.factory import AgentBuilder
from mcp_arena.agent.tools import CalculatorTool, SearchTool

# Fluent configuration
agent = (AgentBuilder("react")
    .with_memory("conversation", max_history=100)
    .with_tool(CalculatorTool())
    .with_tool(SearchTool(search_func))
    .with_config(max_steps=15, temperature=0.7)
    .build())

# Use agent
response = agent.process("Calculate 2^10 and search for Bitcoin")
```

### Method 4: Advanced Configuration with Policies

```python
from mcp_arena.agent.factory import AgentBuilder
from mcp_arena.agent.policies import ContentFilterPolicy

agent = (AgentBuilder("planning")
    .with_memory("episodic")
    .with_tool(FileSystemTool())
    .with_policy(ContentFilterPolicy(
        disallowed_keywords=["malware", "exploit"],
        action="reject"
    ))
    .build())

response = agent.process("Plan a secure file management system")
```

---

## Configuration & Memory

### Memory Types

#### 1. **SimpleMemory**
Minimal in-memory storage for transient data.

```python
from mcp_arena.agent.memory import SimpleMemory

memory = SimpleMemory()
memory.store("key", "value")
value = memory.retrieve("key")
memory.clear()
```

**Use Cases**: Quick tests, single-request scenarios

---

#### 2. **ConversationMemory**
Maintains conversation history with context windows.

```python
from mcp_arena.agent.memory import ConversationMemory

memory = ConversationMemory(max_history=100)  # Keep last 100 turns

# Automatically track conversations
memory.add_conversation_turn(
    user_input="Hello",
    agent_response="Hi there!",
    metadata={"context": "greeting"}
)

# Get recent context for LLM
context = memory.get_recent_context(num_turns=5)  # Last 5 exchanges
history = memory.get_conversation_history()
```

**Use Cases**: Multi-turn conversations, chatbots, customer service

---

#### 3. **EpisodicMemory**
Stores discrete episodes with semantic search capabilities.

```python
from mcp_arena.agent.memory import EpisodicMemory

memory = EpisodicMemory()

# Store episodes (past experiences)
episode_id = memory.add_episode({
    "content": "Successfully implemented authentication system",
    "outcome": "success",
    "tools_used": ["CalculatorTool", "FileSystemTool"],
    "timestamp": "2025-12-31"
})

# Search similar episodes
similar = memory.search_episodes("authentication implementation", limit=5)

# Retrieve specific episode
episode = memory.get_episode(episode_id)
```

**Use Cases**: Long-term learning, planning agents, project management

---

### Memory Factory

```python
from mcp_arena.agent.memory import MemoryFactory

# Create memory by type
conversation_mem = MemoryFactory.create_memory("conversation", max_history=50)
episodic_mem = MemoryFactory.create_memory("episodic")
simple_mem = MemoryFactory.create_memory("simple")
```

### Configuration Dictionary

All agents accept configuration through `config` dict:

```python
config = {
    "llm": your_llm_instance,           # LLM to use
    "memory_type": "conversation",      # Memory backend type
    "max_steps": 10,                    # For ReAct agents
    "max_reflections": 3,               # For Reflection agents
    "temperature": 0.7,                 # Sampling temperature
    "top_p": 0.9,                       # Top-p sampling
    "tools": [tool1, tool2],           # Available tools
}

agent = factory.create_agent("react", config=config)
```

---

## Tools System

### Built-in Tools

#### CalculatorTool
```python
from mcp_arena.agent.tools import CalculatorTool

calc = CalculatorTool()
# Agent can automatically call this for math
result = calc.execute("(15 * 8) + (9 / 3)")  # Returns: 123.0
```

#### SearchTool
```python
from mcp_arena.agent.tools import SearchTool

def my_search(query):
    # Your search implementation
    return ["Result 1", "Result 2"]

search = SearchTool(search_function=my_search)
results = search.execute("quantum computing")
```

#### FileSystemTool
```python
from mcp_arena.agent.tools import FileSystemTool

fs = FileSystemTool()
# Agent can read/write/delete files
content = fs.execute("read", "/path/to/file.txt")
```

### Creating Custom Tools

Inherit from `BaseTool` and implement abstract methods:

```python
from mcp_arena.agent.tools import BaseTool
from mcp_arena.agent.interfaces import IAgentTool

class DatabaseQueryTool(BaseTool):
    def __init__(self, db_connection):
        super().__init__(
            name="database",
            description="Execute SQL queries on the database",
            schema={
                "query": "string",
                "type": "sql query",
                "required": ["query"]
            }
        )
        self.db = db_connection
    
    def execute(self, query: str, **kwargs) -> str:
        """Execute the query and return results"""
        try:
            results = self.db.execute(query)
            return str(results)
        except Exception as e:
            return f"Error: {str(e)}"
    
    def get_description(self) -> str:
        return self.description
    
    def get_schema(self) -> dict:
        return self.schema

# Use it
db_tool = DatabaseQueryTool(your_db)
agent.add_tool(db_tool)
```

### Tool Registry

```python
from mcp_arena.agent.tools import tool_registry

# Register custom tools globally
tool_registry.register("my_tool", DatabaseQueryTool)

# Retrieve registered tools
tool = tool_registry.get("my_tool")
```

---

## State Management

Each agent type has a specialized state class:

### ReactAgentState
```python
from mcp_arena.agent.state import ReactAgentState

state = ReactAgentState()

# Add thought-action-observation cycle
state.add_thought("I need to calculate the result")
state.add_action("calculate(15 * 8)")
state.add_observation("Result is 120")

# Check step limits
state.increment_step()
if state.is_max_steps_reached():
    # Stop execution
    pass

# Access messages
messages = state.get_messages()
```

### ReflectionAgentState
```python
from mcp_arena.agent.state import ReflectionAgentState

state = ReflectionAgentState()

# Initial response generation
state.set_initial_response("Initial answer")

# Reflection cycle
state.add_reflection("This could be improved by...")
state.set_refined_response("Improved answer")

# Check if more reflection needed
if state.can_reflect_more():
    # Continue reflecting
    pass
```

### PlanningAgentState
```python
from mcp_arena.agent.state import PlanningAgentState

state = PlanningAgentState()

# Goal and plan
state.set_goal("Build a web application")
state.set_plan([
    "Design architecture",
    "Set up project structure",
    "Implement core features",
    "Add testing",
    "Deploy to production"
])

# Track progress
current = state.get_current_step()  # "Design architecture"
state.complete_current_step()

# Check completion
if state.is_plan_complete():
    # Plan finished
    pass
```

---

## Policies System

### Validation and Safety

Policies allow you to add validation and safety constraints:

```python
from mcp_arena.agent.interfaces import IAgentPolicy
from mcp_arena.agent.policies import ContentFilterPolicy, SafetyPolicy

class CustomValidationPolicy(IAgentPolicy):
    def validate_action(self, action: dict) -> bool:
        """Return True if action is allowed"""
        if action.get("tool") == "dangerous_tool":
            return False
        return True
    
    def filter_response(self, response) -> str:
        """Modify response if needed"""
        return response.upper()

# Use policies
agent.add_policy(CustomValidationPolicy())
agent.add_policy(SafetyPolicy())
agent.add_policy(ContentFilterPolicy(
    disallowed_keywords=["malware", "exploit"],
    action="reject"  # or "warn", "filter"
))
```

---

## Best Practices

### 1. **Choose the Right Agent Type**

| Task Type | Best Agent |
|-----------|-----------|
| Simple Q&A, explanation | Reflection Agent |
| Multi-step problems, tools needed | ReAct Agent |
| Complex projects, long-term goals | Planning Agent |
| Unknown requirement | Start with ReAct (most flexible) |

### 2. **Memory Selection**

```python
# For short, single conversations
agent = create_reflection_agent(memory_type="simple")

# For ongoing conversations with context
agent = create_react_agent(memory_type="conversation")

# For learning from past experiences
agent = create_planning_agent(memory_type="episodic")
```

### 3. **Tool Organization**

```python
# Bad: Adding irrelevant tools
agent.add_tool(CalculatorTool())  # Not needed for text generation

# Good: Add only relevant tools
agent = AgentBuilder("react") \
    .with_tool(SearchTool(search_func)) \
    .with_tool(WebScraperTool()) \
    .build()  # For information gathering
```

### 4. **Configuration Tuning**

```python
# For quick, simple tasks
config = {"max_steps": 3, "max_reflections": 1}

# For complex problems needing thorough analysis
config = {"max_steps": 20, "max_reflections": 5}

# For safety-critical applications
config = {
    "max_steps": 10,
    "policies": [SafetyPolicy(), ContentFilterPolicy()]
}
```

### 5. **Error Handling**

```python
from mcp_arena.agent.factory import AgentFactory

factory = AgentFactory()

try:
    agent = factory.create_agent("invalid_type")
except ValueError as e:
    print(f"Invalid agent type: {e}")

try:
    result = agent.process(None)
except Exception as e:
    print(f"Processing error: {e}")
    # Fall back to simpler agent type
    agent = create_reflection_agent()
    result = agent.process(original_input)
```

### 6. **Monitoring and Logging**

```python
# Access internal state for monitoring
agent = create_react_agent()
graph = agent.get_compiled_graph()

# Track execution
result = agent.process("Your query")

# Check state for debugging
state = agent.state
print(f"Steps taken: {state.step_count}")
print(f"Messages: {state.get_messages()}")
print(f"Context: {state.get_context()}")
```

### 7. **Extensibility**

```python
# Create custom agent by extending base
from mcp_arena.agent.base import BaseAgent
from mcp_arena.agent.interfaces import IAgent

class CustomAgent(BaseAgent, IAgent):
    def __init__(self):
        super().__init__(CustomAgentState)
        self._build_graph()
    
    def _build_graph(self):
        # Define your workflow
        self.add_node("step1", self._step1)
        self.add_node("step2", self._step2)
        self.add_edge(START, "step1")
        self.add_edge("step1", "step2")
        self.add_edge("step2", END)
    
    def process(self, input_data):
        return self.get_compiled_graph().invoke(input_data)
    
    # Implement other IAgent methods...
```

### 8. **Performance Optimization**

```python
# Cache frequently used agents
class AgentCache:
    def __init__(self):
        self._agents = {}
    
    def get_agent(self, agent_type: str):
        if agent_type not in self._agents:
            factory = AgentFactory()
            self._agents[agent_type] = factory.create_agent(agent_type)
        return self._agents[agent_type]

# Usage
cache = AgentCache()
agent = cache.get_agent("react")  # Reuses same instance
```

---

## Summary

The MCPForge agent system provides a powerful, flexible framework for building intelligent agents:

- **Reflection Agents** for iterative quality improvement
- **ReAct Agents** for tool-based problem solving
- **Planning Agents** for goal-oriented execution

Use the **builder pattern** for complex configurations, select appropriate **memory types**, add relevant **tools**, and apply **policies** for safety. Each agent type excels at different problem types, so match your use case accordingly.

For questions about specific agent types or integration with other MCPForge components, refer to the example files in `mcp_arena/examples/agent_examples.py`.
