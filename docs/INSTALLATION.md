# Installation

## Core (no presets)

```bash
pip install mcp-arena
```

Core includes:
- `mcp` (the MCP SDK)
- `python-dotenv`, `typing-extensions`, `psutil`, `pydantic`
- `typer`, `rich` (CLI)

It does **not** install any LLM provider or MCP-adapter package. Add presets as needed.

## Extras

`mcp_arena` ships an extra for every group of presets. Most presets only need one extra; bundle extras are also provided.

| Extra                              | What you get                                                                        |
| ---------------------------------- | ----------------------------------------------------------------------------------- |
| `mcp-arena[github]`                | GitHub preset + `PyGithub`                                                         |
| `mcp-arena[gitlab]`                | GitLab preset + `python-gitlab`                                                    |
| `mcp-arena[bitbucket]`             | Bitbucket preset + `atlassian-python-api`                                           |
| `mcp-arena[postgres]`              | PostgreSQL preset + `psycopg2-binary`                                              |
| `mcp-arena[mongodb]`               | MongoDB preset + `pymongo`                                                         |
| `mcp-arena[redis]`                 | Redis preset + `redis`                                                              |
| `mcp-arena[docker]`                | Docker preset + `docker`                                                           |
| `mcp-arena[kubernetes]`            | Kubernetes preset + `kubernetes`                                                    |
| `mcp-arena[local_operation]`       | Local OS preset + `psutil`, `pyautogui`                                             |
| `mcp-arena[browser]`               | Browser preset + `playwright`, `opencv-python`, `pillow`                            |
| `mcp-arena[image]`                 | Image preset + `pillow`, `opencv-python`                                            |
| `mcp-arena[video]`                 | Video preset + `moviepy`, `numpy`                                                  |
| `mcp-arena[audio]`                 | Audio preset + `pydub`, `librosa`, `numpy`                                          |
| `mcp-arena[pdf]`                   | PDF preset + `PyMuPDF`, `PyPDF2`, `reportlab`, `pdfplumber`                         |
| `mcp-arena[qrcode]`                | QR-code preset + `qrcode[pil]`, `Pillow`                                            |
| `mcp-arena[webscraping]`           | Web-scraping preset + `requests`, `beautifulsoup4`, `selenium`                      |
| `mcp-arena[spreadsheet]`           | Spreadsheet preset + `pandas`, `openpyxl`                                           |
| `mcp-arena[screencapture]`         | Screen-capture preset + `pyautogui`                                                 |
| `mcp-arena[cloudstorage]`          | Cloud-storage preset + `boto3`, `google-cloud-storage`                              |
| `mcp-arena[generic_api]`           | Generic-API preset + `httpx`                                                        |
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
| `mcp-arena[mail]`      | `mcp-arena[gmail,outlook]`                                       |
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
# Just the GitHub preset
pip install mcp-arena[github]

# Several at once
pip install "mcp-arena[github,slack,whatsapp]"

# Everything except browser automation
pip install "mcp-arena[all]"  # browser is included — there's no "all minus browser" extra; install the rest individually if needed

# Develop the library locally
git clone https://github.com/SatyamSingh8306/mcp_arena
cd mcp_arena
pip install -e ".[complete]"
```

## Python version

Requires Python 3.12+ (`langchain` 1.x and `chromadb` 1.x both need it).

## Verification

```bash
python -c "import mcp_arena; print(mcp_arena.__version__)"
python -c "from mcp_arena.presents import GithubMCPServer; print(GithubMCPServer.__name__)"
```
