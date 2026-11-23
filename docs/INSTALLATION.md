# Installation

## Requirements

Python 3.12 or newer.

```bash
pip install mcp-arena
```

Three general-purpose presets ship in the core package, so no extra is needed to run a real MCP server:

| Preset | Class | Purpose |
| --- | --- | --- |
| Local operations | `LocalOperationsMCPServer` | File, system, and process tools (`psutil`, `pyautogui`) |
| Generic API | `GenericAPIMCPServer` | Arbitrary HTTP requests (`httpx`) |
| SMTP | `SMTPServer` | Outbound email via any SMTP server (stdlib) |

Also included: `BaseMCPServer`, the lazy `mcp_arena.presents` loader, `make_mcp_agent`, `ToolRegistry`, `BaseTool`, and the `mcp-arena` CLI.

All other presets are gated behind an extra. Constructing a gated preset without its extra raises an `ImportError` with the install command:

```text
PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

## What to install

| Goal | Command |
| --- | --- |
| Core only | `pip install mcp-arena` |
| One preset | `pip install "mcp-arena[github]"` |
| Several presets | `pip install "mcp-arena[github,slack,postgres]"` |
| Every preset | `pip install "mcp-arena[all]"` |
| LangChain bridge | `pip install "mcp-arena[agents]" langchain-openai` |
| All presets and dev tooling | `pip install "mcp-arena[complete]"` |

## Available extras

Each preset has an extra. `local_operation`, `generic_api`, and `screencapture` keep their names as no-op aliases because their presets are already in core.

| Extra | What it installs |
| --- | --- |
| `github` | `PyGithub` |
| `gitlab` | `python-gitlab` |
| `bitbucket` | `atlassian-python-api` (also covers `jira` and `confluence`) |
| `postgres` | `psycopg2-binary` |
| `mongodb` | `pymongo` |
| `redis` | `redis` |
| `docker` | `docker` |
| `kubernetes` | `kubernetes` |
| `local_operation` | No-op alias (preset is in core) |
| `browser` | `playwright`, `opencv-python`, `pillow` |
| `image` | `pillow`, `opencv-python` |
| `video` | `moviepy`, `numpy` |
| `audio` | `pydub`, `librosa`, `numpy` |
| `pdf` | `PyMuPDF`, `PyPDF2`, `reportlab`, `pdfplumber` |
| `qrcode` | `qrcode[pil]`, `Pillow` |
| `webscraping` | `requests`, `beautifulsoup4`, `selenium` |
| `spreadsheet` | `pandas`, `openpyxl` |
| `screencapture` | No-op alias (`pyautogui` is in core) |
| `cloudstorage` | `boto3`, `google-cloud-storage` |
| `sentry` | `httpx` |
| `context7` | `httpx` |
| `vectordb` | `chromadb`, `sentence-transformers`, `langchain-pinecone` |
| `generic_api` | No-op alias (preset is in core) |

### Communication extras

| Extra | What it installs |
| --- | --- |
| `gmail` | `google-auth`, `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client` |
| `outlook` | `msal` |
| `slack` | `slack-sdk` |
| `whatsapp` | `twilio` |
| `email` | `gmail`, `outlook` |
| `mail` | `gmail`, `outlook` |
| `messaging` | `slack`, `whatsapp` |
| `communication` | `gmail`, `outlook`, `slack`, `whatsapp` |
| `notification` | `communication` |

### Agents and AI

| Extra | What it installs |
| --- | --- |
| `agents` | `langchain>=1.0,<2.0`, `langchain-mcp-adapters>=0.1,<1.0` |

Install an LLM provider separately, for example `langchain-openai`, `langchain-anthropic`, or `langchain-groq`.

### Bundles

| Extra | What it installs |
| --- | --- |
| `all` | Every preset extra plus `agents` |
| `complete` | `all` plus `dev` |
| `dev` | `pytest`, `pytest-asyncio`, `black`, `isort`, `ruff`, `mypy`, `pre-commit` |

## Examples

```bash
pip install mcp-arena
pip install "mcp-arena[github]"
pip install "mcp-arena[github,slack,whatsapp]"
pip install "mcp-arena[all]"

git clone https://github.com/SatyamSingh8306/mcp_arena
cd mcp_arena
pip install -e ".[complete]"
```

## Verify the installation

Check the version and that the core presets import:

```bash
python -c "import mcp_arena; print(mcp_arena.__version__)"
python -c "
from mcp_arena.presents.local_operation import LocalOperationsMCPServer
from mcp_arena.presents.generic_api import GenericAPIMCPServer
from mcp_arena.presents.smtp import SMTPServer
print(len(LocalOperationsMCPServer().get_registered_tools()), 'tools')
print(len(GenericAPIMCPServer().get_registered_tools()), 'tools')
print(len(SMTPServer(smtp_host='localhost').get_registered_tools()), 'tools')
"
```

A gated preset without its extra fails with an actionable message:

```bash
python -c "from mcp_arena.presents.pdf import PDFMCPServer; PDFMCPServer()"
```

```text
ImportError: PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

After installing the extra, the same command succeeds.

## Find the extra for a preset

Every preset declares `_REQUIRED_EXTRAS`:

```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer

print(WhatsAppMCPServer._REQUIRED_EXTRAS)
```
