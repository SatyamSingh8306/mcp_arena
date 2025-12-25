import asyncio
import json
import threading
import subprocess
import os
import signal
import time
from typing import Dict, Any, List, Optional, Callable, Union, Type
from concurrent.futures import ThreadPoolExecutor
import atexit
import sys

from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_agent
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, BaseMessage

# Import from langchain_mcp_adapters
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient, StdioServerParameters, HttpServerParameters
    MCP_ADAPTERS_AVAILABLE = True
except ImportError:
    MCP_ADAPTERS_AVAILABLE = False
    print("Warning: langchain_mcp_adapters not installed. Install with: pip install langchain-mcp-adapters")


class MCPLangChainWrapper:
    """
    LangChain wrapper for MCP servers with automatic server management.
    
    This wrapper can:
    1. Start MCP server objects in the background
    2. Connect to existing MCP servers
    3. Create agents with any LLM model
    4. Handle multi-server scenarios
    """
    
    def __init__(
        self,
        servers: Optional[Dict[str, Any]] = None,
        auto_start: bool = True
    ):
        """
        Initialize the MCP LangChain wrapper.
        
        Args:
            servers: Dictionary of server configurations or BaseMCPServer instances
                Example: {
                    "s3": s3_server_instance,  # BaseMCPServer object
                    "math": math_server_instance,
                }
                OR
                {
                    "s3": {
                        "server": s3_server_instance,
                        "transport": "stdio",  # or "http"
                        "port": 8000,  # for http transport
                    }
                }
            auto_start: Whether to automatically start servers
        """
        if not MCP_ADAPTERS_AVAILABLE:
            raise ImportError(
                "langchain_mcp_adapters is required. Install with: pip install langchain-mcp-adapters"
            )
        
        self.servers = servers or {}
        self.auto_start = auto_start
        self.mcp_client: Optional[MultiServerMCPClient] = None
        self.tools: List[BaseTool] = []
        self.server_processes: Dict[str, subprocess.Popen] = {}
        self.running_servers: Dict[str, Any] = {}
        self.server_threads: Dict[str, threading.Thread] = {}
        self.connected = False
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
    
    def add_server(self, name: str, server: Any, transport: str = "stdio", **kwargs):
        """Add a server to the wrapper."""
        if isinstance(server, dict):
            self.servers[name] = server
        else:
            self.servers[name] = {
                "server": server,
                "transport": transport,
                **kwargs
            }
        
        if self.connected:
            # If already connected, we need to reconnect
            self._restart_connection()
    
    def _restart_connection(self):
        """Restart the MCP client connection."""
        if self.connected:
            asyncio.run(self.disconnect())
            asyncio.run(self.connect())
    
    def _run_server_in_thread(self, server, name: str, transport: str = "stdio", port: int = None):
        """Run an MCP server in a separate thread."""
        try:
            print(f"Starting server '{name}' with transport '{transport}'...")
            
            if transport == "stdio":
                # Run with stdio transport
                server.run(transport="stdio")
            elif transport == "http":
                # Run with HTTP transport
                if port is None:
                    # Use the server's configured port
                    port = getattr(server, 'port', 8000)
                server.run(transport="sse")  # sse is the HTTP transport for FastMCP
            elif transport == "sse":
                server.run(transport="sse")
            else:
                raise ValueError(f"Unsupported transport: {transport}")
                
        except Exception as e:
            print(f"Server '{name}' error: {e}")
        finally:
            print(f"Server '{name}' stopped")
    
    async def _start_servers(self):
        """Start all MCP servers in background threads."""
        server_configs = {}
        
        for name, server_config in self.servers.items():
            try:
                # Extract server object and config
                if isinstance(server_config, dict):
                    server_obj = server_config.get("server")
                    transport = server_config.get("transport", "stdio")
                    port = server_config.get("port")
                else:
                    # Direct server object
                    server_obj = server_config
                    transport = "stdio"
                    port = None
                
                if server_obj is None:
                    print(f"Warning: No server object for '{name}'")
                    continue
                
                # Start server in a thread
                thread = threading.Thread(
                    target=self._run_server_in_thread,
                    args=(server_obj, name),
                    kwargs={"transport": transport, "port": port},
                    daemon=True,
                    name=f"MCP-Server-{name}"
                )
                thread.start()
                
                # Store thread reference
                self.server_threads[name] = thread
                
                # Wait for server to start
                time.sleep(3)
                
                # Configure for MultiServerMCPClient
                if transport == "stdio":
                    # For stdio, we need to create a script that imports and runs the server
                    server_configs[name] = self._create_stdio_config(server_obj, name)
                elif transport in ["http", "sse"]:
                    # For HTTP/SSE
                    url = f"http://localhost:{port or 8000}/mcp"
                    server_configs[name] = {
                        "transport": "http",
                        "url": url
                    }
                
                self.running_servers[name] = server_obj
                print(f"Server '{name}' started successfully")
                
            except Exception as e:
                print(f"Failed to start server '{name}': {e}")
                continue
        
        return server_configs
    
    def _create_stdio_config(self, server_obj, name: str) -> Dict:
        """
        Create a stdio configuration for a server object.
        
        This creates a temporary Python script that imports and runs the server.
        """
        # Get the module and class name
        module_name = server_obj.__class__.__module__
        class_name = server_obj.__class__.__name__
        
        # Create a temporary script
        import tempfile
        import uuid
        
        # Create a unique script name
        script_id = str(uuid.uuid4())[:8]
        script_content = f'''
import sys
import asyncio

# Import the server class
from {module_name} import {class_name}

# Create and run the server
if __name__ == "__main__":
    # Note: Since we can't serialize the existing instance,
    # we'll create a new one with similar parameters
    # In practice, you might want to pass configuration
    server = {class_name}(
        name="{server_obj.name}",
        description="{server_obj.description}",
        host="{server_obj.host}",
        port={server_obj.port},
        transport="stdio",
        debug={server_obj.debug}
    )
    
    # Run the server
    server.run(transport="stdio")
'''
        
        # Write to a temporary file
        temp_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            prefix=f'mcp_server_{name}_',
            delete=False
        )
        temp_file.write(script_content)
        temp_file.flush()
        temp_file.close()
        
        # Store the temp file path for cleanup
        if not hasattr(self, '_temp_files'):
            self._temp_files = []
        self._temp_files.append(temp_file.name)
        
        return {
            "transport": "stdio",
            "command": sys.executable,  # Use current Python interpreter
            "args": [temp_file.name]
        }
    
    async def connect(self):
        """Connect to MCP servers and load tools."""
        if self.connected:
            return
        
        if self.auto_start:
            # Start servers in background
            server_configs = await self._start_servers()
        else:
            # Use provided configurations
            server_configs = {}
            for name, config in self.servers.items():
                if isinstance(config, dict):
                    transport = config.get("transport", "stdio")
                    if transport == "stdio":
                        server_configs[name] = {
                            "transport": "stdio",
                            "command": config.get("command"),
                            "args": config.get("args", [])
                        }
                    elif transport == "http":
                        server_configs[name] = {
                            "transport": "http",
                            "url": config.get("url")
                        }
        
        if not server_configs:
            raise ValueError("No server configurations available")
        
        # Create MCP client
        self.mcp_client = MultiServerMCPClient(server_configs)
        
        # Get tools from all servers
        self.tools = await self.mcp_client.get_tools()
        
        self.connected = True
        print(f"Connected to {len(self.servers)} servers, loaded {len(self.tools)} tools")
    
    def get_tools(self) -> List[BaseTool]:
        """Get all loaded tools."""
        if not self.connected:
            raise RuntimeError("Not connected to servers. Call connect() first.")
        return self.tools
    
    def create_agent(
        self,
        llm: Union[str, BaseChatModel],
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Runnable:
        """
        Create an agent with the MCP tools using create_agent.
        
        Args:
            llm: Either a model name string or a BaseChatModel instance
            system_prompt: Optional custom system prompt
            **kwargs: Additional arguments for create_agent
            
        Returns:
            An agent runnable
        """
        if not self.connected:
            raise RuntimeError("Not connected to servers. Call connect() first.")
        
        tools = self.get_tools()
        
        # Create agent using langchain_mcp_adapters' create_agent
        agent = create_agent(
            llm,
            tools,
            system_prompt=system_prompt,
            **kwargs
        )
        
        return agent
    
    def create_react_agent(
        self,
        llm: BaseChatModel,
        system_prompt: Optional[str] = None,
        verbose: bool = True,
        **kwargs
    ) -> AgentExecutor:
        """
        Create a ReAct agent with the MCP tools.
        
        Args:
            llm: LangChain chat model instance
            system_prompt: Optional custom system prompt
            verbose: Whether to show agent thinking
            **kwargs: Additional arguments for AgentExecutor
            
        Returns:
            An AgentExecutor
        """
        if not self.connected:
            raise RuntimeError("Not connected to servers. Call connect() first.")
        
        tools = self.get_tools()
        
        # Create prompt
        if system_prompt is None:
            system_prompt = """You are a helpful assistant with access to tools.
            Use the tools to help answer the user's question.
            Always think step by step.
            
            Available tools:
            {tools}
            
            Use the following format:
            
            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Create ReAct agent
        agent = create_agent(
            llm=llm,
            tools=tools,
            prompt=prompt
        )
    
        return agent
    
    async def invoke_agent(
        self,
        agent: Runnable,
        user_input: str,
        chat_history: Optional[List[BaseMessage]] = None
    ) -> Dict[str, Any]:
        """
        Invoke an agent with a user input.
        
        Args:
            agent: The agent to invoke
            user_input: User's input message
            chat_history: Optional chat history
            
        Returns:
            Agent response
        """
        if chat_history is None:
            chat_history = []
        
        # Prepare input
        agent_input = {
            "messages": chat_history + [HumanMessage(content=user_input)]
        }
        
        # Invoke agent
        response = await agent.ainvoke(agent_input)
        
        return response
    
    async def chat_with_agent(
        self,
        agent: Runnable,
        initial_message: Optional[str] = None,
        system_prompt: Optional[str] = None
    ):
        """
        Start an interactive chat session with the agent.
        
        Args:
            agent: The agent to chat with
            initial_message: Optional initial message
            system_prompt: Optional system prompt
        """
        print("\n" + "="*50)
        print("MCP Agent Chat")
        print("="*50)
        print("Type 'quit' or 'exit' to end the chat.\n")
        
        if system_prompt:
            print(f"System: {system_prompt}\n")
        
        chat_history = []
        
        if initial_message:
            print(f"User: {initial_message}")
            response = await self.invoke_agent(agent, initial_message, chat_history)
            print(f"Assistant: {response.get('output', response)}")
            chat_history.extend([
                HumanMessage(content=initial_message),
                AIMessage(content=str(response.get('output', response)))
            ])
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Get agent response
                response = await self.invoke_agent(agent, user_input, chat_history)
                
                # Extract response text
                if isinstance(response, dict):
                    response_text = response.get('output', str(response))
                else:
                    response_text = str(response)
                
                print(f"\nAssistant: {response_text}")
                
                # Update chat history
                chat_history.extend([
                    HumanMessage(content=user_input),
                    AIMessage(content=response_text)
                ])
                
            except KeyboardInterrupt:
                print("\n\nChat interrupted.")
                break
            except Exception as e:
                print(f"\nError: {e}")
    
    async def disconnect(self):
        """Disconnect from MCP servers."""
        if not self.connected:
            return
        
        # Stop server threads
        for name, thread in self.server_threads.items():
            if thread.is_alive():
                # There's no clean way to stop a FastMCP server thread
                # We'll just let them be daemon threads
                pass
        
        # Close MCP client
        if self.mcp_client:
            # MultiServerMCPClient doesn't have a close method in current version
            # We'll just dereference it
            self.mcp_client = None
        
        # Clean up temp files
        if hasattr(self, '_temp_files'):
            for temp_file in self._temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
        
        self.connected = False
        print("Disconnected from MCP servers")
    
    def cleanup(self):
        """Clean up resources."""
        # Kill any remaining subprocesses
        for name, process in self.server_processes.items():
            try:
                process.terminate()
                process.wait(timeout=2)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        # Clean up temp files
        if hasattr(self, '_temp_files'):
            for temp_file in self._temp_files:
                try:
                    os.unlink(temp_file)
                except:
                    pass
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Example usage
async def example_usage():
    """Example showing how to use the MCP LangChain wrapper with BaseMCPServer objects."""
    
    # First, create your MCP server instances
    # Example with S3MCPServer (from your earlier code)
    from mcp_arena.presents import S3MCPServer
    # Create S3 MCP server
    s3_server = S3MCPServer(
        name="S3 Server",
        description="AWS S3 operations server",
        host="127.0.0.1",
        port=8001,  # Different port for HTTP transport
        transport="stdio",  # Will be overridden by wrapper
        auto_register_tools=True
    )
    
    # Create another server (e.g., Math server)
    from mcp.server.fastmcp import FastMCP
    
    math_server = FastMCP("Math Server")
    
    @math_server.tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b
    
    @math_server.tool()
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b
    
    # Create wrapper with servers
    wrapper = MCPLangChainWrapper(
        servers={
            "s3": {
                "server": s3_server,
                "transport": "stdio"  # Run with stdio transport
            },
            "math": {
                "server": math_server,
                "transport": "http",  # Run with HTTP transport
                "port": 8002  # Different port
            }
        },
        auto_start=True
    )
    
    try:
        # Connect to servers
        await wrapper.connect()
        
        # Get tools
        tools = wrapper.get_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Create agent with model name string
        agent = wrapper.create_agent(
            llm="gpt-4-turbo",  # Model name string
            system_prompt="You are a helpful assistant with access to S3 and math tools.",
            verbose=True
        )
        
        # Use the agent
        response = await wrapper.invoke_agent(
            agent,
            "List all S3 buckets and then add 5 and 3"
        )
        print(f"Response: {response}")
        
        # Or create agent with LangChain model instance
        from langchain_openai import ChatOpenAI
        
        llm_openai = ChatOpenAI(model="gpt-4-turbo")
        
        # Create ReAct agent
        react_agent = wrapper.create_react_agent(
            llm=llm_openai,
            system_prompt="You are an expert assistant. Think step by step and use tools when needed.",
            verbose=True,
            max_iterations=5
        )
        
        # Interactive chat
        await wrapper.chat_with_agent(
            react_agent,
            initial_message="Hello! I need help with my S3 buckets and some calculations.",
            system_prompt="You are a helpful assistant with S3 and math capabilities."
        )
        
    finally:
        # Clean up
        await wrapper.disconnect()


# Synchronous wrapper for convenience
class SyncMCPLangChainWrapper:
    """Synchronous wrapper for MCP LangChain integration."""
    
    def __init__(self, servers: Optional[Dict[str, Any]] = None, auto_start: bool = True):
        self.wrapper = MCPLangChainWrapper(servers, auto_start)
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def connect(self):
        """Synchronously connect to MCP servers."""
        self.loop.run_until_complete(self.wrapper.connect())
    
    def create_agent(self, *args, **kwargs):
        """Synchronously create agent."""
        return self.wrapper.create_agent(*args, **kwargs)
    
    def create_react_agent(self, *args, **kwargs):
        """Synchronously create ReAct agent."""
        return self.wrapper.create_react_agent(*args, **kwargs)
    
    def get_tools(self):
        """Get tools synchronously."""
        return self.wrapper.get_tools()
    
    def invoke_agent(self, agent: Runnable, user_input: str, chat_history=None):
        """Synchronously invoke agent."""
        if chat_history is None:
            chat_history = []
        return self.loop.run_until_complete(
            self.wrapper.invoke_agent(agent, user_input, chat_history)
        )
    
    def chat_with_agent(self, agent: Runnable, initial_message=None, system_prompt=None):
        """Synchronously chat with agent."""
        return self.loop.run_until_complete(
            self.wrapper.chat_with_agent(agent, initial_message, system_prompt)
        )
    
    def disconnect(self):
        """Synchronously disconnect."""
        self.loop.run_until_complete(self.wrapper.disconnect())
    
    def cleanup(self):
        """Clean up resources."""
        self.wrapper.cleanup()
        self.loop.close()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        self.cleanup()


if __name__ == "__main__":
    # Quick test with dummy servers
    print("Testing MCP LangChain Wrapper...")
    
    # Create a simple test server
    from mcp.server.fastmcp import FastMCP
    
    # Create test servers
    test_server1 = FastMCP("Test Server 1")
    
    @test_server1.tool()
    def greet(name: str) -> str:
        """Greet someone by name."""
        return f"Hello, {name}!"
    
    test_server2 = FastMCP("Test Server 2")
    
    @test_server2.tool()
    def echo(text: str) -> str:
        """Echo back the input text."""
        return f"Echo: {text}"
    
    # Create wrapper
    wrapper = SyncMCPLangChainWrapper(
        servers={
            "greeter": test_server1,
            "echo": test_server2
        },
        auto_start=True
    )
    
    try:
        with wrapper:
            tools = wrapper.get_tools()
            print(f"Loaded {len(tools)} tools")
            
            # Create a simple agent
            agent = wrapper.create_agent(
                "gpt-3.5-turbo",
                system_prompt="You have access to greeting and echo tools."
            )
            
            # Test the agent
            response = wrapper.invoke_agent(
                agent,
                "Say hello to John and echo 'test message'"
            )
            print(f"Agent response: {response}")
            
    except Exception as e:
        print(f"Error: {e}")