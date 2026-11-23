# MCP Servers

Reference for the presets that ship with `mcp_arena`: what each one does, which extra it needs, which credentials it reads, and how to run it. For a prose walkthrough, see [Quick Start](QUICKSTART.md). For constructor options and custom presets, see [MCP Servers Guide](MCP_SERVERS_GUIDE.md).

## Core presets

Three general-purpose presets ship in the core package:

| Preset | Class | Purpose |
| --- | --- | --- |
| Local operations | `LocalOperationsMCPServer` | File, system, and process tools |
| Generic API | `GenericAPIMCPServer` | Arbitrary HTTP requests |
| SMTP | `SMTPServer` | Outbound email via any SMTP server |

```bash
pip install mcp-arena
python -c "from mcp_arena.presents.local_operation import LocalOperationsMCPServer; LocalOperationsMCPServer().run()"
```

All other presets require an extra. Without it, construction raises an `ImportError` with the install command:

```text
PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

## Available presets

The lazy loader in `mcp_arena.presents` discovers every class whose name ends in `Server`. As of 0.5.0 the following presets ship:

| # | Module | Class | Extra |
| - | ------ | ----- | ----- |
| **Communication** | | | |
| 1 | `slack` | `SlackMCPServer` | `mcp-arena[slack]` |
| 2 | `whatsapp` | `WhatsAppMCPServer` | `mcp-arena[whatsapp]` |
| 3 | `gmail` | `GmailMCPServer` | `mcp-arena[gmail]` |
| 4 | `outlook` | `OutlookMCPServer` | `mcp-arena[outlook]` |
| 5 | `smtp` | `SMTPServer` | core |
| 6 | `mail` | `GmailMCPServer` | `mcp-arena[mail]` |
| 7 | `notification` | `NotificationMCPServer` | `mcp-arena[notification]` |
| **Dev platforms** | | | |
| 8 | `github` | `GithubMCPServer` | `mcp-arena[github]` |
| 9 | `gitlab` | `GitLabMCPServer` | `mcp-arena[gitlab]` |
| 10 | `bitbucket` | `BitbucketMCPServer` | `mcp-arena[bitbucket]` |
| **Productivity** | | | |
| 11 | `notion` | `NotionMCPServer` | `mcp-arena[notion]` |
| 12 | `confluence` | `ConfluenceMCPServer` | `mcp-arena[bitbucket]` |
| 13 | `jira` | `JiraMCPServer` | `mcp-arena[bitbucket]` |
| **Data and storage** | | | |
| 14 | `postgres` | `PostgresMCPServer` | `mcp-arena[postgres]` |
| 15 | `mongo` | `MongoDBMCPServer` | `mcp-arena[mongodb]` |
| 16 | `redis` | `RedisMCPServer` | `mcp-arena[redis]` |
| 17 | `vectordb` | `VectorDBMCPServer` | `mcp-arena[vectordb]` |
| **Monitoring** | | | |
| 18 | `sentry` | `SentryMCPServer` | `mcp-arena[sentry]` |
| **AI and documentation** | | | |
| 19 | `context7` | `Context7MCPServer` | `mcp-arena[context7]` |
| **Cloud and OS** | | | |
| 20 | `aws` | `S3MCPServer` | `mcp-arena[cloudstorage]` |
| 21 | `cloudstorage` | `CloudStorageMCPServer` | `mcp-arena[cloudstorage]` |
| 22 | `docker` | `DockerMCPServer` | `mcp-arena[docker]` |
| 23 | `local_operation` | `LocalOperationsMCPServer` | core |
| 24 | `screencapture` | `ScreenCaptureMCPServer` | `mcp-arena[screencapture]` |
| **Browser, web, and media** | | | |
| 25 | `browser` | `BrowserMCPServer` | `mcp-arena[browser]` |
| 26 | `webscraping` | `WebScrapingMCPServer` | `mcp-arena[webscraping]` |
| 27 | `generic_api` | `GenericAPIMCPServer` | core |
| 28 | `image` | `ImageMCPServer` | `mcp-arena[image]` |
| 29 | `video` | `VideoMCPServer` | `mcp-arena[video]` |
| 30 | `audio` | `AudioMCPServer` | `mcp-arena[audio]` |
| 31 | `pdf` | `PDFMCPServer` | `mcp-arena[pdf]` |
| 32 | `qrcode` | `QRCodeMCPServer` | `mcp-arena[qrcode]` |
| 33 | `spreadsheet` | `SpreadsheetMCPServer` | `mcp-arena[spreadsheet]` |

Adding a new `<name>.py` to `mcp_arena/presents/` makes it appear in the loader automatically. See [Custom presets](MCP_SERVERS_GUIDE.md#4-custom-presets).

## Install

```bash
pip install mcp-arena
pip install "mcp-arena[github]"
pip install "mcp-arena[github,slack,postgres,redis]"
pip install "mcp-arena[all]"
pip install "mcp-arena[agents]" langchain-openai
```

Bundle extras:

| Bundle | Contents |
| --- | --- |
| `email` | `gmail`, `outlook` |
| `messaging` | `slack`, `whatsapp` |
| `communication` | `gmail`, `outlook`, `slack`, `whatsapp` |
| `mail` | `gmail`, `outlook` |
| `notification` | `communication` |
| `all` | Every preset extra plus `agents` |
| `complete` | `all` plus `dev` |
| `dev` | Test and lint tools only |

Python 3.12 or newer is required. See [Installation](INSTALLATION.md) for the full extras table.

## Run a server

### From Python

```python
from mcp_arena.presents.github import GithubMCPServer

server = GithubMCPServer(
    token="ghp_...",
    host="127.0.0.1",
    port=8000,
    transport="stdio",
    debug=False,
)

if __name__ == "__main__":
    server.run()
```

Run it with `python server.py` and point an MCP client at the process.

### From the CLI

```bash
mcp-arena list
mcp-arena info github
mcp-arena run --mcp-server github --token "$GITHUB_TOKEN"
mcp-arena run --mcp-server github --token "$GITHUB_TOKEN" --transport sse --host 0.0.0.0 --port 8001
```

The CLI forwards `--name value` arguments to the preset constructor.

### From an MCP client configuration

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["-m", "mcp_arena.presents.github"],
      "env": { "GITHUB_TOKEN": "ghp_..." }
    }
  }
}
```

## Credentials

Most presets accept credentials as constructor arguments or read them from environment variables. A `.env` file in the project root is loaded when `mcp_arena` is imported.

| Server | Environment variables |
| --- | --- |
| `github` | `GITHUB_TOKEN` |
| `gitlab` | `GITLAB_PRIVATE_TOKEN`, `GITLAB_OAUTH_TOKEN`, `CI_JOB_TOKEN` |
| `bitbucket` | `BITBUCKET_USERNAME`, `BITBUCKET_APP_PASSWORD` |
| `notion` | `NOTION_TOKEN` |
| `confluence` | `CONFLUENCE_USERNAME`, `CONFLUENCE_PASSWORD` |
| `jira` | `JIRA_USERNAME`, `JIRA_PASSWORD` |
| `slack` | `SLACK_BOT_TOKEN` or `SLACK_TOKEN` |
| `whatsapp` | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_NUMBER` |
| `gmail` | `GMAIL_CREDENTIALS_PATH` |
| `outlook` | Set via constructor (MSAL) |
| `smtp` | `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` |
| `postgres` | `POSTGRES_CONNECTION_STRING` |
| `mongo` | `MONGODB_CONNECTION_STRING` |
| `redis` | Constructor arguments |
| `vectordb` | Constructor arguments; `OPENAI_API_KEY` for embeddings |
| `sentry` | `SENTRY_AUTH_TOKEN`, `SENTRY_ORG` |
| `context7` | `CONTEXT7_API_KEY` (optional) |
| `aws` | `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `S3_BUCKET_NAME` |
| `cloudstorage` | `GCS_PROJECT_ID`, `GCS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS` |
| `docker` | Docker socket and configuration |
| `local_operation`, `screencapture`, `browser`, `webscraping`, `generic_api`, `image`, `video`, `audio`, `pdf`, `qrcode`, `spreadsheet` | None |

## Recipes

### Communication

```bash
pip install "mcp-arena[slack]"
```

```python
import os
from mcp_arena.presents.slack import SlackMCPServer

SlackMCPServer(token=os.environ["SLACK_BOT_TOKEN"]).run()
```

```bash
pip install "mcp-arena[whatsapp]"
```

```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer

WhatsAppMCPServer().run()
```

```bash
pip install "mcp-arena[gmail,outlook]"
```

```python
from mcp_arena.presents.gmail import GmailMCPServer

GmailMCPServer(credentials_path="./gmail_creds.json").run()
```

### Dev platforms

```bash
pip install "mcp-arena[github,gitlab,bitbucket]"
```

### Productivity

```bash
pip install "mcp-arena[notion,bitbucket]"
```

`bitbucket` provides `atlassian-python-api`, which covers Bitbucket, Jira, and Confluence.

### Data and storage

```bash
pip install "mcp-arena[postgres,mongodb,redis,vectordb]"
```

### Monitoring and documentation

```bash
pip install "mcp-arena[sentry,context7]"
```

```python
from mcp_arena.presents.context7 import Context7MCPServer

Context7MCPServer().run()
```

`Context7MCPServer` registers `resolve_library_id`, `query_docs`, and `search_docs`.

### Cloud and OS

```bash
pip install "mcp-arena[cloudstorage,docker,screencapture]"
```

### Browser, web, and media

```bash
pip install "mcp-arena[browser,webscraping,image,video,audio,pdf,qrcode,spreadsheet]"
```

## Transports

| Transport | Endpoint | Use case |
| --- | --- | --- |
| `stdio` (default) | stdin/stdout | Local MCP clients and `make_mcp_agent` |
| `sse` | `http://<host>:<port>/sse` | Browser and streaming clients |
| `streamable-http` | `http://<host>:<port>/mcp` | Networked or multi-process setups |

```python
server = GithubMCPServer(token="...", transport="stdio")
server = GithubMCPServer(token="...", transport="sse", port=8001)
server = GithubMCPServer(token="...", transport="streamable-http", port=8001)
```

## Consume a running server

1. **Any MCP client** — speak MCP over the chosen transport.
2. **LangChain agent** — pass the same server object to `make_mcp_agent`. See [LangChain Integration](LANGCHAIN_INTEGRATION.md).
3. **Plain Python callables** — use `MCPAgentWrapper`, without an MCP client.

```python
from mcp_arena.wrapper import MCPAgentWrapper

for tool in MCPAgentWrapper(server).get_tools():
    print(tool["function"]["name"])
```
