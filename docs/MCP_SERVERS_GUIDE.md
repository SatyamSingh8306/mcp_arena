# MCPForge MCP Servers: Comprehensive Developer Guide

## Table of Contents
1. [Overview](#overview)
2. [MCP Server Architecture](#mcp-server-architecture)
3. [BaseMCPServer](#basemcpserver)
4. [Available MCP Servers](#available-mcp-servers)
5. [Creating Custom MCP Servers](#creating-custom-mcp-servers)
6. [Running MCP Servers](#running-mcp-servers)
7. [Integration with Agents](#integration-with-agents)
8. [Best Practices](#best-practices)

---

## Overview

MCP (Model Context Protocol) Servers in MCPForge are service wrappers that expose capabilities to agents and tools. They provide:

- **Standardized Interface**: Built on FastMCP for consistent behavior
- **Multiple Transports**: Support for stdio, SSE, and HTTP
- **Tool Registration**: Automatic or manual tool registration
- **Service Integration**: Seamless connection to external services (GitHub, Docker, databases, etc.)

**Location**: `mcp_arena/presents/` and `mcp_arena/mcp/`

---

## MCP Server Architecture

### Core Components

```
BaseMCPServer (Abstract Base)
    ├── FastMCP (from mcp.server.fastmcp)
    ├── Tool Registration System
    ├── Configuration Management
    └── Transport Handling
```

### Key Flow

```
MCP Server Initialize
    ↓
Load Configuration (host, port, transport)
    ↓
Auto-register Tools (if enabled)
    ↓
Run Server
    ↓
Listen for Tool Calls
    ↓
Execute and Return Results
```

---

## BaseMCPServer

The abstract base class all MCP servers inherit from.

### Constructor Parameters

```python
class BaseMCPServer(ABC):
    def __init__(
        self,
        name: str,                                      # Server name
        description: str,                               # Server description/instructions
        host: str = "127.0.0.1",                       # Host to run on
        port: int = 8000,                              # Port to run on
        transport: Literal['stdio', 'sse', 
                          'streamable-http'] = "stdio", # Transport protocol
        debug: bool = False,                           # Enable debug mode
        log_level: Literal["DEBUG", "INFO", "WARNING", 
                          "ERROR", "CRITICAL"] = "INFO", # Logging level
        mount_path: str = "/",                         # HTTP mount path
        sse_path: str = "/sse",                        # SSE endpoint
        message_path: str = "/messages/",              # Message endpoint
        streamable_http_path: str = "/mcp",            # HTTP endpoint
        json_response: bool = False,                   # JSON response mode
        stateless_http: bool = False,                  # Stateless HTTP mode
        dependencies: Collection[str] = (),            # Additional dependencies
        auto_register_tools: bool = True               # Auto-register tools
    ):
```

### Key Methods

```python
class BaseMCPServer(ABC):
    
    @abstractmethod
    def _register_tools(self) -> None:
        """Register all tools with the MCP server.
        
        Override this in subclasses to define what tools are available.
        """
        pass
    
    def get_registered_tools(self) -> List[str]:
        """Get list of registered tool names.
        
        Returns:
            List of tool names registered with this server
        """
        pass
    
    def run(self, transport: Optional[str] = None) -> None:
        """Run the MCP server.
        
        Args:
            transport: Transport type (uses instance default if None)
        """
        pass
    
    def invoke(self, transport: Optional[str] = None) -> None:
        """Run the MCP server (alias for run)."""
        pass
```

### Transport Types

#### 1. **stdio (Standard I/O)**
Default transport using stdin/stdout for communication.

```python
server = MyMCPServer(transport="stdio")
server.run()  # Runs via stdin/stdout
```

**Use Cases**:
- Local agent integration
- Testing and development
- Single client connection

---

#### 2. **SSE (Server-Sent Events)**
HTTP-based transport using Server-Sent Events.

```python
server = MyMCPServer(
    host="0.0.0.0",
    port=8000,
    transport="sse",
    sse_path="/sse"
)
server.run()  # Listens on http://0.0.0.0:8000/sse
```

**Use Cases**:
- Web browser clients
- Real-time streaming
- Single-direction server notifications

---

#### 3. **Streamable-HTTP**
Full HTTP protocol with request/response bodies.

```python
server = MyMCPServer(
    host="0.0.0.0",
    port=8000,
    transport="streamable-http",
    streamable_http_path="/mcp"
)
server.run()  # Listens on http://0.0.0.0:8000/mcp
```

**Use Cases**:
- Complex client-server interaction
- Multiple concurrent clients
- Request/response with large payloads

---

---

## Available MCP Servers

MCPForge provides 17 pre-built MCP servers for common services.

### 1. **GithubMCPServer**

**Purpose**: Manage GitHub repositories, issues, pull requests, branches, commits, and files.

**Location**: `mcp_arena/presents/github.py`

**Dependencies**: PyGithub, GitHub Personal Access Token

**Capabilities**:
- Repository operations (list, get, create, update)
- Issue management (create, update, list, get)
- Pull request operations (create, update, list, merge)
- Branch management
- Commit operations
- File content operations

**Constructor**:
```python
from mcp_arena.presents.github import GithubMCPServer

github_server = GithubMCPServer(
    token="your_github_pat",           # GitHub Personal Access Token
    host="127.0.0.1",
    port=8001,
    transport="stdio",
    debug=False,
    auto_register_tools=True
)
```

**Environment Variable**:
```python
# Can also use environment variable GITHUB_TOKEN
import os
os.environ["GITHUB_TOKEN"] = "your_token"

github_server = GithubMCPServer()  # Automatically reads GITHUB_TOKEN
```

**Error Handling**:
```python
try:
    github_server = GithubMCPServer(token="invalid_token")
except ValueError as e:
    print(f"GitHub token error: {e}")
```

---

### 2. **LocalOperationsMCPServer**

**Purpose**: Perform local system operations - file management, system commands, process monitoring.

**Location**: `mcp_arena/presents/local_operation.py`

**Capabilities**:
- File operations (read, write, delete, list, move, copy)
- Directory operations
- System commands execution
- Process monitoring and management
- System information retrieval
- Network information
- Application launching
- Automation (clipboard, mouse, keyboard)

**Constructor**:
```python
from mcp_arena.presents.local_operation import LocalOperationsMCPServer

local_server = LocalOperationsMCPServer(
    host="127.0.0.1",
    port=8002,
    transport="stdio",
    debug=False,
    enable_system_commands=True,      # Enable OS commands
    enable_file_operations=True,      # Enable file operations
    enable_system_info=True,          # Enable system info
    safe_mode=True,                   # Enable safety checks
    auto_register_tools=True
)
```

**Safety Features**:
```python
# With safe_mode=True:
# - Prevents execution of dangerous commands (rm -rf, del /s, etc.)
# - Restricts file access to specified directories
# - Validates command input
# - Rate limits operations

local_server = LocalOperationsMCPServer(
    safe_mode=True                    # Recommended for security
)
```

**What It Can Do**:
```python
# File operations
- read_file(path)
- write_file(path, content)
- delete_file(path)
- list_directory(path)
- copy_file(source, destination)
- move_file(source, destination)

# System commands
- execute_command(command)
- execute_script(script_path)

# System monitoring
- get_system_info()
- get_process_info(pid)
- get_disk_usage()
- get_memory_usage()

# Network
- get_network_info()
- get_hostname()
- get_ip_address()

# Automation
- open_application(app_name)
- get_clipboard()
- set_clipboard(text)
- move_mouse(x, y)
- press_key(key)
```

---

### 3. **DockerMCPServer**

**Purpose**: Manage Docker containers, images, networks, and volumes.

**Location**: `mcp_arena/presents/docker.py`

**Dependencies**: docker-py (Docker Python client)

**Capabilities**:
- Container management (list, create, start, stop, remove, inspect)
- Image operations (list, pull, remove, inspect, build)
- Network management
- Volume management
- Container logs and statistics
- Exec into containers

**Constructor**:
```python
from mcp_arena.presents.docker import DockerMCPServer

docker_server = DockerMCPServer(
    base_url=None,                    # Docker daemon URL (auto-detect if None)
    version="auto",                   # API version
    timeout=60,                       # Timeout for API calls
    tls_config=None,                  # TLS configuration for remote
    use_ssh_client=False,             # Use SSH for remote
    max_pool_size=10,                 # Connection pool size
    host="127.0.0.1",
    port=8003,
    transport="stdio",
    auto_register_tools=True
)
```

**Remote Docker Connection**:
```python
# Local Unix socket (Linux/Mac)
docker_server = DockerMCPServer(
    base_url="unix:///var/run/docker.sock"
)

# Remote TCP connection
docker_server = DockerMCPServer(
    base_url="tcp://192.168.1.100:2375"
)

# Remote with TLS
docker_server = DockerMCPServer(
    base_url="tcp://remote-host:2376",
    tls_config={
        "client_cert": ("/path/to/cert.pem", "/path/to/key.pem"),
        "ca_cert": "/path/to/ca.pem",
        "verify": True
    }
)
```

**What It Can Do**:
```python
# Containers
- list_containers(all=False)
- create_container(image, name, ...)
- start_container(container_id)
- stop_container(container_id)
- remove_container(container_id)
- get_container_logs(container_id)
- get_container_stats(container_id)
- exec_container(container_id, command)

# Images
- list_images()
- pull_image(repository, tag)
- remove_image(image_id)
- build_image(dockerfile_path)

# Networks
- list_networks()
- create_network(name, driver)
- connect_container_to_network(container_id, network_id)
- disconnect_container_from_network(container_id, network_id)

# Volumes
- list_volumes()
- create_volume(name, driver)
- remove_volume(volume_id)
```

---

### 4. **PostgresMCPServer**

**Purpose**: Execute SQL queries on PostgreSQL databases.

**Location**: `mcp_arena/presents/postgres.py`

**Dependencies**: psycopg2 (PostgreSQL driver)

**Constructor**:
```python
from mcp_arena.presents.postgres import PostgresMCPServer

postgres_server = PostgresMCPServer(
    host="localhost",
    port=5432,
    database="mydb",
    user="postgres",
    password="password",
    mcp_host="127.0.0.1",
    mcp_port=8004,
    auto_register_tools=True
)
```

**What It Can Do**:
```python
# Query execution
- execute_query(sql)
- execute_select(sql)
- execute_insert(sql, values)
- execute_update(sql, values)
- execute_delete(sql, values)

# Database operations
- list_tables()
- get_table_schema(table_name)
- list_databases()
- create_table(table_name, schema)
```

---

### 5. **MongoDBMCPServer**

**Purpose**: Perform MongoDB operations (CRUD, aggregation).

**Location**: `mcp_arena/presents/mongo.py`

**Dependencies**: pymongo (MongoDB driver)

**Constructor**:
```python
from mcp_arena.presents.mongo import MongoDBMCPServer

mongo_server = MongoDBMCPServer(
    connection_string="mongodb://localhost:27017",
    database="mydb",
    host="127.0.0.1",
    port=8005,
    auto_register_tools=True
)
```

---

### 6. **RedisMCPServer**

**Purpose**: Perform Redis operations (get, set, list, delete, cache operations).

**Location**: `mcp_arena/presents/redis.py`

**Constructor**:
```python
from mcp_arena.presents.redis import RedisMCPServer

redis_server = RedisMCPServer(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    mcp_host="127.0.0.1",
    mcp_port=8006,
    auto_register_tools=True
)
```

---

### 7. **S3MCPServer** (AWS S3)

**Purpose**: Manage AWS S3 buckets and objects.

**Location**: `mcp_arena/presents/aws.py`

**Dependencies**: boto3 (AWS SDK)

**Constructor**:
```python
from mcp_arena.presents.aws import S3MCPServer

s3_server = S3MCPServer(
    access_key_id="your_key",
    secret_access_key="your_secret",
    region="us-east-1",
    host="127.0.0.1",
    port=8007,
    auto_register_tools=True
)
```

---

### 8. **SlackMCPServer**

**Purpose**: Send messages, get channel info, manage Slack workspace.

**Location**: `mcp_arena/presents/slack.py`

**Constructor**:
```python
from mcp_arena.presents.slack import SlackMCPServer

slack_server = SlackMCPServer(
    bot_token="xoxb-your-token",
    host="127.0.0.1",
    port=8008,
    auto_register_tools=True
)
```

---

### 9. **JiraMCPServer**

**Purpose**: Create issues, update tickets, manage Jira projects.

**Location**: `mcp_arena/presents/jira.py`

**Constructor**:
```python
from mcp_arena.presents.jira import JiraMCPServer

jira_server = JiraMCPServer(
    url="https://your-jira.atlassian.net",
    username="your-email@company.com",
    api_token="your-api-token",
    host="127.0.0.1",
    port=8009,
    auto_register_tools=True
)
```

---

### 10. **VectorDBMCPServer**

**Purpose**: Vector database operations for embeddings and semantic search.

**Location**: `mcp_arena/presents/vectordb.py`

**Constructor**:
```python
from mcp_arena.presents.vectordb import VectorDBMCPServer

vectordb_server = VectorDBMCPServer(
    db_url="localhost:6333",          # Qdrant or similar
    collection_name="my_collection",
    host="127.0.0.1",
    port=8010,
    auto_register_tools=True
)
```

---

### 11. **NotionMCPServer**

**Purpose**: Access and manage Notion databases and pages.

**Location**: `mcp_arena/presents/notion.py`

**Constructor**:
```python
from mcp_arena.presents.notion import NotionMCPServer

notion_server = NotionMCPServer(
    token="notion_integration_token",
    host="127.0.0.1",
    port=8011,
    auto_register_tools=True
)
```

---

### 12. **GitLabMCPServer**

**Purpose**: Manage GitLab repositories, issues, merge requests.

**Location**: `mcp_arena/presents/gitlab.py`

**Constructor**:
```python
from mcp_arena.presents.gitlab import GitLabMCPServer

gitlab_server = GitLabMCPServer(
    url="https://gitlab.com",
    token="your_gitlab_token",
    host="127.0.0.1",
    port=8012,
    auto_register_tools=True
)
```

---

### 13. **BitbucketMCPServer**

**Purpose**: Manage Bitbucket repositories and pull requests.

**Location**: `mcp_arena/presents/bitbucket.py`

**Constructor**:
```python
from mcp_arena.presents.bitbucket import BitbucketMCPServer

bitbucket_server = BitbucketMCPServer(
    username="your_username",
    app_password="your_app_password",
    host="127.0.0.1",
    port=8013,
    auto_register_tools=True
)
```

---

### 14. **ConfluenceMCPServer**

**Purpose**: Create and manage Confluence pages and spaces.

**Location**: `mcp_arena/presents/confluence.py`

**Constructor**:
```python
from mcp_arena.presents.confluence import ConfluenceMCPServer

confluence_server = ConfluenceMCPServer(
    url="https://your-confluence.atlassian.net",
    username="your-email@company.com",
    api_token="your-api-token",
    host="127.0.0.1",
    port=8014,
    auto_register_tools=True
)
```

---

### 15. **GmailMCPServer**

**Purpose**: Manage Gmail emails, send messages, handle attachments.

**Location**: `mcp_arena/presents/mail.py`

**Dependencies**: google-auth, google-api-python-client

**Constructor**:
```python
from mcp_arena.presents.mail import GmailMCPServer

gmail_server = GmailMCPServer(
    credentials_path="path/to/credentials.json",
    token_path="path/to/token.json",
    host="127.0.0.1",
    port=8015,
    auto_register_tools=True
)
```

---

### 16. **OutlookMCPServer**

**Purpose**: Manage Outlook emails, calendar events, and Microsoft 365 services.

**Location**: `mcp_arena/presents/outlook.py`

**Dependencies**: msal (Microsoft Authentication Library)

**Constructor**:
```python
from mcp_arena.presents.outlook import OutlookMCPServer

outlook_server = OutlookMCPServer(
    client_id="your_client_id",
    client_secret="your_client_secret",
    tenant_id="your_tenant_id",
    host="127.0.0.1",
    port=8016,
    auto_register_tools=True
)
```

---

### 17. **WhatsAppMCPServer**

**Purpose**: Send WhatsApp messages, manage conversations via Twilio API.

**Location**: `mcp_arena/presents/whatsapp.py`

**Dependencies**: twilio

**Constructor**:
```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer

whatsapp_server = WhatsAppMCPServer(
    account_sid="your_account_sid",
    auth_token="your_auth_token",
    from_number="whatsapp:+1234567890",
    host="127.0.0.1",
    port=8017,
    auto_register_tools=True
)
```

---

## Creating Custom MCP Servers

### Step 1: Extend BaseMCPServer

```python
from mcp_arena.mcp.server import BaseMCPServer
from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional

class CustomMCPServer(BaseMCPServer):
    def __init__(
        self,
        api_key: str,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        **kwargs
    ):
        # Store any service-specific configuration
        self.api_key = api_key
        
        # Call parent initializer
        super().__init__(
            name="Custom Service MCP Server",
            description="MCP server for my custom service",
            host=host,
            port=port,
            transport=transport,
            **kwargs
        )
    
    def _register_tools(self) -> None:
        """Register tools - this is called automatically"""
        # Define your tools here
        self._register_data_tools()
        self._register_processing_tools()
    
    def _register_data_tools(self) -> None:
        """Register data-related tools"""
        
        @self.mcp_server.tool()
        def fetch_data(
            resource_id: Annotated[str, "Resource ID to fetch"],
            format: Annotated[str, "Response format"] = "json"
        ) -> dict:
            """Fetch data from the custom service"""
            try:
                # Your implementation
                result = {"status": "success", "data": {...}}
                self._registered_tools.append("fetch_data")
                return result
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def store_data(
            resource_id: Annotated[str, "Resource ID"],
            data: Annotated[dict, "Data to store"]
        ) -> dict:
            """Store data in the custom service"""
            try:
                # Your implementation
                result = {"status": "stored", "id": resource_id}
                self._registered_tools.append("store_data")
                return result
            except Exception as e:
                return {"error": str(e)}
    
    def _register_processing_tools(self) -> None:
        """Register processing tools"""
        
        @self.mcp_server.tool()
        def process(
            input_data: Annotated[str, "Data to process"],
            algorithm: Annotated[str, "Processing algorithm to use"]
        ) -> str:
            """Process data using specified algorithm"""
            try:
                # Your implementation
                result = f"Processed with {algorithm}"
                self._registered_tools.append("process")
                return result
            except Exception as e:
                return f"Error: {str(e)}"
```

### Step 2: Use Your Custom Server

```python
# Create instance
custom_server = CustomMCPServer(api_key="your_key")

# Get registered tools
tools = custom_server.get_registered_tools()
print(f"Available tools: {tools}")

# Run the server
custom_server.run()  # Uses default transport (stdio)

# Or run with different transport
custom_server.run(transport="sse")
```

### Step 3: Integrate with Agent

```python
from mcp_arena.tools.base import BaseMCPTool
from mcp_arena.agent import create_react_agent

# Create custom tool wrapper
class CustomMCPTools(BaseMCPTool):
    def __init__(self, server: CustomMCPServer):
        super().__init__(server)

# Create agent with custom server
custom_server = CustomMCPServer(api_key="your_key")
custom_tools = CustomMCPTools(custom_server)

agent = create_react_agent()

# Get tools from server and add to agent
for tool in custom_tools.get_list_of_tools():
    # Add tool to agent (implementation depends on agent)
    pass

response = agent.process("Your task using custom server")
```

---

## Running MCP Servers

### Option 1: Direct Execution

```python
from mcp_arena.presents.github import GithubMCPServer

github_server = GithubMCPServer(token="your_token")
github_server.run()  # Blocks until server stops
```

### Option 2: With Different Transport

```python
github_server = GithubMCPServer(
    token="your_token",
    host="0.0.0.0",
    port=8001,
    transport="sse"
)

github_server.run()  # Listens on http://0.0.0.0:8001/sse
```

### Option 3: Programmatic with Control

```python
from mcp_arena.presents.docker import DockerMCPServer
import subprocess
import time

docker_server = DockerMCPServer()

# Run in separate process
process = subprocess.Popen(
    ["python", "-c", """
from mcp_arena.presents.docker import DockerMCPServer
server = DockerMCPServer(transport='sse')
server.run()
"""],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(2)  # Wait for server to start

# Do something with server...

process.terminate()  # Stop server
```

### Option 4: Using MCP Registry

```python
from mcp_arena.mcp.registry import RegistryMCP

registry = RegistryMCP()

# List all available MCP servers
registry.list_avail_mcp()

# Get specific server class and instantiate
# GithubMCPServer, LocalOperationsMCPServer, DockerMCPServer, etc.
```

---

## Integration with Agents

### Using MCP Server with Agents

```python
from mcp_arena.agent.react_agent import ReactAgent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.tools.github import GithubMCPTools

# Step 1: Create MCP server
github_server = GithubMCPServer(token="your_token")

# Step 2: Create MCP tools wrapper
github_tools = GithubMCPTools(github_server)

# Step 3: Create agent
agent = ReactAgent(llm=None, memory_type="conversation")

# Step 4: Get tools from MCP server
available_tools = github_tools.get_list_of_tools()

# Step 5: Add to agent (depends on agent implementation)
# This is pseudo-code - actual implementation varies
for tool in available_tools:
    agent.add_tool(tool)

# Step 6: Use agent with MCP capabilities
response = agent.process("List all my GitHub repositories and their stars")
```

### Multi-Server Integration

```python
from mcp_arena.agent.react_agent import ReactAgent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.docker import DockerMCPServer
from mcp_arena.presents.postgres import PostgresMCPServer

# Create multiple servers
github = GithubMCPServer(token="...")
docker = DockerMCPServer()
postgres = PostgresMCPServer(host="...", user="...", password="...")

# Create agent with multi-service capability
agent = ReactAgent(llm=None, memory_type="episodic")

# Add capabilities from multiple services
github_tools = GithubMCPTools(github)
docker_tools = DockerMCPTools(docker)
postgres_tools = PostgresMCPTools(postgres)

# Agent can now coordinate across services
response = agent.process(
    "Deploy the latest code from GitHub to Docker, "
    "then update the deployment database in PostgreSQL"
)
```

---

## Best Practices

### 1. **Server Configuration**

```python
# Good: Explicit configuration
github_server = GithubMCPServer(
    token="your_token",
    host="127.0.0.1",
    port=8001,
    transport="stdio",
    debug=False,
    log_level="INFO",
    auto_register_tools=True
)

# Bad: Minimal config with defaults might miss important settings
github_server = GithubMCPServer()  # May use wrong token or settings
```

### 2. **Error Handling**

```python
from mcp_arena.presents.github import GithubMCPServer

try:
    github_server = GithubMCPServer(token="invalid_token")
    tools = github_server.get_registered_tools()
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"Server initialization error: {e}")
```

### 3. **Security - Credentials Management**

```python
import os
from mcp_arena.presents.github import GithubMCPServer

# Bad: Hardcoded credentials
github_server = GithubMCPServer(token="ghp_1234567890abcdef")

# Good: Use environment variables
github_server = GithubMCPServer(token=os.getenv("GITHUB_TOKEN"))

# Good: Use secrets manager
import json
with open("/run/secrets/github_token") as f:
    token = json.load(f)["token"]
github_server = GithubMCPServer(token=token)
```

### 4. **Transport Selection**

```python
# For local agent integration with subprocess
server = DockerMCPServer(transport="stdio")
server.run()

# For web-based clients
server = DockerMCPServer(
    host="0.0.0.0",
    port=8003,
    transport="sse"
)
server.run()

# For complex interactions
server = DockerMCPServer(
    host="0.0.0.0",
    port=8003,
    transport="streamable-http"
)
server.run()
```

### 5. **Tool Registration**

```python
# Automatic (default and recommended)
server = GithubMCPServer(
    token="your_token",
    auto_register_tools=True  # Tools registered on init
)

# Manual control
server = GithubMCPServer(
    token="your_token",
    auto_register_tools=False
)

# Then register selectively
server._register_tools()  # Call manually when ready
```

### 6. **Logging and Debugging**

```python
# For development/debugging
server = LocalOperationsMCPServer(
    debug=True,
    log_level="DEBUG"
)

# For production
server = LocalOperationsMCPServer(
    debug=False,
    log_level="INFO"
)
```

### 7. **Port and Host Configuration**

```python
# For local development (only localhost)
server = DockerMCPServer(
    host="127.0.0.1",
    port=8003
)

# For network access (all interfaces)
server = DockerMCPServer(
    host="0.0.0.0",  # Listen on all interfaces
    port=8003
)

# For specific interface
server = DockerMCPServer(
    host="192.168.1.100",  # Specific IP
    port=8003
)
```

### 8. **Resource Limits and Safety**

```python
# LocalOperationsMCPServer with safety
server = LocalOperationsMCPServer(
    safe_mode=True,                    # Enable safety checks
    enable_system_commands=True,       # Allow OS commands
    enable_file_operations=True,       # Allow file ops
    enable_system_info=True            # Allow system info
)

# Docker with resource limits (when creating containers)
# Implement in custom server initialization

# Database with connection pooling
postgres_server = PostgresMCPServer(
    host="localhost",
    pool_size=10,
    max_overflow=20
)
```

### 9. **Testing MCP Servers**

```python
from mcp_arena.presents.github import GithubMCPServer

# Test server initialization
try:
    server = GithubMCPServer(token="test_token")
    print("✓ Server initialized successfully")
except Exception as e:
    print(f"✗ Server initialization failed: {e}")

# Test tool registration
tools = server.get_registered_tools()
assert len(tools) > 0, "No tools registered"
print(f"✓ Registered {len(tools)} tools")

# Test tool names
expected_tools = ["list_repositories", "get_repository", "create_issue"]
for tool_name in expected_tools:
    assert tool_name in tools, f"Missing tool: {tool_name}"
print("✓ All expected tools registered")
```

### 10. **Monitoring and Health Checks**

```python
def check_server_health(server):
    """Check if MCP server is responsive"""
    try:
        tools = server.get_registered_tools()
        return {
            "status": "healthy",
            "tool_count": len(tools),
            "tools": tools
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

# Check health
health = check_server_health(github_server)
print(f"Server health: {health['status']}")
```

---

## Summary

MCPForge MCP Servers provide:

- **17 Pre-built Servers**: GitHub, Docker, PostgreSQL, MongoDB, Redis, S3, Slack, Jira, Notion, GitLab, Bitbucket, Confluence, LocalOperations, VectorDB, Gmail, Outlook, WhatsApp
- **Flexible Configuration**: Multiple transports, customizable host/port, debug modes
- **Easy Integration**: Simple tool registration and agent integration
- **Extensibility**: Simple base class for creating custom servers
- **Security**: Credential management and safe mode options

Choose the right server for your service needs, configure appropriately for your environment, and integrate seamlessly with agents for powerful multi-service automation.
