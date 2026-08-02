# Installation

## What `pip install mcp-arena` ships today

The core package includes three general-purpose MCP server presets so you can run a real MCP server with zero extra setup:

| Preset | Class | Why it's in core |
| ------ | ----- | ----------------- |
| Local operations | `LocalOperationsMCPServer` | file / system / process tools — uses `psutil` + `pyautogui` |
| Generic API | `GenericAPIMCPServer` | make any HTTP API call — uses `httpx` |
| SMTP | `SMTPServer` | send email via any SMTP server — pure stdlib |

Plus: `BaseMCPServer`, the lazy `mcp_arena.presents` loader, `make_mcp_agent`, `ToolRegistry`, `BaseTool`, and the `mcp-arena` CLI.

Everything else is gated behind an extra. If you try to instantiate a gated preset without its extra, you get a clear `ImportError` pointing at the install command:

```
PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server but are not installed.
Install it with:    pip install "mcp-arena[pdf]"
```

## What to install

| What you want                                          | Install                                            |
| ------------------------------------------------------ | -------------------------------------------------- |
| Just the core (3 presets + base classes + CLI)         | `pip install mcp-arena`                            |
| One extra preset                                       | `pip install "mcp-arena[<extra>]"`                 |
| Several presets                                        | `pip install "mcp-arena[github,slack,postgres]"`   |
| Every preset (heavy)                                   | `pip install "mcp-arena[all]"`                     |
| The LangChain `make_mcp_agent` bridge                  | `pip install "mcp-arena[agents]"` plus your LLM provider (e.g. `langchain-openai`) |
| All presets + dev tooling                              | `pip install "mcp-arena[complete]"`                |

## Available extras

`mcp_arena` ships an extra for every preset or group. The three presets in core (`local_operation`, `generic_api`, `smtp`) keep their old extra names as no-op aliases for back-compat.

| Extra                              | What you get                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| `mcp-arena[github]`                | GitHub preset + `PyGithub`                                                         |
| `mcp-arena[gitlab]`                | GitLab preset + `python-gitlab`                                                    |
| `mcp-arena[bitbucket]`             | Bitbucket preset + `atlassian-python-api` (also covers `jira`, `confluence`)        |
| `mcp-arena[postgres]`              | PostgreSQL preset + `psycopg2-binary`                                              |
| `mcp-arena[mongodb]`               | MongoDB preset + `pymongo`                                                         |
| `mcp-arena[redis]`                 | Redis preset + `redis`                                                              |
| `mcp-arena[docker]`                | Docker preset + `docker`                                                           |
| `mcp-arena[kubernetes]`            | Kubernetes preset + `kubernetes`                                                    |
| `mcp-arena[local_operation]`       | (no-op alias — preset is in core)                                                  |
| `mcp-arena[browser]`               | Browser preset + `playwright`, `opencv-python`, `pillow`                            |
| `mcp-arena[image]`                 | Image preset + `pillow`, `opencv-python`                                            |
| `mcp-arena[video]`                 | Video preset + `moviepy`, `numpy`                                                  |
| `mcp-arena[audio]`                 | Audio preset + `pydub`, `librosa`, `numpy`                                          |
| `mcp-arena[pdf]`                   | PDF preset + `PyMuPDF`, `PyPDF2`, `reportlab`, `pdfplumber`                         |
| `mcp-arena[qrcode]`                | QR-code preset + `qrcode[pil]`, `Pillow`                                            |
| `mcp-arena[webscraping]`           | Web-scraping preset + `requests`, `beautifulsoup4`, `selenium`                      |
| `mcp-arena[spreadsheet]`           | Spreadsheet preset + `pandas`, `openpyxl`                                           |
| `mcp-arena[screencapture]`         | Screen-capture preset + `pyautogui` (already in core; alias is a no-op)              |
| `mcp-arena[cloudstorage]`          | Cloud-storage preset + `boto3`, `google-cloud-storage`                              |
| `mcp-arena[generic_api]`           | (no-op alias — preset is in core)                                                  |
| `mcp-arena[vectordb]`              | Vector-DB preset + `chromadb`, `sentence-transformers`                              |

### Communication extras

| Extra                  | What you get                                                    |
| ---------------------- | --------------------------------------------------------------- |
| `mcp-arena[gmail]`     | `google-auth*`, `google-api-python-client`                      |
| `mcp-arena[outlook]`   | `msal`                                                           |
| `mcp-arena[slack]`     | `slack-sdk`                                                      |
| `mcp-arena[whatsapp]`  | `twilio`                                                         |
| `mcp-arena[email]`     | `mcp-arena[gmail,outlook]`                                       |
| `mcp-arena[messaging]` | `mcp-arena[slack,whatsapp]`                                      |
| `mcp-arena[communication]` | `mcp-arena[gmail,outlook,slack,whatsapp]`                   |
| `mcp-arena[mail]`      | `mcp-arena[gmail,outlook]` (used by `MailMCPServer` / `SMTPMCPServer`) |
| `mcp-arena[notification]` | `mcp-arena[communication]`                                    |

### Agents & AI

| Extra                  | What you get                                                    |
| ---------------------- | --------------------------------------------------------------- |
| `mcp-arena[agents]`    | `langchain>=1.0,<2.0`, `langchain-mcp-adapters>=0.1,<1.0`      |

> Install your LLM provider separately: `langchain-openai`, `langchain-anthropic`, `langchain-groq`, etc.

### Bundles

| Extra                  | What you get                                                    |
| ---------------------- | --------------------------------------------------------------- |
| `mcp-arena[all]`       | every preset + the agents extra                                 |
| `mcp-arena[complete]`  | `mcp-arena[all,dev]` (adds pytest, black, ruff, mypy, pre-commit) |
| `mcp-arena[dev]`       | pytest, pytest-asyncio, black, isort, ruff, mypy, pre-commit    |

## Examples

```bash
# Core (no extras) — three general-purpose presets work out of the box
pip install mcp-arena

# Add GitHub
pip install "mcp-arena[github]"

# Several presets at once
pip install "mcp-arena[github,slack,whatsapp]"

# Everything
pip install "mcp-arena[all]"

# Develop the library locally
git clone https://github.com/SatyamSingh8306/mcp_arena
cd mcp_arena
pip install -e ".[complete]"
```

## Python version

Requires Python 3.12+ (`langchain` 1.x and `chromadb` 1.x both need it).

## Verification

```bash
# 1. Core is installed
python -c "import mcp_arena; print(mcp_arena.__version__)"

# 2. The three core presets work without any extra
python -c "
from mcp_arena.presents.local_operation import LocalOperationsMCPServer
from mcp_arena.presents.generic_api import GenericAPIMCPServer
from mcp_arena.presents.smtp import SMTPServer
print('LocalOperationsMCPServer:', len(LocalOperationsMCPServer().get_registered_tools()), 'tools')
print('GenericAPIMCPServer:', len(GenericAPIMCPServer().get_registered_tools()), 'tools')
print('SMTPServer:', len(SMTPServer(smtp_host='localhost').get_registered_tools()), 'tools')
"

# 3. A gated preset without the extra gives a clear error
python -c "
from mcp_arena.presents.pdf import PDFMCPServer
PDFMCPServer()
"
# expected:
#   ImportError: PyPDF2, fitz, pdfplumber and reportlab are required for this MCP server
#   but are not installed.
#   Install it with:    pip install "mcp-arena[pdf]"

# 4. Install the extra and retry
pip install "mcp-arena[pdf]"
python -c "from mcp_arena.presents.pdf import PDFMCPServer; print(len(PDFMCPServer().get_registered_tools()), 'tools')"
```

## "What package do I need for `<preset>`?" 

If you forget, ask the preset — every preset declares `_REQUIRED_EXTRAS`:

```python
from mcp_arena.presents.whatsapp import WhatsAppMCPServer
print(WhatsAppMCPServer._REQUIRED_EXTRAS)
# -> {'twilio': 'whatsapp'}
```
