# Environment Variables

Complete reference for every environment variable supported by **mcp_arena** preset servers.

---

## Table of Contents

- [Quick Reference](#quick-reference)
- [GitHub](#github)
- [Slack](#slack)
- [Notion](#notion)
- [PostgreSQL](#postgresql)
- [MongoDB](#mongodb)
- [GitLab](#gitlab)
- [Bitbucket](#bitbucket)
- [Confluence](#confluence)
- [Jira](#jira)
- [Gmail](#gmail)
- [WhatsApp](#whatsapp)
- [VectorDB](#vectordb)
- [Outlook](#outlook)
- [Redis](#redis)
- [AWS S3](#aws-s3)
- [Docker](#docker)
- [SMTP](#smtp)
- [Generic API](#generic-api)
- [Local Operations](#local-operations)
- [Using a .env File](#using-a-env-file)
- [Security Best Practices](#security-best-practices)

---

## Quick Reference

All 21 configuration environment variables at a glance:

| Variable | Preset | Required | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | GitHub | Yes | GitHub Personal Access Token |
| `SLACK_TOKEN` | Slack | Yes | Slack Bot OAuth Token |
| `NOTION_TOKEN` | Notion | Yes | Notion Internal Integration Token |
| `POSTGRES_CONNECTION_STRING` | PostgreSQL | Yes | PostgreSQL connection URI |
| `MONGODB_CONNECTION_STRING` | MongoDB | Yes | MongoDB connection URI |
| `GITLAB_PRIVATE_TOKEN` | GitLab | Conditional | GitLab Personal Access Token |
| `GITLAB_OAUTH_TOKEN` | GitLab | Conditional | GitLab OAuth Token |
| `CI_JOB_TOKEN` | GitLab | Conditional | GitLab CI/CD Job Token |
| `BITBUCKET_USERNAME` | Bitbucket | Conditional | Bitbucket username |
| `BITBUCKET_APP_PASSWORD` | Bitbucket | Conditional | Bitbucket App Password |
| `BITBUCKET_OAUTH_KEY` | Bitbucket | No | Bitbucket OAuth consumer key |
| `BITBUCKET_OAUTH_SECRET` | Bitbucket | No | Bitbucket OAuth consumer secret |
| `CONFLUENCE_USERNAME` | Confluence | No | Confluence username (CLI only) |
| `CONFLUENCE_PASSWORD` | Confluence | No | Confluence API token (CLI only) |
| `JIRA_USERNAME` | Jira | No | Jira username (CLI only) |
| `JIRA_PASSWORD` | Jira | No | Jira API token (CLI only) |
| `GMAIL_CREDENTIALS_PATH` | Gmail | Conditional | Path to Google OAuth2 JSON |
| `TWILIO_ACCOUNT_SID` | WhatsApp | Yes | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | WhatsApp | Yes | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | WhatsApp | Yes | Twilio WhatsApp sender number |
| `OPENAI_API_KEY` | VectorDB | Conditional | OpenAI API key for embeddings |

**Required** = server raises `ValueError` on startup if missing.  
**Conditional** = required only when a specific auth method or provider is chosen.

---

## GitHub

**Server class:** `GithubMCPServer`  
**Import:** `from mcp_arena.presents.github import GithubMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `GITHUB_TOKEN` | `token` | **Yes** | GitHub Personal Access Token |

The server will raise a `ValueError` if `token` is not provided as a constructor argument **and** the environment variable is not set.

**How to generate:** Go to [GitHub Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens) and create a token with the scopes you need (minimum: `repo`, `read:org`, `read:user`).

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```python
# Explicit — no env var needed
server = GithubMCPServer(token="ghp_...")

# Env var fallback
server = GithubMCPServer()  # reads GITHUB_TOKEN
```

---

## Slack

**Server class:** `SlackMCPServer`  
**Import:** `from mcp_arena.presents.slack import SlackMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `SLACK_TOKEN` | `token` | **Yes** | Slack Bot OAuth Token |

Raises `ValueError` if missing.

**How to generate:** Create a Slack app at [api.slack.com/apps](https://api.slack.com/apps), install it to your workspace, and copy the **Bot User OAuth Token** (`xoxb-...`). Required scopes depend on the tools you use — at minimum: `channels:read`, `chat:write`, `users:read`.

```bash
export SLACK_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Notion

**Server class:** `NotionMCPServer`  
**Import:** `from mcp_arena.presents.notion import NotionMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `NOTION_TOKEN` | `token` | **Yes** | Notion Internal Integration Token |

Raises `ValueError` if missing.

**How to generate:** Create an integration at [notion.so/my-integrations](https://www.notion.so/my-integrations), then share the target pages/databases with the integration.

```bash
export NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## PostgreSQL

**Server class:** `PostgresMCPServer`  
**Import:** `from mcp_arena.presents.postgres import PostgresMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `POSTGRES_CONNECTION_STRING` | `connection_string` | **Yes** | PostgreSQL connection URI |

Raises `ValueError` if missing.

**Format:**

```
postgresql://username:password@hostname:5432/database_name
```

**Examples:**

```bash
# Local database
export POSTGRES_CONNECTION_STRING=postgresql://postgres:mysecretpw@localhost:5432/mydb

# Remote with SSL
export POSTGRES_CONNECTION_STRING=postgresql://user:pass@db.example.com:5432/prod?sslmode=require
```

---

## MongoDB

**Server class:** `MongoDBMCPServer`  
**Import:** `from mcp_arena.presents.mongo import MongoDBMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `MONGODB_CONNECTION_STRING` | `connection_string` | **Yes** | MongoDB connection URI |

Raises `ValueError` if missing.

**Format:**

```bash
# Local
export MONGODB_CONNECTION_STRING=mongodb://username:password@localhost:27017/database

# MongoDB Atlas
export MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/database
```

> **Note:** For Atlas (`mongodb+srv://`), install `dnspython`: `pip install dnspython`.

---

## GitLab

**Server class:** `GitLabMCPServer`  
**Import:** `from mcp_arena.presents.gitlab import GitLabMCPServer`

GitLab supports multiple authentication methods with a fallback chain:

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `GITLAB_PRIVATE_TOKEN` | `private_token` | Conditional | Personal Access Token |
| `GITLAB_OAUTH_TOKEN` | `oauth_token` | Conditional | OAuth2 Token |
| `CI_JOB_TOKEN` | `job_token` | Conditional | GitLab CI/CD Job Token (auto-set in CI) |

**Auth priority:** `private_token` → `oauth_token` → `GITLAB_PRIVATE_TOKEN` → `GITLAB_OAUTH_TOKEN` → `CI_JOB_TOKEN`

At least one must be provided. If none are available, the server initializes with `connected=False` and tools will return error responses.

```bash
# Personal access token (most common)
export GITLAB_PRIVATE_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# For GitLab CI/CD pipelines, CI_JOB_TOKEN is set automatically
```

> **Self-hosted GitLab:** Pass `url="https://gitlab.your-company.com"` to the constructor.

---

## Bitbucket

**Server class:** `BitbucketMCPServer`  
**Import:** `from mcp_arena.presents.bitbucket import BitbucketMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `BITBUCKET_USERNAME` | `username` | Conditional | Bitbucket username |
| `BITBUCKET_APP_PASSWORD` | `app_password` | Conditional | Bitbucket App Password |
| `BITBUCKET_OAUTH_KEY` | `oauth_key` | No | OAuth consumer key (CLI only) |
| `BITBUCKET_OAUTH_SECRET` | `oauth_secret` | No | OAuth consumer secret (CLI only) |

**Auth:** Username + App Password is the primary method. The server raises `ValueError` if no valid authentication can be established.

**How to generate an App Password:** Go to [Bitbucket Settings → App passwords](https://bitbucket.org/account/settings/app-passwords/) and create one with the permissions you need.

```bash
export BITBUCKET_USERNAME=your-username
export BITBUCKET_APP_PASSWORD=xxxxxxxxxxxxxxxxxxxx
```

---

## Confluence

**Server class:** `ConfluenceMCPServer`  
**Import:** `from mcp_arena.presents.confluence import ConfluenceMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `CONFLUENCE_USERNAME` | `username` | No | Confluence username (CLI fallback only) |
| `CONFLUENCE_PASSWORD` | `password` | No | Confluence API token (CLI fallback only) |

> **Note:** These environment variables are only used as defaults when running Confluence via the CLI (`python -m mcp_arena.presents.confluence`). When using the Python API directly, pass `username` and `password` as constructor arguments.

```bash
export CONFLUENCE_USERNAME=your@email.com
export CONFLUENCE_PASSWORD=your_api_token
```

**How to generate:** For Atlassian Cloud, create an API token at [id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens).

---

## Jira

**Server class:** `JiraMCPServer`  
**Import:** `from mcp_arena.presents.jira import JiraMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `JIRA_USERNAME` | `username` | No | Jira username/email (CLI fallback only) |
| `JIRA_PASSWORD` | `password` | No | Jira API token (CLI fallback only) |

> **Note:** Same pattern as Confluence — env vars are only used as CLI defaults, not in the constructor.

```bash
export JIRA_USERNAME=your@email.com
export JIRA_PASSWORD=your_api_token
```

---

## Gmail

**Server class:** `GmailMCPServer`  
**Import:** `from mcp_arena.presents.mail import GmailMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `GMAIL_CREDENTIALS_PATH` | `credentials_path` | Conditional | Path to Google OAuth2 client credentials JSON |

Required if no existing `token.json` file is present. The server raises `ValueError` if it cannot authenticate.

**Setup steps:**

1. Create a project in [Google Cloud Console](https://console.cloud.google.com/).
2. Enable the **Gmail API**.
3. Create **OAuth 2.0 credentials** (Desktop application type).
4. Download the JSON file.
5. Set the env var to the file path:

```bash
export GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
```

On first run, a browser window opens for OAuth consent. After authorization, a `token.json` is saved locally so subsequent runs don't need the browser.

---

## WhatsApp

**Server class:** `WhatsAppMCPServer`  
**Import:** `from mcp_arena.presents.whatsapp import WhatsAppMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `TWILIO_ACCOUNT_SID` | `account_sid` | **Yes** | Twilio Account SID |
| `TWILIO_AUTH_TOKEN` | `auth_token` | **Yes** | Twilio Auth Token |
| `TWILIO_WHATSAPP_NUMBER` | `whatsapp_number` | **Yes** | Twilio WhatsApp-enabled sender number |

All three are required. The server raises `ValueError` if any are missing.

**How to set up:**

1. Create an account at [twilio.com](https://www.twilio.com/).
2. Get your Account SID and Auth Token from the Twilio Console dashboard.
3. Enable WhatsApp in the Twilio Sandbox (for testing) or request a WhatsApp Business number.

```bash
export TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
export TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

> **Number format:** Include the `whatsapp:` prefix and full E.164 number.

---

## VectorDB

**Server class:** `VectorDBMCPServer`  
**Import:** `from mcp_arena.presents.vectordb import VectorDBMCPServer`

| Variable | Constructor param | Required | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | `openai_key` | Conditional | OpenAI API key for embeddings |

Required **only** when using `embedding_provider="openai"`. Not needed for `embedding_provider="huggingface"` (the default uses local models).

```bash
# Only needed for OpenAI embeddings
export OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

```python
# No env var needed — uses free local HuggingFace embeddings
server = VectorDBMCPServer(embedding_provider="huggingface", store_provider="chroma")

# Requires OPENAI_API_KEY
server = VectorDBMCPServer(embedding_provider="openai")
```

---

## Outlook

**Server class:** `OutlookMCPServer`  
**Import:** `from mcp_arena.presents.outlook import OutlookMCPServer`

No environment variables. Credentials (`client_id`, `client_secret`, `tenant_id`) must be passed as constructor arguments.

```python
server = OutlookMCPServer(
    client_id="your-azure-app-client-id",
    client_secret="your-azure-app-client-secret",
    tenant_id="your-azure-tenant-id"  # default: "common"
)
```

---

## Redis

**Server class:** `RedisMCPServer`  
**Import:** `from mcp_arena.presents.redis import RedisMCPServer`

No environment variables. Connection parameters are passed as constructor arguments.

```python
server = RedisMCPServer(
    host="localhost",  # default
    port=6379,         # default
    db=0,              # default
    password=None      # optional
)
```

---

## AWS S3

**Server class:** `S3MCPServer`  
**Import:** `from mcp_arena.presents.aws import S3MCPServer`

No environment variables are read by the S3 preset server itself. However, the underlying `boto3` AWS SDK reads standard AWS variables automatically:

| Variable | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS access key (used by boto3) |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key (used by boto3) |
| `AWS_DEFAULT_REGION` | Default AWS region (used by boto3) |
| `AWS_SESSION_TOKEN` | Temporary session token (used by boto3) |

These are **standard AWS SDK variables**, not mcp_arena-specific. You can also pass credentials directly:

```python
server = S3MCPServer(
    aws_access_key_id="AKIA...",
    aws_secret_access_key="...",
    region_name="us-east-1"
)
```

---

## Docker

**Server class:** `DockerMCPServer`  
**Import:** `from mcp_arena.presents.docker import DockerMCPServer`

No environment variables. The Docker SDK connects automatically via the local Docker socket.

```python
server = DockerMCPServer()  # connects to local Docker daemon
```

---

## SMTP

**Server class:** `SMTPServer`  
**Import:** `from mcp_arena.presents.smtp import SMTPServer`

No environment variables. All parameters are passed as constructor arguments.

```python
server = SMTPServer(
    smtp_host="smtp.gmail.com",
    smtp_port=587,
    username="your@gmail.com",
    password="your_app_password",
    use_tls=True
)
```

---

## Generic API

**Server class:** `GenericAPIMCPServer`  
**Import:** `from mcp_arena.presents.generic_api import GenericAPIMCPServer`

No environment variables. API configuration is passed as constructor arguments.

```python
server = GenericAPIMCPServer(
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer your-token"}
)
```

---

## Local Operations

**Server class:** `LocalOperationsMCPServer`  
**Import:** `from mcp_arena.presents.local_operation import LocalOperationsMCPServer`

No configuration environment variables. The server reads the system environment only through its `get_environment()` tool, which exposes (or redacts) variables at runtime for agent use.

```python
server = LocalOperationsMCPServer()
```

---

## Using a .env File

mcp_arena loads `.env` files automatically via `python-dotenv`. Create a `.env` file in your project root:

```env
# GitHub
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Slack
SLACK_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxx-xxxxxxxxxxxxxxxxxxxxxxxx

# Notion
NOTION_TOKEN=ntn_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Databases
POSTGRES_CONNECTION_STRING=postgresql://user:pass@localhost:5432/mydb
MONGODB_CONNECTION_STRING=mongodb://user:pass@localhost:27017/mydb

# GitLab
GITLAB_PRIVATE_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx

# Bitbucket
BITBUCKET_USERNAME=your-username
BITBUCKET_APP_PASSWORD=xxxxxxxxxxxxxxxxxxxx

# Atlassian
CONFLUENCE_USERNAME=your@email.com
CONFLUENCE_PASSWORD=your_api_token
JIRA_USERNAME=your@email.com
JIRA_PASSWORD=your_api_token

# Google
GMAIL_CREDENTIALS_PATH=/path/to/credentials.json

# WhatsApp / Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Embeddings (only for OpenAI)
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> **Important:** Add `.env` to your `.gitignore` to avoid committing secrets.

---

## Security Best Practices

1. **Never commit tokens to version control.** Use `.env` files or a secrets manager.

2. **Use the minimum required scopes.** For example, if you only need to read GitHub repos, generate a token with `repo:read` only.

3. **Rotate tokens regularly.** Especially if they appear in logs or error messages.

4. **Use separate tokens per environment.** Don't reuse production tokens in development.

5. **Prefer constructor arguments in production.** Pull secrets from a vault (e.g., AWS Secrets Manager, HashiCorp Vault) and pass them directly instead of relying on env vars.

6. **Restrict file permissions on `.env` files:**
   ```bash
   chmod 600 .env   # Linux/macOS — owner read/write only
   ```

7. **Audit token permissions.** Periodically review which scopes and services each token can access.
