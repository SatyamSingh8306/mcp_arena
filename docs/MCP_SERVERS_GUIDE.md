# MCP Servers Guide

`mcp_arena` ships 32 ready-to-run MCP server presets. Each preset is a `BaseMCPServer` subclass that registers its tools at construction. The `mcp_arena.presents` loader discovers them automatically: drop a `*.py` file in `mcp_arena/presents/` and `from mcp_arena.presents import YourMCPServer` works.

## Contents

- [1. Architecture](#1-architecture)
- [2. BaseMCPServer](#2-basemcpserver)
- [3. Presets by category](#3-presets-by-category)
- [4. Custom presets](#4-custom-presets)
- [5. Running presets](#5-running-presets)
- [6. Using presets with LangChain](#6-using-presets-with-langchain)
- [7. Best practices](#7-best-practices)

## 1. Architecture

```text
BaseMCPServer (abstract — mcp_arena.mcp.server)
    |
    +-- self.mcp_server : FastMCP
    +-- self._registered_tools : dict[str, Callable]
    +-- subclass overrides _register_tools() to add tools
```

`_register_tools()` registers functions with FastMCP via `self.mcp_server.tool()`. After construction, the same functions are copied into `_registered_tools` so non-MCP consumers can inspect and call them.

For stdio connections, `make_mcp_agent` launches a preset as `python -m mcp_arena.presents.<module>`. Each module should define one `*Server` class with a constructor that can be called from environment variables alone.

## 2. BaseMCPServer

```python
from mcp_arena.mcp.server import BaseMCPServer

class MyServer(BaseMCPServer):
    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def hello(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"
```

The constructor (`auto_register_tools=True` by default) creates the FastMCP instance, calls `_register_tools()`, and synchronizes the registered functions into `_registered_tools`.

### Transports

| Transport | Server endpoint |
| --- | --- |
| `stdio` (default) | stdin/stdout |
| `sse` | `http://<host>:<port>/sse` |
| `streamable-http` | `http://<host>:<port>/mcp` |

Call `server.run()` to use the instance's transport, or override it with `server.run(transport="sse")`.

### Constructor arguments

| Argument | Meaning |
| --- | --- |
| `name` | Server name |
| `description` | Server instructions shown to clients |
| `host` | Bind address (default `127.0.0.1`) |
| `port` | Bind port (default `8000`) |
| `transport` | `stdio`, `sse`, or `streamable-http` |
| `debug` | Enable debug logging |
| `log_level` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL` |
| `mount_path`, `sse_path`, `streamable_http_path` | Override HTTP endpoint paths |
| `auto_register_tools` | Register tools during construction (default `True`) |

Each preset adds its own arguments for credentials, output directories, and formats.

## 3. Presets by category

The extra column shows what to install; a blank entry means the preset is in core.

### Communication

| Preset | Class | Extra | Notes |
| --- | --- | --- | --- |
| Slack | `SlackMCPServer` | `mcp-arena[slack]` | Channels, messages, workflows |
| WhatsApp | `WhatsAppMCPServer` | `mcp-arena[whatsapp]` | Twilio; needs `TWILIO_*` variables |
| Gmail | `GmailMCPServer` | `mcp-arena[mail]` | OAuth; needs `credentials.json` |
| Outlook | `OutlookMCPServer` | `mcp-arena[outlook]` | MSAL |
| SMTP | `SMTPServer` | core | Outbound email companion |

### Dev platforms

| Preset | Class | Extra |
| --- | --- | --- |
| GitHub | `GithubMCPServer` | `mcp-arena[github]` |
| GitLab | `GitLabMCPServer` | `mcp-arena[gitlab]` |
| Bitbucket | `BitbucketMCPServer` | `mcp-arena[bitbucket]` |

### Productivity

| Preset | Class | Extra |
| --- | --- | --- |
| Notion | `NotionMCPServer` | `mcp-arena[notion]` |
| Confluence | `ConfluenceMCPServer` | `mcp-arena[bitbucket]` |
| Jira | `JiraMCPServer` | `mcp-arena[bitbucket]` |

### Data and storage

| Preset | Class | Extra |
| --- | --- | --- |
| PostgreSQL | `PostgresMCPServer` | `mcp-arena[postgres]` |
| MongoDB | `MongoDBMCPServer` | `mcp-arena[mongodb]` |
| Redis | `RedisMCPServer` | `mcp-arena[redis]` |
| VectorDB (Chroma) | `VectorDBMCPServer` | `mcp-arena[vectordb]` |

### Monitoring

| Preset | Class | Extra | Notes |
| --- | --- | --- | --- |
| Sentry | `SentryMCPServer` | `mcp-arena[sentry]` | Read-only projects, issues, and issue events |

### AI and documentation

| Preset | Class | Extra | Notes |
| --- | --- | --- | --- |
| Context7 | `Context7MCPServer` | `mcp-arena[context7]` | `resolve_library_id`, `query_docs`, `search_docs`; optional `CONTEXT7_API_KEY` |

### Cloud and OS

| Preset | Class | Extra |
| --- | --- | --- |
| AWS S3 | `S3MCPServer` | `mcp-arena[cloudstorage]` |
| Cloud storage (multi) | `CloudStorageMCPServer` | `mcp-arena[cloudstorage]` |
| Docker | `DockerMCPServer` | `mcp-arena[docker]` |
| Local operations | `LocalOperationsMCPServer` | core |
| Screen capture | `ScreenCaptureMCPServer` | `mcp-arena[screencapture]` |

### Browser, web, and media

| Preset | Class | Extra | Notes |
| --- | --- | --- | --- |
| Browser (Playwright) | `BrowserMCPServer` | `mcp-arena[browser]` | Navigation, screenshots, form filling, OCR |
| Web scraping | `WebScrapingMCPServer` | `mcp-arena[webscraping]` | requests, BeautifulSoup, Selenium |
| Generic API | `GenericAPIMCPServer` | core | Generic HTTP wrapper |
| Image | `ImageMCPServer` | `mcp-arena[image]` | Pillow and OpenCV |
| Video | `VideoMCPServer` | `mcp-arena[video]` | moviepy and numpy |
| Audio | `AudioMCPServer` | `mcp-arena[audio]` | pydub and librosa |
| PDF | `PDFMCPServer` | `mcp-arena[pdf]` | PyMuPDF, PyPDF2, reportlab, pdfplumber |
| QR code | `QRCodeMCPServer` | `mcp-arena[qrcode]` | Generate and decode |
| Spreadsheet | `SpreadsheetMCPServer` | `mcp-arena[spreadsheet]` | pandas and openpyxl |

## 4. Custom presets

```python
from mcp_arena.mcp.server import BaseMCPServer

class GreeterMCPServer(BaseMCPServer):
    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def greet(name: str, style: str = "friendly") -> str:
            """Greet someone in a chosen tone."""
            styles = {"friendly": "Hi", "formal": "Hello", "casual": "Hey"}
            return f"{styles.get(style, 'Hi')}, {name}!"
```

Save as `mcp_arena/presents/greeter.py`, then import and run it:

```python
from mcp_arena.presents import GreeterMCPServer

server = GreeterMCPServer(name="greeter", description="Greeter")
server.run()
```

The loader in `mcp_arena/presents/__init__.py` parses each module with `ast` and exports every class whose name ends in `Server`.

If your server lives outside `mcp_arena/presents/`, the stdio auto-spawn used by `make_mcp_agent` cannot find a `python -m` target. Start the server yourself and connect over SSE or `streamable-http`.

## 5. Running presets

Directly:

```python
from mcp_arena.presents.github import GithubMCPServer

GithubMCPServer(token="ghp_...").run()
```

With a transport override:

```python
GithubMCPServer(token="ghp_...", transport="sse", host="0.0.0.0", port=8001).run()
```

From the CLI:

```bash
mcp-arena list
mcp-arena info github
mcp-arena run --mcp-server github --token "$GITHUB_TOKEN"
```

Using environment variables only:

```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer

WhatsAppMCPServer().run()
```

## 6. Using presets with LangChain

The same server objects can be handed to `make_mcp_agent`:

```python
import asyncio
import os

from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.slack import SlackMCPServer

async def main():
    agent = await make_mcp_agent(
        ChatOpenAI(model="gpt-4o"),
        [
            GithubMCPServer(token=os.environ["GITHUB_TOKEN"]),
            SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"]),
        ],
        system_prompt="You can search GitHub and post to Slack.",
    )
    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": "Find my top-3 starred repos and DM me the list.",
        }]
    })
    print(result["messages"][-1].content)

asyncio.run(main())
```

See [Agent Guide](AGENT_GUIDE.md) for tool filtering and forwarded `create_agent` parameters.

## 7. Best practices

- Keep credentials in environment variables rather than in source code. Presets read from `os.environ` when an argument is omitted.
- Use one transport per server instance. For both `stdio` and HTTP access, create two instances.
- Prefer `stdio` for local agent workflows and `streamable-http` or `sse` for networked setups.
- Set `debug=True` on the constructor when you need verbose logs; it is independent of the transport.
