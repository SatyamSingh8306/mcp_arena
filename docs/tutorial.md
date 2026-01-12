# Building "Jarvis" with mcp_arena and LangChain

This tutorial shows how to build a personal "Jarvis" assistant that can operate your local machine (files, terminal, apps) using `mcp_arena` and `langchain`.

## Prerequisites

```bash
pip install mcp_arena[local_operation,github] langchain-mcp-adapters langchain-groq gradio
```

## Step 1: Start the Local MCP Server

First, we need a server that handles the actual operations (file manipulation, opening apps, etc.).

Create a file named `server.py`:

```python
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

# Create the server
server = LocalOperationsMCPServer(
    host="localhost",
    port=8000,
    debug=True,
    # Enable specific capabilities
    enable_system_commands=True,
    enable_file_operations=True,
    enable_system_info=True
)

# Run with SSE (Server-Sent Events) for HTTP compatibility
# This allows remote clients (like our LangChain agent) to connect over HTTP
print("Starting Local Operations Server on http://localhost:8000/sse")
server.run(transport="sse")
```

Run this server in a separate terminal:
```bash
python server.py
```

## Step 2: Create the Agent (Client)

Now we'll create the agent that connects to this server. We'll use `langchain-groq` for the LLM (fast inference) and `MultiServerMCPClient` to manage tools.

Create `agent.py`:

```python
import os
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain.agents import create_agent, AgentExecutor
from langgraph.prebuilt import create_react_agent

# 1. Initialize the MCP Client
# We connect to our running Local server (HTTP) and optionally others
client = MultiServerMCPClient(
    {
        "local": {
            "transport": "sse",  # Using SSE as configured in server.py
            "url": "http://localhost:8000/sse",
        },
        # You could add more servers here
        # "github": {
        #     "transport": "stdio",
        #     "command": "python",
        #     "args": ["-m", "mcp_arena", "run", "--mcp-server", "github"],
        # }
    }
)

async def create_jarvis():
    # 2. Load Tools
    # This connects to the server and fetches available tools
    await client.connect()
    tools = await client.get_tools()
    
    # 3. Initialize LLM (Groq)
    # Ensure GROQ_API_KEY is set in environment
    llm = ChatGroq(
        model="llama3-70b-8192", # Or "mixtral-8x7b-32768"
        temperature=0
    )
    
    # 4. Create Agent
    # We use LangGraph's prebuilt React agent for reliability
    agent = create_react_agent(llm, tools)
    
    return agent

# Example Usage
async def main():
    agent = await create_jarvis()
    
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "What is the OS version of this machine?"}]}
    )
    
    # Print just the final response content
    print(response["messages"][-1].content)

if __name__ == "__main__":
    asyncio.run(main())
```

## Step 3: Build the User Interface

Let's wrap this in a nice Gradio UI to make it feel like real Jarvis.

Create `app.py`:

```python
import gradio as gr
import asyncio
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage

# --- Agent Setup (Global) ---

# Initialize Client
client = MultiServerMCPClient({
    "local": {
        "transport": "sse",
        "url": "http://localhost:8000/sse",
    }
})

# Global agent variable
agent = None

async def init_agent():
    global agent
    await client.connect()
    tools = await client.get_tools()
    llm = ChatGroq(model="llama3-70b-8192", temperature=0)
    agent = create_react_agent(llm, tools)
    return agent

# Initialize loop for async operations
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
loop.run_until_complete(init_agent())

# --- Chat Function ---

async def interact_with_jarvis(message, history):
    if not agent:
        return "Agent not initialized. Please restart."
    
    # Convert history to format if needed, but create_react_agent handles memory internally 
    # if we pass the full state. 
    # For a simple chat interface, we just pass the new message
    # LangGraph agent is stateless by default unless we use checkpointers, 
    # but here we just want a response to the current query.
    
    # We'll pass the conversation history to give context
    messages = []
    for user_msg, assistant_msg in history:
        messages.append(HumanMessage(content=user_msg))
        messages.append({"role": "assistant", "content": assistant_msg})
    
    messages.append(HumanMessage(content=message))
    
    result = await agent.ainvoke({"messages": messages})
    
    # The last message is the assistant's response
    return result["messages"][-1].content

# Wrapper to run async function in Gradio
def predict(message, history):
    return loop.run_until_complete(interact_with_jarvis(message, history))

# --- UI Setup ---

with gr.Blocks(theme=gr.themes.Soft(), title="Jarvis Control Center") as demo:
    gr.Markdown("# 🤖 Jarvis Control Center")
    gr.Markdown("Connected to: **Local Operation Server**")
    
    chat = gr.ChatInterface(
        predict,
        chatbot=gr.Chatbot(height=500),
        textbox=gr.Textbox(placeholder="Ask me to open apps, check files, or run commands...", container=False, scale=7),
        title=None,
        description="Your AI System Executiant",
        examples=[
            "What files are in the current directory?",
            "Open the calculator",
            "What is my IP address?",
            "Create a new folder called 'ProjectX'\n"
        ],
    )

if __name__ == "__main__":
    demo.launch()
```

## Running Instructions

1. **Terminal 1 (Server):**
   ```bash
   python server.py
   ```

2. **Terminal 2 (App):**
   ```bash
   # Ensure keys are set
   $env:GROQ_API_KEY="gsk_..."
   
   python app.py
   ```

Open your browser to the URL shown (usually `http://127.0.0.1:7860`). Jarvis is now online!
