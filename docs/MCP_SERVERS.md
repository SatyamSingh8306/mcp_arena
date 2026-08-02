# Available MCP Servers — install & run reference

> **The headline feature of `mcp_arena` is the MCP server.** This doc is a focused reference: what presets ship today, what extra to install for each, what credentials they need, and how to run them.

If you want the prose walk-through instead, see [`QUICKSTART.md`](QUICKSTART.md). For the full constructor surface and writing your own preset, see [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md).

---

## What `pip install mcp-arena` already gives you

Three general-purpose presets ship in **core** — no extra needed:

| Preset | Class | Use it for |
| ------ | ----- | ---------- |
| Local operations | `LocalOperationsMCPServer` | file / system / process tools on your own machine |
| Generic API | `GenericAPIMCPServer` | make any HTTP request (saves API calls, request bodies, retries) |
| SMTP | `SMTPServer` | send email via any SMTP server |

```bash
pip install mcp-arena
python -c "
from mcp_arena.presents.local_operation import LocalOperationsMCPServer
LocalOperationsMCPServer().run()
"
```

That's a working MCP server with one command.

Everything else is gated behind an extra. If you try to instantiate a gated preset without its extra, you get a clear `ImportError` pointing at the install command:

```
PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

## What ships today — 30+ presets

The lazy loader in `mcp_arena.presents` AST-scans the package directory and exports every class whose name ends in `Server`. Concretely, as of `0.4.0`:

| # | Module | Class | Extra to install |
| - | ------ | ----- | ----------------- |
| **Communication** | | | |
| 1 | `slack`         | `SlackMCPServer`         | `mcp-arena[slack]` |
| 2 | `whatsapp`      | `WhatsAppMCPServer`      | `mcp-arena[whatsapp]` |
| 3 | `gmail`         | `GmailMCPServer`         | `mcp-arena[gmail]` |
| 4 | `outlook`       | `OutlookMCPServer`       | `mcp-arena[outlook]` |
| 5 | `smtp`          | `SMTPMCPServer`          | `mcp-arena[mail]` |
| 6 | `mail`          | `MailMCPServer`          | `mcp-arena[mail]` |
| 7 | `notification`  | `NotificationMCPServer`  | `mcp-arena[notification]` |
| **Dev platforms** | | | |
| 8 | `github`        | `GithubMCPServer`        | `mcp-arena[github]` |
| 9 | `gitlab`        | `GitLabMCPServer`        | `mcp-arena[gitlab]` |
| 10 | `bitbucket`    | `BitbucketMCPServer`     | `mcp-arena[bitbucket]` |
| **Productivity** | | | |
| 11 | `notion`       | `NotionMCPServer`        | `mcp-arena[notion]` |
| 12 | `confluence`   | `ConfluenceMCPServer`    | `mcp-arena[bitbucket]` |
| 13 | `jira`         | `JiraMCPServer`          | `mcp-arena[bitbucket]` |
| **Data & storage** | | | |
| 14 | `postgres`     | `PostgresMCPServer`      | `mcp-arena[postgres]` |
| 15 | `mongo`        | `MongoDBMCPServer`       | `mcp-arena[mongodb]` |
| 16 | `redis`        | `RedisMCPServer`         | `mcp-arena[redis]` |
| 17 | `vectordb`     | `VectorDBMCPServer`      | `mcp-arena[vectordb]` |
| **Cloud / OS** | | | |
| 18 | `aws`          | `S3MCPServer`            | `mcp-arena[cloudstorage]` |
| 19 | `cloudstorage` | `CloudStorageMCPServer`  | `mcp-arena[cloudstorage]` |
| 20 | `docker`       | `DockerMCPServer`        | `mcp-arena[docker]` |
| 21 | `local_operation` | `LocalOperationsMCPServer` | `mcp-arena[local_operation]` |
| 22 | `screencapture` | `ScreenCaptureMCPServer` | `mcp-arena[screencapture]` |
| **Browser / web / media** | | | |
| 23 | `browser`      | `BrowserMCPServer`       | `mcp-arena[browser]` |
| 24 | `webscraping`  | `WebScrapingMCPServer`   | `mcp-arena[webscraping]` |
| 25 | `generic_api`  | `GenericAPIMCPServer`    | `mcp-arena[generic_api]` |
| 26 | `image`        | `ImageMCPServer`         | `mcp-arena[image]` |
| 27 | `video`        | `VideoMCPServer`         | `mcp-arena[video]` |
| 28 | `audio`        | `AudioMCPServer`         | `mcp-arena[audio]` |
| 29 | `pdf`          | `PDFMCPServer`           | `mcp-arena[pdf]` |
| 30 | `qrcode`       | `QRCodeMCPServer`        | `mcp-arena[qrcode]` |
| 31 | `spreadsheet`  | `SpreadsheetMCPServer`   | `mcp-arena[spreadsheet]` |

> Drop a new `<your_preset>.py` in `mcp_arena/presents/` and it appears in this list automatically — see [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md#custom) for the recipe.

---

## How to install

`mcp_arena` has a no-presets core, plus one extra per preset / group. You only pay for what you use.

```bash
# 1. Core only (CLI + base classes; no preset can actually run yet)
pip install mcp-arena

# 2. One preset
pip install "mcp-arena[github]"

# 3. Several at once
pip install "mcp-arena[github,slack,postgres,redis]"

# 4. Everything (heavy)
pip install "mcp-arena[all]"

# 5. Core + the LangChain bridge (you'll still need the matching preset extras)
pip install "mcp-arena[agents] langchain-openai"
```

### Bundle extras

| Bundle          | What it pulls in                                                            |
| --------------- | -------------------------------------------------------------------------- |
| `email`         | `[gmail,outlook]`                                                          |
| `messaging`     | `[slack,whatsapp]`                                                         |
| `communication` | `[gmail,outlook,slack,whatsapp]`                                            |
| `mail`          | `[gmail,outlook]` (used by `MailMCPServer` / `SMTPMCPServer`)              |
| `notification`  | `[communication]`                                                          |
| `all`           | every preset extra + `[agents]`                                             |
| `complete`      | `[all,dev]` — adds `pytest`, `black`, `ruff`, `mypy`, `pre-commit`          |
| `dev`           | test/lint tools only (no presets)                                          |

Python 3.12+ is required (`langchain>=1.0,<2.0` and `chromadb>=1.3.5` both need it).

---

## How to run a server

Three ways. Pick whichever fits your client.

### 1. From Python (any preset)

```python
# server.py
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(
    token="ghp_…",                        # or pull from $GITHUB_TOKEN
    host="127.0.0.1",
    port=8000,
    transport="stdio",                     # stdio (default) | sse | http
    debug=False,
)

if __name__ == "__main__":
    server.run()
```

Run it: `python server.py`. Now point any MCP client at the process.

### 2. From the CLI

```bash
mcp-arena list                  # every preset mcp_arena knows about
mcp-arena run github --help     # preset-specific options
mcp-arena run github --token "$GITHUB_TOKEN"
mcp-arena run github --token "$GITHUB_TOKEN" --transport sse --host 0.0.0.0 --port 8001
```

The CLI is generated from each preset's `__init__` signature — so every kwarg is also a `--flag`.

### 3. Standalone for stdio clients (Claude Desktop, Cursor, …)

Add to your client's MCP config:

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["-m", "mcp_arena.presents.github"],
      "env": { "GITHUB_TOKEN": "ghp_…" }
    }
  }
}
```

The CLI command `mcp-arena run github …` is a thin wrapper around this.

---

## Credentials each server reads

Most presets accept credentials as **constructor kwargs** *or* **environment variables** (and the preset picks the env var if you skip the kwarg). Use whatever's easier; the env-var fallback is there so you can ship a `.env` file.

| Server | Env var(s) it reads |
| ------ | ------------------- |
| `github`        | `GITHUB_TOKEN` |
| `gitlab`        | `GITLAB_PRIVATE_TOKEN`, `GITLAB_OAUTH_TOKEN`, `CI_JOB_TOKEN` |
| `bitbucket`     | `BITBUCKET_USERNAME` + `BITBUCKET_APP_PASSWORD` (or OAuth) |
| `notion`        | `NOTION_TOKEN` |
| `confluence`    | `CONFLUENCE_USERNAME` + `CONFLUENCE_PASSWORD` |
| `jira`          | `JIRA_USERNAME` + `JIRA_PASSWORD` |
| `slack`         | `SLACK_BOT_TOKEN` (preferred) or `SLACK_TOKEN` |
| `whatsapp`      | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` |
| `gmail`         | `GMAIL_CREDENTIALS_PATH` (OAuth JSON) |
| `outlook`       | (MSAL client — set via constructor) |
| `smtp`          | `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` |
| `postgres`      | `POSTGRES_CONNECTION_STRING` |
| `mongo`         | `MONGODB_CONNECTION_STRING` |
| `redis`         | (constructor kwargs — host/port/password) |
| `vectordb`      | (constructor kwargs; OpenAI uses `OPENAI_API_KEY` for embeddings) |
| `aws`           | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` |
| `cloudstorage`  | `GCS_PROJECT_ID`, `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS` |
| `docker`        | (reads Docker socket / config) |
| `local_operation` | none (uses `psutil`) |
| `screencapture` | none (uses `pyautogui`) |
| `browser`       | none (uses Playwright) |
| `webscraping`   | none (uses `requests` / `beautifulsoup4`) |
| `generic_api`   | none |
| `image`, `video`, `audio`, `pdf`, `qrcode`, `spreadsheet` | none |

A `.env` file at the project root is auto-loaded on `import mcp_arena` (via `python-dotenv`).

---

## Recipes per category

### Communication

```bash
pip install "mcp-arena[slack]"
```

```python
import os
from mcp_arena.presents.slack import SlackMCPServer

server = SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"])
server.run()
```

```bash
pip install "mcp-arena[whatsapp]"
```
```python
server = WhatsAppMCPServer()   # pulls TWILIO_* from env
server.run()
```

```bash
pip install "mcp-arena[gmail,outlook]"
```
```python
from mcp_arena.presents.gmail import GmailMCPServer
server = GmailMCPServer(credentials_path="./gmail_creds.json")
server.run()
```

```bash
pip install "mcp-arena[communication]"   # gmail + outlook + slack + whatsapp
```

### Dev platforms

```bash
pip install "mcp-arena[github]"
```
```python
from mcp_arena.presents.github import GithubMCPServer
server = GithubMCPServer(token=os.environ["GITHUB_TOKEN"])
server.run()
```

```bash
pip install "mcp-arena[gitlab]"
pip install "mcp-arena[bitbucket]"
```

### Productivity

```bash
pip install "mcp-arena[notion]"
pip install "mcp-arena[bitbucket]"   # atlassian-python-api covers jira + confluence + bitbucket
```

### Data & storage

```bash
pip install "mcp-arena[postgres]"
pip install "mcp-arena[mongodb]"
pip install "mcp-arena[redis]"
pip install "mcp-arena[vectordb]"   # chromadb + sentence-transformers (heavy)
```

### Cloud / OS

```bash
pip install "mcp-arena[cloudstorage]"   # boto3 + google-cloud-storage
pip install "mcp-arena[docker]"
pip install "mcp-arena[local_operation]"
pip install "mcp-arena[screencapture]"
```

### Browser / web / media

```bash
pip install "mcp-arena[browser]"          # playwright + opencv + pillow
pip install "mcp-arena[webscraping]"      # requests + bs4 + selenium
pip install "mcp-arena[generic_api]"      # httpx
pip install "mcp-arena[image]"            # pillow + opencv
pip install "mcp-arena[video]"            # moviepy + numpy
pip install "mcp-arena[audio]"            # pydub + librosa + numpy
pip install "mcp-arena[pdf]"              # PyMuPDF + PyPDF2 + reportlab + pdfplumber
pip install "mcp-arena[qrcode]"           # qrcode[pil]
pip install "mcp-arena[spreadsheet]"      # pandas + openpyxl
```

---

## Pick a transport

Every preset supports all three transports; pick by where the client lives.

| Transport         | Endpoint                        | Use when                                       |
| ----------------- | ------------------------------- | ---------------------------------------------- |
| `stdio` (default) | in-process via stdin/stdout     | Local MCP clients (Claude Desktop, Cursor), the `make_mcp_agent` flow |
| `sse`             | `http://<host>:<port>/sse`      | Browser clients, streaming, server-sent events |
| `http`            | `http://<host>:<port>/mcp`      | Multi-process / networked setups, custom clients |

```python
# Same server, three ways
server = GithubMCPServer(token="…", transport="stdio")             # default
server = GithubMCPServer(token="…", transport="sse", port=8001)    # listen on :8001/sse
server = GithubMCPServer(token="…", transport="http", port=8001)   # listen on :8001/mcp
```

---

## How to install *every* preset

If you're kicking the tyres and want the whole library:

```bash
pip install "mcp-arena[all]"
```

That's ~30 packages. Use `pip install "mcp-arena[complete]"` if you also want dev tooling (pytest, black, ruff, mypy, pre-commit).

---

## After it's running

Once `server.run()` is going, you have three consumers you can attach:

1. **Any MCP client** (Claude Desktop, Cursor, your own) — speak MCP over the transport you chose.
2. **The `make_mcp_agent` bridge** — pass the same `BaseMCPServer` instance to a LangChain agent. See [`LANGCHAIN_INTEGRATION.md`](LANGCHAIN_INTEGRATION.md).
3. **The `MCPAgentWrapper`** — pull the tools out as plain Python callables, no MCP client needed. See [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md).

```python
# 1. Plain MCP client (any)
server.run()                     # stdio — client spawns the process

# 2. LangChain agent
from mcp_arena.agent import make_mcp_agent
agent = await make_mcp_agent(llm, [server], system_prompt="…")

# 3. Plain Python callables
from mcp_arena.wrapper import MCPAgentWrapper
for tool in MCPAgentWrapper(server).get_tools():
    print(tool["function"]["name"])
```

Pick one, then read the matching doc:

- MCP client / `make_mcp_agent` → [`LANGCHAIN_INTEGRATION.md`](LANGCHAIN_INTEGRATION.md)
- `MCPAgentWrapper` / writing your own preset → [`MCP_SERVERS_GUIDE.md`](MCP_SERVERS_GUIDE.md)