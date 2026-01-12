# MCPForge Tools System: Comprehensive Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [Tool Types](#tool-types)
3. [Agent Tools (BaseTool)](#agent-tools-basetool)
4. [MCP Tools (BaseMCPTool)](#mcp-tools-basemcptool)
5. [Tool Registry](#tool-registry)
6. [Creating Custom Tools](#creating-custom-tools)
7. [Tool Integration with Agents](#tool-integration-with-agents)
8. [Best Practices](#best-practices)

---

## Overview

The MCPForge tools system provides two distinct but complementary tool frameworks:

1. **Agent Tools (BaseTool)** - Direct tools integrated with agents for task execution
2. **MCP Tools (BaseMCPTool)** - Tools that wrap MCP server capabilities

Both follow the interface pattern and can be composed together for powerful agent capabilities.

---

## Tool Types

### 1. **Agent Tools** (Direct Integration)
Tools that agents can directly call during execution. These are lightweight, stateless, and can be easily composed.

**Location**: `mcp_arena/agent/tools.py`  
**Base Class**: `BaseTool` (implements `IAgentTool`)

### 2. **MCP Tools** (Server-Based)
Tools that bridge to MCP server functionality. These connect agents to external services and systems.

**Location**: `mcp_arena/tools/`  
**Base Class**: `BaseMCPTool`

---

## Agent Tools (BaseTool)

### Interface: IAgentTool

```python
class IAgentTool(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Execute the tool with given arguments"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get tool description"""
        pass
    
    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """Get tool schema"""
        pass
```

### Built-in Agent Tools

#### 1. **CalculatorTool**
Performs safe mathematical calculations without executing arbitrary code.

**What It Does**:
- Evaluates mathematical expressions safely
- Supports: addition, subtraction, multiplication, division, power, modulo
- Uses AST (Abstract Syntax Tree) for safe evaluation

**Example Usage**:
```python
from mcp_arena.agent.tools import CalculatorTool

calc = CalculatorTool()

# Direct execution
result = calc.execute("(15 * 8) + (9 / 3)")  # Returns: "123.0"
result = calc.execute("2 ** 10")              # Returns: "1024"
result = calc.execute("100 % 7")              # Returns: "2"

# Get tool info
description = calc.get_description()
# Returns: "calculator: Perform mathematical calculations"

schema = calc.get_schema()
# Returns: {"expression": "string", "type": "mathematical expression"}
```

**Integration with ReAct Agent**:
```python
from mcp_arena.agent import create_react_agent
from mcp_arena.agent.tools import CalculatorTool

agent = create_react_agent(memory_type="conversation", max_steps=10)
agent.add_tool(CalculatorTool())

response = agent.process("Calculate the area of a circle with radius 5. Use π as 3.14159")
# Agent will think: "Need to calculate π * r²"
# Agent will act: "calculator.execute('3.14159 * 5 * 5')"
# Agent will observe: "78.53975"
```

**Supported Operations**:
```python
calc = CalculatorTool()

# Arithmetic
calc.execute("10 + 5")      # Addition
calc.execute("10 - 5")      # Subtraction
calc.execute("10 * 5")      # Multiplication
calc.execute("10 / 5")      # Division (float division)
calc.execute("2 ** 8")      # Power/exponentiation
calc.execute("17 % 5")      # Modulo

# Unary operations
calc.execute("-42")         # Negation

# Complex expressions
calc.execute("((10 + 5) * 2) - 3")
```

**Error Handling**:
```python
result = calc.execute("1 / 0")  
# Returns: "Calculation error: division by zero"

result = calc.execute("invalid syntax @#$")
# Returns: "Calculation error: invalid syntax (<unknown>, line 1)"
```

---

#### 2. **FileSystemTool**
Performs file and directory operations within a safe base path.

**What It Does**:
- Read file contents
- Write/create files
- List directory contents
- Check file/directory existence

**Constructor Parameters**:
```python
FileSystemTool(base_path: str = ".")
# base_path: Root directory for all operations (prevents access outside this path)
```

**Operations**:

```python
from mcp_arena.agent.tools import FileSystemTool

fs = FileSystemTool(base_path="/my/safe/directory")

# READ operation
content = fs.execute("read", "documents/file.txt")
# Returns: File contents as string or error message

# WRITE operation
result = fs.execute("write", "output.txt", content="Hello World")
# Returns: "Successfully wrote to: /my/safe/directory/output.txt"

# LIST operation
contents = fs.execute("list", "documents/")
# Returns: Directory listing with all files and folders

# EXISTS operation
exists = fs.execute("exists", "myfile.txt")
# Returns: "Path exists: True/False"
```

**Schema**:
```python
{
    "operation": "string",      # read, write, list, exists
    "path": "string",           # Relative path from base_path
    "content": "string (optional)"  # For write operations
}
```

**Example with Agent**:
```python
from mcp_arena.agent import create_react_agent
from mcp_arena.agent.tools import FileSystemTool

agent = create_react_agent(memory_type="conversation", max_steps=10)
agent.add_tool(FileSystemTool(base_path="/home/user/projects"))

response = agent.process("Read the README.md file and summarize it")
# Agent will:
# 1. Think: "Need to read README.md file"
# 2. Act: "filesystem.execute('read', 'README.md')"
# 3. Observe: Gets file content
# 4. Think: "Now summarize the content"
# 5. Return: Summary of the file
```

**Error Handling**:
```python
fs = FileSystemTool(base_path="/safe")

result = fs.execute("read", "nonexistent.txt")
# Returns: "File not found: /safe/nonexistent.txt"

result = fs.execute("list", "/outside/path")
# Returns: "Directory not found: /safe//outside/path"

result = fs.execute("invalid_op", "file.txt")
# Returns: "Unsupported operation: invalid_op"
```

---

#### 3. **SearchTool**
Performs searches using a custom search function.

**What It Does**:
- Executes searches using provided callback function
- Returns results as list
- Handles exceptions gracefully

**Constructor**:
```python
SearchTool(search_function: Callable[[str], List[str]])
# search_function: Function that takes query string and returns list of results
```

**Example Usage**:
```python
from mcp_arena.agent.tools import SearchTool

# Define your search implementation
def my_search(query: str) -> List[str]:
    # Implementation could:
    # - Query a database
    # - Call an API
    # - Search local documents
    # - Use a search engine
    results = [f"Result about {query} #1", f"Result about {query} #2"]
    return results

search = SearchTool(search_function=my_search)

# Use it
results = search.execute("machine learning")
# Returns: ["Result about machine learning #1", "Result about machine learning #2"]
```

**Real-World Example - Web Search Integration**:
```python
import requests
from mcp_arena.agent.tools import SearchTool

def web_search(query: str) -> List[str]:
    """Search the web (example using a hypothetical API)"""
    try:
        response = requests.get(
            "https://api.example.com/search",
            params={"q": query},
            timeout=5
        )
        data = response.json()
        return [item["title"] for item in data["results"][:5]]
    except Exception as e:
        return [f"Search error: {str(e)}"]

search_tool = SearchTool(search_function=web_search)

# Add to agent
agent.add_tool(search_tool)
```

**Database Search Example**:
```python
from mcp_arena.agent.tools import SearchTool

def database_search(query: str) -> List[str]:
    """Search a database"""
    # Assume we have a database connection
    results = db.query(f"SELECT * FROM documents WHERE content LIKE '%{query}%'")
    return [r["content"] for r in results]

search_tool = SearchTool(search_function=database_search)
agent.add_tool(search_tool)
```

---

#### 4. **WebTool**
Performs web operations like fetching content and headers.

**What It Does**:
- Fetch webpage content (first 2000 characters)
- Get HTTP headers from URLs

**Operations**:

```python
from mcp_arena.agent.tools import WebTool

web = WebTool()

# FETCH operation - Get webpage content
content = web.execute("fetch", "https://example.com")
# Returns: First 2000 characters of HTML content

# HEADERS operation - Get HTTP headers
headers = web.execute("headers", "https://example.com")
# Returns: String representation of headers dict
```

**Example with Agent**:
```python
from mcp_arena.agent import create_react_agent
from mcp_arena.agent.tools import WebTool

agent = create_react_agent(memory_type="conversation")
agent.add_tool(WebTool())

response = agent.process("What is the main topic of the webpage at https://example.com?")
# Agent will fetch the page and analyze content
```

**Error Handling**:
```python
web = WebTool()

result = web.execute("fetch", "https://nonexistent-domain-xyz.com")
# Returns: "Web operation error: [appropriate error message]"

result = web.execute("invalid_op", "https://example.com")
# Returns: "Unsupported web operation: invalid_op"
```

---

#### 5. **DataAnalysisTool**
Performs basic data analysis and summarization.

**What It Does**:
- Text summarization (word/character/line counts)
- List summarization (item counts)
- Statistics on numeric data (mean, median, min, max)

**Operations**:

```python
from mcp_arena.agent.tools import DataAnalysisTool

data_tool = DataAnalysisTool()

# SUMMARIZE operation - Text
text_summary = data_tool.execute(
    "summarize",
    "The quick brown fox jumps over the lazy dog"
)
# Returns: "Text summary: 8 words, 44 characters, 1 lines"

# SUMMARIZE operation - List
list_summary = data_tool.execute("summarize", ["item1", "item2", "item3"])
# Returns: "List summary: 3 items"

# STATISTICS operation - Numeric list
stats = data_tool.execute("statistics", [1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
# Returns: {
#     "count": 10,
#     "mean": 5.5,
#     "median": 5.5,
#     "min": 1,
#     "max": 10
# }
```

**Example with Agent**:
```python
from mcp_arena.agent import create_react_agent
from mcp_arena.agent.tools import DataAnalysisTool

agent = create_react_agent()
agent.add_tool(DataAnalysisTool())

# Analyze data
response = agent.process("Analyze these numbers: 10, 20, 30, 40, 50. Get statistics.")
# Agent will use data analysis tool to compute mean, median, etc.
```

---

### BaseTool: Creating Custom Tools

Inherit from `BaseTool` to create custom tools:

```python
from mcp_arena.agent.tools import BaseTool
from mcp_arena.agent.interfaces import IAgentTool

class MyCustomTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="my_tool",
            description="Description of what my tool does",
            schema={
                "param1": "string",
                "param2": "integer",
                "type": "description of parameters"
            }
        )
    
    def execute(self, param1: str, param2: int, **kwargs) -> str:
        """Execute the tool"""
        try:
            # Your implementation here
            result = f"Processed {param1} with value {param2}"
            return result
        except Exception as e:
            return f"Error: {str(e)}"
```

**Complete Example - Email Tool**:

```python
from mcp_arena.agent.tools import BaseTool
import smtplib
from email.mime.text import MIMEText

class EmailTool(BaseTool):
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        super().__init__(
            name="email",
            description="Send emails via SMTP",
            schema={
                "to": "string (email address)",
                "subject": "string",
                "body": "string",
                "type": "email parameters"
            }
        )
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def execute(self, to: str, subject: str, body: str, **kwargs) -> str:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = self.username
            msg['To'] = to
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            return f"Email sent to {to}"
        except Exception as e:
            return f"Email error: {str(e)}"

# Usage
email_tool = EmailTool(
    smtp_server="smtp.gmail.com",
    smtp_port=587,
    username="your-email@gmail.com",
    password="your-password"
)

agent.add_tool(email_tool)
```

---

## MCP Tools (BaseMCPTool)

MCP Tools act as bridges between agents and MCP servers, allowing agents to leverage external service capabilities.

### What is BaseMCPTool?

```python
class BaseMCPTool:
    def __init__(self, mcp_server: BaseMCPServer):
        self.server = mcp_server
    
    def get_list_of_tools(self) -> List[Tool]:
        """Get all tools available from the MCP server"""
        return self.server.mcp_server.list_tools()
    
    def remove_tool(self, name: str):
        """Remove a tool from the server"""
        return self.server.mcp_server.remove_tool(name)
    
    def call_tool(self, name: str):
        """Call a tool on the MCP server"""
        return self.server.mcp_server.call_tool(name)
```

### Available MCP Tool Wrappers

Located in `mcp_arena/tools/`, these wrap MCP servers:

1. **GithubMCPTools** - GitHub operations via MCP
2. **LocalOperationsMCPTools** - Local system operations via MCP
3. **VectorDBMCPTools** - Vector database operations via MCP

### Example Usage

```python
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.tools.github import GithubMCPTools

# Create GitHub MCP server
github_server = GithubMCPServer(token="your_github_token")

# Wrap with MCP tools
github_tools = GithubMCPTools(github_server)

# Get available tools from server
tools = github_tools.get_list_of_tools()
for tool in tools:
    print(f"Tool: {tool.name} - {tool.description}")

# Call a specific tool
result = github_tools.call_tool("list_repositories")
```

---

## Tool Registry

The `ToolRegistry` provides centralized management of tools.

### ToolRegistry API

```python
from mcp_arena.agent.tools import tool_registry, ToolRegistry

class ToolRegistry:
    def register_tool(self, name: str, tool_class: type) -> None:
        """Register a tool class"""
        pass
    
    def create_tool(self, name: str, **kwargs) -> IAgentTool:
        """Create an instance of a registered tool"""
        pass
    
    def get_tool(self, name: str) -> Optional[IAgentTool]:
        """Get an existing tool instance"""
        pass
    
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        pass
    
    def create_default_tools(self) -> List[IAgentTool]:
        """Create a set of default tools"""
        pass
```

### Pre-Registered Tools

By default, the global `tool_registry` has:
- `calculator` → `CalculatorTool`
- `filesystem` → `FileSystemTool`
- `web` → `WebTool`
- `data_analysis` → `DataAnalysisTool`

### Using the Registry

```python
from mcp_arena.agent.tools import tool_registry

# List available tools
available = tool_registry.list_tools()
print(available)  # ['calculator', 'filesystem', 'web', 'data_analysis']

# Create a tool
calculator = tool_registry.create_tool("calculator")
result = calculator.execute("5 * 5")  # "25"

# Get previously created tool
same_calculator = tool_registry.get_tool("calculator")

# Create all default tools
all_tools = tool_registry.create_default_tools()
```

### Registering Custom Tools

```python
from mcp_arena.agent.tools import tool_registry, BaseTool

class DatabaseQueryTool(BaseTool):
    def __init__(self):
        super().__init__(
            name="database",
            description="Query the database",
            schema={"query": "SQL query string"}
        )
    
    def execute(self, query: str, **kwargs):
        # Implementation
        pass

# Register the tool
tool_registry.register_tool("database", DatabaseQueryTool)

# Now create it
db_tool = tool_registry.create_tool("database")
```

---

## Creating Custom Tools

### Step 1: Define the Tool Class

```python
from mcp_arena.agent.tools import BaseTool

class TranslationTool(BaseTool):
    def __init__(self, api_key: str):
        super().__init__(
            name="translation",
            description="Translate text between languages",
            schema={
                "text": "string (text to translate)",
                "from_lang": "string (source language code)",
                "to_lang": "string (target language code)",
                "type": "translation parameters"
            }
        )
        self.api_key = api_key
    
    def execute(self, text: str, from_lang: str, to_lang: str, **kwargs) -> str:
        try:
            # Call translation API
            import requests
            response = requests.post(
                "https://api.example.com/translate",
                json={
                    "text": text,
                    "source_lang": from_lang,
                    "target_lang": to_lang
                },
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()["translated_text"]
            else:
                return f"Translation error: {response.status_code}"
        
        except Exception as e:
            return f"Translation failed: {str(e)}"
```

### Step 2: Add to Agent

```python
from mcp_arena.agent import create_react_agent

translation_tool = TranslationTool(api_key="your_key")

agent = create_react_agent(memory_type="conversation")
agent.add_tool(translation_tool)

response = agent.process("Translate 'Hello World' to Spanish")
```

### Step 3: Register (Optional)

```python
from mcp_arena.agent.tools import tool_registry

tool_registry.register_tool("translation", TranslationTool)

# Later, create it from registry
tool = tool_registry.create_tool("translation", api_key="your_key")
```

---

## Tool Integration with Agents

### Adding Tools to ReAct Agent

```python
from mcp_arena.agent import create_react_agent
from mcp_arena.agent.tools import CalculatorTool, FileSystemTool, SearchTool

agent = create_react_agent(
    memory_type="conversation",
    max_steps=15
)

# Add individual tools
agent.add_tool(CalculatorTool())
agent.add_tool(FileSystemTool(base_path="/data"))
agent.add_tool(SearchTool(search_function=my_search_func))

# Process task requiring multiple tools
response = agent.process(
    "Find the sales data in 'data/sales.txt', " +
    "calculate the total revenue, " +
    "and search for relevant industry reports"
)
```

### Using Builder Pattern with Tools

```python
from mcp_arena.agent.factory import AgentBuilder
from mcp_arena.agent.tools import CalculatorTool, WebTool, FileSystemTool

agent = (AgentBuilder("react")
    .with_memory("conversation", max_history=100)
    .with_tool(CalculatorTool())
    .with_tool(WebTool())
    .with_tool(FileSystemTool(base_path="/workspace"))
    .with_config(max_steps=12)
    .build())

response = agent.process("Your complex task here")
```

### Using with ReflectionAgent

Tools work primarily with ReAct agents, but can be used with reflection agents for information gathering:

```python
from mcp_arena.agent import create_reflection_agent
from mcp_arena.agent.tools import SearchTool

agent = create_reflection_agent(
    memory_type="conversation",
    max_reflections=3
)

# Add search tool for information gathering
agent.add_tool(SearchTool(search_function=research_function))

response = agent.process(
    "Write a comprehensive article on quantum computing. " +
    "Use the search tool to find relevant information."
)
```

---

## Best Practices

### 1. **Choose Right Tools for the Task**

```python
# Good: Match tools to requirements
# For calculating: Use CalculatorTool
# For files: Use FileSystemTool
# For research: Use SearchTool

agent = create_react_agent()
agent.add_tool(CalculatorTool())      # If doing calculations
agent.add_tool(FileSystemTool())      # If managing files
agent.add_tool(SearchTool(search))    # If researching

# Bad: Adding irrelevant tools
agent.add_tool(CalculatorTool())      # Not needed for text generation
```

### 2. **Secure Tool Parameters**

```python
import os

# Bad: Hardcoding secrets
email_tool = EmailTool(
    smtp_server="smtp.gmail.com",
    username="user@example.com",
    password="hardcoded_password"  # NEVER do this
)

# Good: Use environment variables
email_tool = EmailTool(
    smtp_server="smtp.gmail.com",
    username=os.getenv("EMAIL_USER"),
    password=os.getenv("EMAIL_PASSWORD")
)
```

### 3. **Limit FileSystemTool Access**

```python
# Good: Restrict to safe directory
fs = FileSystemTool(base_path="/app/data")
# Can only access files under /app/data

# Bad: Unrestricted access
fs = FileSystemTool(base_path="/")  # Access to entire system
```

### 4. **Handle Tool Errors**

```python
from mcp_arena.agent import create_react_agent

agent = create_react_agent(memory_type="conversation")
agent.add_tool(WebTool())

try:
    result = agent.process("Fetch content from https://example.com")
except Exception as e:
    print(f"Agent processing error: {e}")
    # Fall back to reflection agent without web tool
    from mcp_arena.agent import create_reflection_agent
    fallback_agent = create_reflection_agent()
    result = fallback_agent.process("Your query")
```

### 5. **Tool Timeout and Limits**

```python
# For WebTool, note the 2000 character limit on page content
# For FileSystemTool, large files will consume memory
# For SearchTool, limit number of results

def limited_search(query: str, max_results: int = 5) -> List[str]:
    results = perform_search(query)
    return results[:max_results]  # Limit results

search_tool = SearchTool(search_function=limited_search)
```

### 6. **Document Custom Tools**

```python
class APICallTool(BaseTool):
    """
    Tool for making API calls to external services.
    
    Supported Operations:
    - GET: Fetch data
    - POST: Submit data
    - PUT: Update data
    
    Parameters:
    - method: HTTP method (GET, POST, PUT)
    - endpoint: API endpoint URL
    - data: Data to send (for POST/PUT)
    - headers: Custom HTTP headers
    
    Examples:
        Execute GET request:
        tool.execute("GET", "https://api.example.com/users")
        
        Execute POST request:
        tool.execute("POST", "https://api.example.com/data", 
                    data={"key": "value"})
    """
    def __init__(self, api_key: str):
        super().__init__(
            name="api_call",
            description=self.__doc__,
            schema={
                "method": "HTTP method (GET, POST, PUT, DELETE)",
                "endpoint": "API endpoint URL",
                "data": "Request data (optional)",
                "headers": "Custom headers (optional)"
            }
        )
        self.api_key = api_key
    
    def execute(self, method: str, endpoint: str, data=None, headers=None, **kwargs):
        # Implementation...
        pass
```

### 7. **Tool Composition**

```python
# Create agent with multiple complementary tools
agent = (AgentBuilder("react")
    .with_tool(SearchTool(web_search))        # Find information
    .with_tool(DataAnalysisTool())             # Analyze data
    .with_tool(FileSystemTool(base_path))     # Save results
    .with_tool(CalculatorTool())               # Calculate metrics
    .with_config(max_steps=20)
    .build())

# Single complex task using multiple tools
response = agent.process(
    "Search for market data, analyze trends, " +
    "calculate growth percentages, and save report to file"
)
```

### 8. **Testing Custom Tools**

```python
# Test tool in isolation
test_tool = MyCustomTool()

# Test basic execution
result = test_tool.execute(param1="test", param2=42)
assert result is not None

# Test error handling
result = test_tool.execute(param1="", param2=-1)
assert "error" in result.lower()

# Test schema
schema = test_tool.get_schema()
assert "param1" in schema
assert "param2" in schema

# Test description
desc = test_tool.get_description()
assert len(desc) > 0
```

---

## Summary

The MCPForge tools system provides:

- **5 Built-in Agent Tools**: Calculator, FileSystem, Search, Web, DataAnalysis
- **BaseTool Framework**: Easy custom tool creation
- **BaseMCPTool Framework**: Bridge to MCP servers
- **ToolRegistry**: Centralized tool management
- **Seamless Agent Integration**: Tools work naturally with agents

Use agent tools for direct capabilities, MCP tools for external services, and always choose tools that match your task requirements. Secure sensitive data, limit access appropriately, and test tools thoroughly before use in production.
