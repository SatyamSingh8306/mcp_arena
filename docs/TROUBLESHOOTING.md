# Troubleshooting Guide

A comprehensive guide for resolving common issues when using **mcp_arena**.

---

## Table of Contents

- [Installation Issues](#installation-issues)
- [Server Issues](#server-issues)
- [Agent Issues](#agent-issues)
- [Integration Issues](#integration-issues)
- [CLI Issues](#cli-issues)
- [Platform-Specific Issues](#platform-specific-issues)
  - [GitHub](#github)
  - [Slack](#slack)
  - [Gmail](#gmail)
  - [Outlook](#outlook)
  - [Notion](#notion)
  - [PostgreSQL](#postgresql)
  - [MongoDB](#mongodb)
  - [Redis](#redis)
  - [Docker](#docker)
  - [GitLab](#gitlab)
  - [Jira](#jira)
  - [Confluence](#confluence)
  - [Bitbucket](#bitbucket)
  - [WhatsApp](#whatsapp)
  - [VectorDB](#vectordb)
  - [AWS S3](#aws-s3)

---

## Installation Issues

### Issue: `ModuleNotFoundError` when importing mcp_arena

**Symptom:**

```
ModuleNotFoundError: No module named 'mcp_arena'
```

**Solution:**

1. Ensure you installed the package:
   ```bash
   pip install mcp-arena
   ```
2. If you cloned the repo for development, install in editable mode:
   ```bash
   pip install -e .
   ```
3. Verify you are using the correct Python environment:
   ```bash
   python -c "import mcp_arena; print(mcp_arena.__version__)"
   ```

---

### Issue: Dependency conflicts during installation

**Symptom:**

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**Solution:**

1. Create a fresh virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate   # Linux/macOS
   venv\Scripts\activate      # Windows
   ```
2. Install only the presets you need instead of everything:
   ```bash
   # Only GitHub + Slack
   pip install mcp-arena[github,slack]
   
   # Only agents
   pip install mcp-arena[agents]
   
   # Everything
   pip install mcp-arena[all]
   ```

Available optional groups: `github`, `gitlab`, `bitbucket`, `slack`, `gmail`, `outlook`, `whatsapp`, `postgres`, `mongodb`, `redis`, `docker`, `vectordb`, `agents`, `local_operation`, `dev`, `all`.

---

### Issue: `psycopg2` build failure

**Symptom:**

```
Error: pg_config executable not found.
```

**Solution:**

- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt-get install libpq-dev python3-dev
  ```
- **macOS:**
  ```bash
  brew install postgresql
  ```
- **Windows:** The `psycopg2-binary` wheel should install without build tools. If not:
  ```bash
  pip install psycopg2-binary
  ```

---

### Issue: `sentence-transformers` / PyTorch installation is slow or fails

**Symptom:** Installation hangs or takes a very long time downloading PyTorch.

**Solution:**

`sentence-transformers` requires PyTorch, which is a large download (~2 GB). If you don't need local embeddings:

```bash
# Install without vectordb extras
pip install mcp-arena
```

If you do need it, install PyTorch first for your platform from [pytorch.org](https://pytorch.org/get-started/locally/), then:

```bash
pip install mcp-arena[vectordb]
```

---

### Issue: Python version mismatch

**Symptom:**

```
ERROR: mcp-arena requires Python >=3.12
```

**Solution:**

mcp_arena requires **Python 3.12 or higher**. Check your version:

```bash
python --version
```

Upgrade Python from [python.org](https://www.python.org/downloads/) or use `pyenv`:

```bash
pyenv install 3.12
pyenv local 3.12
```

---

## Server Issues

### Issue: Server fails to start

**Symptom:**

```
RuntimeError: Server failed to start
```

**Possible Causes & Solutions:**

1. **Missing credentials:** Each preset server requires specific tokens or connection strings. Check the [Platform-Specific Issues](#platform-specific-issues) section for your server.

2. **Port already in use:**
   ```
   OSError: [Errno 98] Address already in use
   ```
   Change the port:
   ```python
   server = GithubMCPServer(token="...", port=8001)
   ```
   Or find and kill the process using the port:
   ```bash
   # Linux/macOS
   lsof -i :8000
   kill -9 <PID>
   
   # Windows
   netstat -ano | findstr :8000
   taskkill /PID <PID> /F
   ```

3. **Transport mismatch:** Ensure the client connects using the same transport:
   ```python
   # Server
   server.run(transport="stdio")       # Default
   server.run(transport="sse")         # SSE at http://host:port/sse
   server.run(transport="streamable-http")  # HTTP at http://host:port/mcp
   ```

---

### Issue: Authentication failures

**Symptom:**

```
ValueError: GitHub token is required. Provide it as argument or set GITHUB_TOKEN environment variable.
```

**Solution:**

All preset servers follow the same pattern — provide credentials either as constructor arguments or via environment variables:

```python
# Option 1: Direct argument
server = GithubMCPServer(token="ghp_your_token_here")

# Option 2: Environment variable
import os
os.environ["GITHUB_TOKEN"] = "ghp_your_token_here"
server = GithubMCPServer()

# Option 3: .env file (auto-loaded by mcp_arena)
# Create a .env file in your project root:
# GITHUB_TOKEN=ghp_your_token_here
```

| Server | Constructor Param | Env Variable |
|---|---|---|
| GitHub | `token` | `GITHUB_TOKEN` |
| Slack | `token` | `SLACK_TOKEN` |
| Notion | `token` | `NOTION_TOKEN` |
| PostgreSQL | `connection_string` | `POSTGRES_CONNECTION_STRING` |
| MongoDB | `connection_string` | `MONGODB_CONNECTION_STRING` |
| GitLab | `private_token` | `GITLAB_PRIVATE_TOKEN` |
| Bitbucket | `username`, `app_password` | `BITBUCKET_USERNAME`, `BITBUCKET_APP_PASSWORD` |
| WhatsApp | `account_sid`, `auth_token` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` |

---

### Issue: Tool registration errors

**Symptom:** Tools are not available or throw errors when called.

**Solution:**

1. Ensure `auto_register_tools=True` (the default):
   ```python
   server = GithubMCPServer(token="...", auto_register_tools=True)
   ```

2. If registering custom tools, make sure the function signature is correct:
   ```python
   @server.tool()
   def my_tool(param1: str, param2: int) -> str:
       """Tool description — this docstring is required."""
       return "result"
   ```

3. Check that tools are registered before running:
   ```python
   tools = server.get_list_of_tools()
   print(f"Registered tools: {len(tools)}")
   ```

---

### Issue: `BrokenPipeError` or stream closed warnings

**Symptom:**

```
BrokenPipeError: [Errno 32] Broken pipe
ValueError: Stream closed
```

**Cause:** This typically occurs when a stdio transport client disconnects. It's expected behavior when the client terminates the connection.

**Solution:** These can usually be ignored. The CLI handles them gracefully. If you need to suppress them in your own code:

```python
import signal
signal.signal(signal.SIGPIPE, signal.SIG_DFL)
```

---

## Agent Issues

### Issue: Agent not responding / returns empty

**Symptom:** `agent.process()` returns `None` or `"LLM not configured"`.

**Solution:**

Agents require an LLM to be configured. Set up a Groq, OpenAI, or other LangChain-compatible LLM:

```python
from langchain_groq import ChatGroq
from mcp_arena.agent import create_react_agent

# Set up LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", api_key="your_groq_key")

# Pass LLM to agent
agent = create_react_agent(llm=llm, memory_type="conversation")
response = agent.process("Hello!")
```

Ensure your API key is valid and the model is available.

---

### Issue: Memory errors

**Symptom:**

```
ValueError: Unknown memory type: <type>
```

**Solution:**

Use one of the supported memory types:

| Memory Type | Class | Description |
|---|---|---|
| `"simple"` | `SimpleMemory` | Basic key-value store |
| `"conversation"` | `ConversationMemory` | Conversation history (default, max 100 turns) |
| `"episodic"` | `EpisodicMemory` | Keyword-indexed episode storage |

```python
agent = create_reflection_agent(memory_type="conversation")
```

---

### Issue: Unknown agent type error

**Symptom:**

```
ValueError: Unknown agent type: <type>
```

**Solution:**

Use one of the built-in agent types:

| Type | Class | Use Case |
|---|---|---|
| `"reflection"` | `ReflectionAgent` | Iterative self-improvement |
| `"react"` | `ReactAgent` | Tool-using reasoning + acting |
| `"planning"` | `PlanningAgent` | Multi-step goal decomposition |

```python
from mcp_arena.agent import create_agent

agent = create_agent("react", config={"max_steps": 10})
```

Or register your own agent type:

```python
from mcp_arena.agent.factory import AgentFactory

factory = AgentFactory()
factory.register_agent_type("custom", MyCustomAgent)
```

---

### Issue: Routing failures (multi-agent)

**Symptom:** `SmartRouter` always falls back to `"reflection"` agent.

**Cause:** The LLM-based router failed to classify the query, so it defaults to `"reflection"`.

**Solution:**

1. Ensure the router's LLM is configured and responsive.
2. Use `ConditionalRouter` for deterministic routing:
   ```python
   from mcp_arena.agent.router import ConditionalRouter
   
   router = ConditionalRouter()
   router.add_route(
       condition=lambda query: "calculate" in query.lower(),
       agent_type="react",
       priority=1
   )
   ```
3. Check router logs for classification errors.

---

### Issue: Agent max steps exceeded

**Symptom:** ReactAgent or PlanningAgent stops without completing the task.

**Solution:**

Increase the maximum steps:

```python
agent = create_react_agent(memory_type="conversation", max_steps=20)
```

Or via the builder:

```python
from mcp_arena.agent.factory import AgentBuilder

agent = (AgentBuilder("react")
         .with_config(max_steps=25)
         .build())
```

---

## Integration Issues

### Issue: LangChain integration errors

**Symptom:**

```
ImportError: langchain_mcp_adapters is required
```

**Solution:**

Install the MCP adapters package:

```bash
pip install langchain-mcp-adapters
```

If the import shows a warning but doesn't crash:

```
Warning: langchain_mcp_adapters not installed.
```

The wrapper modules (`MCPLangChainWrapper`) will be set to `None`. Install the package to enable them.

---

### Issue: FastMCP compatibility errors

**Symptom:**

```
ModuleNotFoundError: No module named 'mcp.server.fastmcp'
```

**Solution:**

Ensure you have the correct version of the `mcp` package:

```bash
pip install "mcp>=1.25,<2.0"
```

If you have a conflicting `mcp` package installed (e.g., from another project), remove it first:

```bash
pip uninstall mcp
pip install "mcp>=1.25,<2.0"
```

---

### Issue: MCPLangChainIntegration server connection timeout

**Symptom:** `add_github_server()` or similar hangs or raises timeout errors.

**Solution:**

1. Verify the server starts independently first:
   ```python
   from mcp_arena.presents.github import GithubMCPServer
   server = GithubMCPServer(token="...")
   server.run()  # Test standalone
   ```

2. When using `MCPLangChainIntegration`, the wrapper spawns subprocess scripts for stdio transport. Ensure Python is accessible on your `PATH`.

3. Try using SSE transport instead of stdio for debugging:
   ```python
   integration = MCPLangChainIntegration(llm=llm, default_transport="sse")
   ```

---

## CLI Issues

### Issue: `mcp-arena` command not found

**Symptom:**

```
mcp-arena: command not found
```

**Solution:**

1. Ensure mcp_arena is installed:
   ```bash
   pip install mcp-arena
   ```
2. If installed but not on PATH, run via Python module:
   ```bash
   python -m mcp_arena.cli list
   ```
3. Check that your pip scripts directory is on your PATH:
   ```bash
   python -m site --user-base
   # Add the `bin/` (Linux/macOS) or `Scripts/` (Windows) subdirectory to PATH
   ```

---

### Issue: Server preset not found

**Symptom:**

```
Server preset 'xyz' not found.
```

**Solution:**

List available presets:

```bash
mcp-arena list
```

Available presets: `github`, `slack`, `notion`, `postgres`, `mongo`, `redis`, `aws`, `docker`, `gitlab`, `bitbucket`, `confluence`, `jira`, `mail`, `outlook`, `whatsapp`, `smtp`, `generic_api`, `vectordb`, `local_operation`.

---

### Issue: CLI run command fails with parameter errors

**Symptom:**

```
TypeError: __init__() missing required arguments
```

**Solution:**

Pass required parameters using `--extra-args`:

```bash
mcp-arena run --mcp-server github --extra-args token=ghp_your_token

# Multiple parameters
mcp-arena run --mcp-server postgres --extra-args connection_string=postgresql://user:pass@localhost/db
```

Use `mcp-arena info <preset>` to see required parameters for a specific server.

---

## Platform-Specific Issues

### GitHub

**Import:**
```python
from mcp_arena.presents.github import GithubMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing token | `ValueError: GitHub token is required...` | Set `GITHUB_TOKEN` env var or pass `token=` |
| Rate limiting | `403 API rate limit exceeded` | Use a token with higher limits or wait |
| Repo not found | `GithubException: 404 Not Found` | Verify repo name format: `owner/repo` |
| Insufficient permissions | `GithubException: 403 Forbidden` | Ensure token has required scopes (`repo`, `admin:org`, etc.) |

**Required Token Scopes:** `repo`, `read:org`, `read:user` (minimum)

---

### Slack

**Import:**
```python
from mcp_arena.presents.slack import SlackMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing token | `ValueError: Slack token is required...` | Set `SLACK_TOKEN` env var or pass `token=` |
| Invalid token | `SlackApiError: invalid_auth` | Regenerate bot token in Slack app settings |
| Missing scopes | `SlackApiError: missing_scope` | Add required OAuth scopes: `channels:read`, `chat:write`, `users:read` |
| Channel not found | `SlackApiError: channel_not_found` | Use channel ID (e.g., `C01234ABCDE`), not name |

---

### Gmail

**Import:**
```python
from mcp_arena.presents.mail import GmailMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| No credentials file | `ValueError: credentials_path is required...` | Download OAuth client JSON from Google Cloud Console |
| OAuth flow fails | Browser doesn't open for auth | Set `GMAIL_CREDENTIALS_PATH` env var; ensure `token.json` is writable |
| Token expired | `google.auth.exceptions.RefreshError` | Delete `token.json` and re-authenticate |
| Insufficient scopes | `HttpError 403: insufficient permission` | Required scopes: `gmail.readonly`, `gmail.send`, `gmail.modify` |

**Setup Steps:**
1. Create a project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the Gmail API
3. Create OAuth 2.0 credentials (Desktop app)
4. Download the JSON file
5. Pass the path to `GmailMCPServer(credentials_path="path/to/credentials.json")`

---

### Outlook

**Import:**
```python
from mcp_arena.presents.outlook import OutlookMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Auth failure | `ValueError: Failed to get access token: ...` | Verify `client_id` and `client_secret` in Azure AD |
| Tenant mismatch | `AADSTS50020` error | Set correct `tenant_id` (default is `"common"`) |
| Missing permissions | `403 Insufficient privileges` | Add `Mail.Read`, `Mail.Send` permissions in Azure AD |

**Setup Steps:**
1. Register an app in [Azure AD](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps)
2. Add `Mail.Read` and `Mail.Send` API permissions
3. Create a client secret
4. Pass `client_id` and `client_secret` to `OutlookMCPServer`

---

### Notion

**Import:**
```python
from mcp_arena.presents.notion import NotionMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing token | `ValueError: Notion token is required...` | Set `NOTION_TOKEN` env var |
| Page not found | `APIResponseError: Could not find...` | Share the page/database with your integration |
| Wrong token type | `APIResponseError: Unauthorized` | Use an internal integration token, not OAuth |

**Setup Steps:**
1. Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations)
2. Copy the Internal Integration Secret
3. Share your Notion pages/databases with the integration

---

### PostgreSQL

**Import:**
```python
from mcp_arena.presents.postgres import PostgresMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing connection string | `ValueError: PostgreSQL connection string is required...` | Set `POSTGRES_CONNECTION_STRING` env var |
| Connection refused | `psycopg2.OperationalError: could not connect` | Verify PostgreSQL is running and accepting connections |
| Auth failure | `psycopg2.OperationalError: password authentication failed` | Check username/password in connection string |
| SSL required | `psycopg2.OperationalError: SSL required` | Add `?sslmode=require` to connection string |

**Connection String Format:**
```
postgresql://username:password@hostname:5432/database_name
```

---

### MongoDB

**Import:**
```python
from mcp_arena.presents.mongo import MongoDBMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing connection string | `ValueError: MongoDB connection string is required...` | Set `MONGODB_CONNECTION_STRING` env var |
| Connection timeout | `ServerSelectionTimeoutError` | Check MongoDB is running; verify host/port |
| Auth failure | `OperationFailure: Authentication failed` | Verify username/password; check auth database |
| DNS resolution | `ConfigurationError: query() got unexpected keyword` | For Atlas, use `mongodb+srv://` prefix and install `dnspython` |

**Connection String Format:**
```
mongodb://username:password@hostname:27017/database_name

# MongoDB Atlas
mongodb+srv://username:password@cluster.mongodb.net/database_name
```

---

### Redis

**Import:**
```python
from mcp_arena.presents.redis import RedisMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Connection failed | Tools return `{"error": "Redis connection not available"}` | Verify Redis server is running on the specified host/port |
| Auth required | `ResponseError: NOAUTH Authentication required` | Pass `password=` parameter |
| Wrong database | Unexpected data | Verify `db=` parameter (default is `0`) |

**Note:** Redis server connection failures are handled silently — the server starts but tools return errors. Check `server.connected` to verify:

```python
server = RedisMCPServer(host="localhost", port=6379)
if not server.connected:
    print("Redis connection failed!")
```

---

### Docker

**Import:**
```python
from mcp_arena.presents.docker import DockerMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Docker not running | `connected = False` | Start Docker Desktop (Windows/macOS) or the Docker daemon (Linux) |
| Permission denied | `PermissionError` | Add user to `docker` group (Linux): `sudo usermod -aG docker $USER` |
| Socket not found | `FileNotFoundError: /var/run/docker.sock` | Verify Docker is installed and the daemon is running |

**Verifying Docker is available:**
```python
server = DockerMCPServer()
print(f"Docker connected: {server.connected}")
```

---

### GitLab

**Import:**
```python
from mcp_arena.presents.gitlab import GitLabMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Auth failure | `connected = False` | Set `GITLAB_PRIVATE_TOKEN` env var or pass `private_token=` |
| Self-hosted URL | Can't connect | Set `url=` to your GitLab instance URL |
| CI/CD token | Token doesn't work in CI | Use `CI_JOB_TOKEN` env var (auto-set in GitLab CI) |

**Auth Priority:** `private_token` → `oauth_token` → env `GITLAB_PRIVATE_TOKEN` → env `GITLAB_OAUTH_TOKEN` → env `CI_JOB_TOKEN`

---

### Jira

**Import:**
```python
from mcp_arena.presents.jira import JiraMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Connection failed | `connected = False` | Verify URL, username, and API token |
| Cloud vs Server | Wrong API responses | Set `cloud=True` for Atlassian Cloud, `cloud=False` for self-hosted |
| API token | Auth failure | Use an API token (not password) from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens) |

```python
server = JiraMCPServer(
    url="https://your-domain.atlassian.net",
    username="your@email.com",
    password="your_api_token",  # API token, not password
    cloud=True
)
```

---

### Confluence

**Import:**
```python
from mcp_arena.presents.confluence import ConfluenceMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Connection failed | `connected = False` | Verify URL, username, and API token |
| Page content empty | HTML not converting | Ensure `html2text` is installed: `pip install html2text` |
| Space not found | `404` error | Verify space key (case-sensitive) |

```python
server = ConfluenceMCPServer(
    url="https://your-domain.atlassian.net/wiki",
    username="your@email.com",
    password="your_api_token",
    cloud=True
)
```

---

### Bitbucket

**Import:**
```python
from mcp_arena.presents.bitbucket import BitbucketMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Auth failure | Connection error | Use an App Password from [Bitbucket settings](https://bitbucket.org/account/settings/app-passwords/) |
| Cloud vs Server | Wrong API | Set `cloud=True` for Bitbucket Cloud |

**Env Variables:** `BITBUCKET_USERNAME`, `BITBUCKET_APP_PASSWORD`

---

### WhatsApp

**Import:**
```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing credentials | `ValueError: Twilio credentials and WhatsApp number are required` | Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` |
| Number format | Message fails | Use format `whatsapp:+1234567890` |
| Sandbox mode | Messages not delivered | Join the Twilio sandbox first by sending the join code |

---

### VectorDB

**Import:**
```python
from mcp_arena.presents.vectordb import VectorDBMCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| Missing OpenAI key | `ValueError: OpenAI API Key required for OpenAI embeddings` | Set `OPENAI_API_KEY` or use `embedding_provider="huggingface"` |
| Missing Pinecone key | `ValueError: Pinecone credentials missing` | Set `pinecone_api_key` and `pinecone_index_name` |
| ChromaDB error | Various `chromadb` errors | Ensure `chromadb>=1.3.5` is installed |
| Slow first run | Model download takes time | HuggingFace embeddings download models on first use |

**Default transport:** VectorDB server defaults to `"streamable-http"` (unlike other servers that default to `"stdio"`).

```python
# Using free local embeddings (no API key needed)
server = VectorDBMCPServer(
    embedding_provider="huggingface",
    store_provider="chroma"
)

# Using OpenAI embeddings
server = VectorDBMCPServer(
    embedding_provider="openai",
    openai_api_key="sk-..."
)
```

---

### AWS S3

**Import:**
```python
from mcp_arena.presents.aws import S3MCPServer
```

**Common Issues:**

| Problem | Error | Solution |
|---|---|---|
| No credentials | `NoCredentialsError` | Configure AWS credentials via env vars, `~/.aws/credentials`, or constructor params |
| Access denied | `ClientError: AccessDenied` | Verify IAM permissions for S3 operations |
| Region mismatch | `ClientError: PermanentRedirect` | Set correct `region_name=` |

**Credential Options:**
```python
# Option 1: Explicit
server = S3MCPServer(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1"
)

# Option 2: Environment variables
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

# Option 3: AWS credentials file (~/.aws/credentials)
server = S3MCPServer(region_name="us-east-1")
```

---

## General Tips

### Enable Debug Mode

Most servers accept a `debug=True` parameter for verbose logging:

```python
server = GithubMCPServer(token="...", debug=True)
```

### Using `.env` Files

mcp_arena automatically loads `.env` files via `python-dotenv`. Create a `.env` file in your project root:

```env
GITHUB_TOKEN=ghp_your_token
SLACK_TOKEN=xoxb-your-token
NOTION_TOKEN=ntn_your_token
POSTGRES_CONNECTION_STRING=postgresql://user:pass@localhost/db
GROQ_API_KEY=gsk_your_key
```

### Check Server Connection Status

Servers that use soft-fail connection (Docker, Redis, GitLab, Jira, Confluence, Bitbucket) expose a `connected` attribute:

```python
server = DockerMCPServer()
if not server.connected:
    print("Warning: Docker is not available")
```

### Headless Environments (CI/CD, Servers)

The `LocalOperationsMCPServer` depends on `pyautogui` for GUI operations, but it handles headless environments gracefully — GUI tools are simply disabled when no display is available.

---

## Getting Help

- **Documentation:** [https://mcparena.vercel.app/docs](https://mcparena.vercel.app/docs)
- **GitHub Issues:** [https://github.com/SatyamSingh8306/mcp_arena/issues](https://github.com/SatyamSingh8306/mcp_arena/issues)
- **Community Discussions:** [https://github.com/SatyamSingh8306/mcp_arena/discussions](https://github.com/SatyamSingh8306/mcp_arena/discussions)
- **PyPI:** [https://pypi.org/project/mcp-arena/](https://pypi.org/project/mcp-arena/)
