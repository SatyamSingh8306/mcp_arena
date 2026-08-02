# MCP Servers Guide

`mcp_arena` ships ~30 ready-to-use MCP server presets. Each preset is a `BaseMCPServer` subclass that registers its tools at construction time; `mcp_arena.presents` discovers them automatically — drop a `*.py` in `mcp_arena/presents/` and `from mcp_arena.presents import XMCPServer` just works.

## Table of contents
1. [Architecture](#architecture)
2. [`BaseMCPServer`](#base)
3. [Presets by category](#presets)
4. [Custom presets](#custom)
5. [Running presets](#running)
6. [Handing presets to a LangChain agent](#integration)
7. [Best practices](#best-practices)

---

<a id="architecture"></a>
## 1. Architecture

```
BaseMCPServer (abstract — mcp_arena.mcp.server)
    │
    ├── self.mcp_server : FastMCP            # the actual MCP server
    ├── self._registered_tools : Dict[str, Callable]
    │     # populated when subclasses register via self.mcp_server.tool()
    │
    └── subclass overrides _register_tools() to add tools
```

Subprocess stdio servers are launched as `python -m mcp_arena.presents.<module>` by `make_mcp_agent`'s `_config_for` function. Each `<module>.py` must define exactly one `*Server` class.

---

<a id="base"></a>
## 2. `BaseMCPServer`

```python
from mcp_arena.mcp.server import BaseMCPServer

class MyServer(BaseMCPServer):
    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def hello(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"
```

The default constructor (`auto_register_tools=True`) wires up FastMCP, runs your `_register_tools`, and copies the registered functions into `self._registered_tools` so non-MCP clients (and `ToolRegistry`) can introspect them.

### Transport options

| Transport      | Server endpoint                    |
| -------------- | ---------------------------------- |
| `stdio`        | in-process via stdin/stdout        |
| `sse`          | `http://<host>:<port>/sse`         |
| `http`         | `http://<host>:<port>/mcp`         |
| `streamable-http` | alias for `http`                |

Run with `server.run()` — uses the transport set on the instance — or pass an override: `server.run(transport="sse")`.

### Constructor kwargs (most presets)

| Key            | Meaning                                                                  |
| -------------- | ------------------------------------------------------------------------ |
| `host`         | bind address (default `127.0.0.1`)                                       |
| `port`         | bind port (default `8000`)                                               |
| `transport`    | `stdio` / `sse` / `http`                                                 |
| `debug`        | verbose logs                                                             |
| `log_level`    | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`                     |

Each preset adds its own kwargs (credentials, output dirs, default formats, etc.) on top.

---

<a id="presets"></a>
## 3. Presets by category

### Communication
| Preset                       | Class                         | Requires                          | Notes |
| ---------------------------- | ----------------------------- | --------------------------------- | ----- |
| Slack                        | `SlackMCPServer`              | `mcp-arena[slack]`                | channels, messages, workflows |
| WhatsApp                     | `WhatsAppMCPServer`           | `mcp-arena[whatsapp]`             | Twilio-backed; needs `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` |
| Gmail                        | `GmailMCPServer`              | `mcp-arena[gmail]`                | OAuth; needs `credentials.json` |
| Outlook                      | `OutlookMCPServer`            | `mcp-arena[outlook]`              | MSAL |
| SMTP                         | `SMTPMCPServer`               | `mcp-arena[mail]` (pulls in gmail/outlook) | Outbound-only companion |
| Mail                         | `MailMCPServer`               | `mcp-arena[mail]`                 | Facade over Gmail + Outlook |
| Notification                 | `NotificationMCPServer`       | `mcp-arena[notification]`         | email + Slack + webhook |

### Dev platforms
| Preset                       | Class                         | Requires                          |
| ---------------------------- | ----------------------------- | --------------------------------- |
| GitHub                       | `GithubMCPServer`             | `mcp-arena[github]`               |
| GitLab                       | `GitLabMCPServer`             | `mcp-arena[gitlab]`               |
| Bitbucket                    | `BitbucketMCPServer`          | `mcp-arena[bitbucket]`            |

### Productivity
| Preset                       | Class                         | Requires                          |
| ---------------------------- | ----------------------------- | --------------------------------- |
| Notion                       | `NotionMCPServer`             | `mcp-arena[notion]`               |
| Confluence                   | `ConfluenceMCPServer`         | `mcp-arena[bitbucket]` (atlassian-python-api) |
| Jira                         | `JiraMCPServer`               | `mcp-arena[bitbucket]` (atlassian-python-api) |

### Data & storage
| Preset                       | Class                         | Requires                          |
| ---------------------------- | ----------------------------- | --------------------------------- |
| PostgreSQL                   | `PostgresMCPServer`           | `mcp-arena[postgres]`             |
| MongoDB                      | `MongoDBMCPServer`            | `mcp-arena[mongodb]`              |
| Redis                        | `RedisMCPServer`              | `mcp-arena[redis]`                |
| VectorDB (Chroma)            | `VectorDBMCPServer`           | `mcp-arena[vectordb]`             |

### Cloud
| Preset                       | Class                         | Requires                          |
| ---------------------------- | ----------------------------- | --------------------------------- |
| AWS S3                       | `S3MCPServer`                 | `mcp-arena[cloudstorage]` (boto3) |
| Cloud storage (multi)        | `CloudStorageMCPServer`       | `mcp-arena[cloudstorage]`         |
| Docker                       | `DockerMCPServer`             | `mcp-arena[docker]`               |

### System / OS
| Preset                       | Class                         | Requires                          |
| ---------------------------- | ----------------------------- | --------------------------------- |
| Local operations             | `LocalOperationsMCPServer`    | `mcp-arena[local_operation]`      |
| Screen capture               | `ScreenCaptureMCPServer`      | `mcp-arena[screencapture]`        |

### Browser / web / media
| Preset                       | Class                         | Requires                          | Notes |
| ---------------------------- | ----------------------------- | --------------------------------- | ----- |
| Browser (Playwright)         | `BrowserMCPServer`            | `mcp-arena[browser]`              | navigate, screenshot, form-fill, OCR |
| Web scraping                 | `WebScrapingMCPServer`        | `mcp-arena[webscraping]`          | requests + BS4 + selenium |
| Generic API                  | `GenericAPIMCPServer`         | `mcp-arena[generic_api]`          | generic HTTP wrapper |
| Image                        | `ImageMCPServer`              | `mcp-arena[image]`                | PIL + OpenCV |
| Video                        | `VideoMCPServer`              | `mcp-arena[video]`                | moviepy + numpy |
| Audio                        | `AudioMCPServer`              | `mcp-arena[audio]`                | pydub + librosa |
| PDF                          | `PDFMCPServer`                | `mcp-arena[pdf]`                  | PyMuPDF + PyPDF2 + reportlab + pdfplumber |
| QR code                      | `QRCodeMCPServer`             | `mcp-arena[qrcode]`               | generate / decode |
| Spreadsheet                  | `SpreadsheetMCPServer`        | `mcp-arena[spreadsheet]`          | pandas + openpyxl (xlsx/csv) |

> The list above is what `mcp_arena/presents/*.py` ships today. Drop a new file in there and it'll auto-appear in the next section.

---

<a id="custom"></a>
## 4. Custom presets

```python
# mcp_arena/presents/greeter.py
from mcp_arena.mcp.server import BaseMCPServer

class GreeterMCPServer(BaseMCPServer):
    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def greet(name: str, style: str = "friendly") -> str:
            """Greet someone in a chosen tone."""
            styles = {"friendly": "Hi", "formal": "Hello", "casual": "Hey"}
            return f"{styles.get(style, 'Hi')}, {name}!"
```

Then:

```python
from mcp_arena.presents import GreeterMCPServer

server = GreeterMCPServer(name="greeter", description="Greeter")
server.run()
```

The lazy loader in `mcp_arena/presents/__init__.py` walks the directory and AST-parses each `.py`; any class whose name ends in `Server` gets exported under that exact name.

If your custom server lives outside `mcp_arena/presents/` (e.g. in user code), `make_mcp_agent`'s stdio auto-spawn won't find a `python -m` target — start the server yourself and pass it via SSE/HTTP.

---

<a id="running"></a>
## 5. Running presets

### Direct

```python
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(token="ghp_…")
server.run()
```

### Choose a transport

```python
server = GithubMCPServer(token="ghp_…", transport="sse", host="0.0.0.0", port=8001)
server.run()
```

### CLI

```bash
mcp-arena list            # see all presets
mcp-arena run github --token "$GITHUB_TOKEN"
mcp-arena run gmail --help
```

### Environment-only instantiation

Most presets read credentials from env vars:

```python
import os
from mcp_arena.presents.whatsapp import WhatsAppMCPServer

server = WhatsAppMCPServer()  # pulls TWILIO_* from os.environ
server.run()
```

---

<a id="integration"></a>
## 6. Handing presets to a LangChain agent

This is the main path. See also [`AGENT_GUIDE.md`](AGENT_GUIDE.md) and [`LANGCHAIN_INTEGRATION.md`](LANGCHAIN_INTEGRATION.md).

```python
import asyncio
from langchain_openai import ChatOpenAI
from mcp_arena.agent import make_mcp_agent
from mcp_arena.presents.github import GithubMCPServer
from mcp_arena.presents.slack import SlackMCPServer

async def main():
    llm = ChatOpenAI(model="gpt-4o")
    agent = await make_mcp_agent(
        llm,
        [GithubMCPServer(token="ghp_…"), SlackMCPServer(token="xoxb-…")],
        system_prompt="You can search GitHub and post to Slack.",
    )
    out = await agent.ainvoke({
        "messages": [{"role": "user", "content": "Find my top-3 starred repos and DM me the list."}]
    })
    print(out["messages"][-1].content)

asyncio.run(main())
```

---

<a id="best-practices"></a>
## 7. Best practices

**Credentials in env vars, not in code.** Most presets read from `os.environ` first. Override per-instance if you need to.

**One transport per server.** If you need both `stdio` and `http` connections, instantiate the server twice.

**Use stdio for local agent workflows; HTTP/SSE for multi-process or networked setups.** Stdio is the easiest path for `make_mcp_agent`.

**Auto-register is on by default.** Override with `auto_register_tools=False` if you want to call `_register_tools()` later (useful for testing).

**Debug logging lives on the server, not on transport.** Pass `debug=True` to the preset constructor.
