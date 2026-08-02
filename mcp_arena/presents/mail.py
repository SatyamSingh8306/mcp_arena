"""Gmail MCP server: list, get, send, draft, search."""
import base64
import os
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

try:
    from google.oauth2.credentials import Credentials as _Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow as _Flow
    from google.auth.transport.requests import Request as _Request
    from googleapiclient.discovery import build as _gmail_build
except ImportError:
    _Credentials = _Flow = _Request = _gmail_build = None


def _ensure_gmail():
    if _Credentials is None:
        raise ImportError(
            "google-api-python-client + google-auth-oauthlib are required. "
            "pip install google-api-python-client google-auth-oauthlib"
        )
    return _Credentials, _Flow, _Request, _gmail_build


class GmailMCPServer(BaseMCPServer):
    """Gmail MCP server."""
    _REQUIRED_EXTRAS = {"googleapiclient": "mail", "msal": "mail"}

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: str = "token.json",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        Credentials, Flow, Request, gmail_build = _ensure_gmail()

        self.credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH")
        self.token_path = token_path
        # Defer the OAuth flow unless we can actually run it. Tests construct
        # the server with stub paths that don't exist on disk and don't want
        # an interactive `run_local_server` call.
        creds = None
        if token_path and os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception:
                creds = None
        if not creds or not getattr(creds, "valid", False):
            if creds and getattr(creds, "expired", False) and getattr(creds, "refresh_token", None):
                try:
                    creds.refresh(Request())
                except Exception:
                    creds = None
            else:
                # No valid cached creds. Only kick off the OAuth flow when we
                # actually have a credentials file on disk; otherwise leave
                # `service` as None and let tools fail at call-time.
                if self.credentials_path and os.path.exists(self.credentials_path):
                    creds = Flow.from_client_secrets_file(
                        self.credentials_path, SCOPES
                    ).run_local_server(port=0)
                    try:
                        with open(token_path, "w") as token:
                            token.write(creds.to_json())
                    except Exception:
                        pass

        if creds is not None:
            self.service = gmail_build("gmail", "v1", credentials=creds)
        else:
            self.service = None

        super().__init__(
            name="Gmail MCP Server",
            description="MCP server for Gmail operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def list_messages(
            max_results: int = 10,
            label_ids: Optional[List[str]] = None,
            query: str = "",
        ) -> Dict[str, Any]:
            """List email messages from Gmail."""
            results = self.service.users().messages().list(
                userId="me", maxResults=max_results, labelIds=label_ids, q=query,
            ).execute()
            return {"messages": results.get("messages", [])}

        @self.mcp_server.tool()
        def get_message(message_id: str) -> Dict[str, Any]:
            """Get a specific email message."""
            message = self.service.users().messages().get(
                userId="me", id=message_id, format="full",
            ).execute()
            return {"message": message}

        @self.mcp_server.tool()
        def send_email(
            to: str,
            subject: str,
            body: str,
            cc: Optional[str] = None,
            bcc: Optional[str] = None,
            attachments: Optional[List[Dict[str, Any]]] = None,
        ) -> Dict[str, Any]:
            """Send an email via Gmail."""
            message = MIMEMultipart()
            message["to"] = to
            message["subject"] = subject
            if cc:
                message["cc"] = cc
            if bcc:
                message["bcc"] = bcc
            message.attach(MIMEText(body, "plain"))
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(base64.b64decode(attachment["data"]))
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename={attachment["filename"]}',
                    )
                    message.attach(part)
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            response = self.service.users().messages().send(
                userId="me", body={"raw": raw},
            ).execute()
            return {"message_id": response["id"]}

        @self.mcp_server.tool()
        def create_draft(to: str, subject: str, body: str) -> Dict[str, Any]:
            """Create a draft email."""
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            response = self.service.users().drafts().create(
                userId="me", body={"message": {"raw": raw}},
            ).execute()
            return {"draft_id": response["id"]}

