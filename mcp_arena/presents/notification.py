"""Multi-channel notification MCP server: email, Slack, webhook."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import requests as _requests
except ImportError:
    _requests = None

try:
    from slack_sdk import WebClient as _SlackWebClient
except ImportError:
    _SlackWebClient = None


def _ensure_requests():
    if _requests is None:
        raise ImportError("requests is required. pip install requests")
    return _requests


def _ensure_slack():
    if _SlackWebClient is None:
        raise ImportError("slack-sdk is required. pip install slack-sdk")
    return _SlackWebClient


class NotificationMCPServer(BaseMCPServer):
    """Notification MCP server (email, Slack, webhook)."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        slack_token: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.slack_token = slack_token or os.getenv("SLACK_BOT_TOKEN")

        super().__init__(
            name="Notification MCP Server",
            description="MCP server for multi-platform notifications (email, Slack, webhook)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        self._register_email_tools()
        self._register_slack_tools()
        self._register_webhook_tools()

    def _register_email_tools(self):
        @self.mcp_server.tool()
        def send_email(
            to_address: str,
            subject: str,
            body: str,
            from_address: Optional[str] = None,
            is_html: bool = False,
        ) -> Dict[str, Any]:
            """Send an email notification."""
            try:
                if not self.smtp_host:
                    return {"error": "SMTP server not configured"}

                msg = MIMEMultipart()
                msg["From"] = from_address or self.smtp_username
                msg["To"] = to_address
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "html" if is_html else "plain"))

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

                return {"success": True, "type": "email", "to": to_address, "subject": subject}
            except Exception as exc:
                return {"error": str(exc), "type": "email"}

    def _register_slack_tools(self):
        @self.mcp_server.tool()
        def send_slack_message(
            channel: str,
            message: str,
            webhook_url: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Send a Slack message via webhook or bot token."""
            try:
                requests = _ensure_requests()
                if webhook_url:
                    response = requests.post(
                        webhook_url,
                        json={"text": message, "channel": channel},
                    )
                    return {
                        "success": response.status_code == 200,
                        "type": "slack",
                        "channel": channel,
                    }

                if not self.slack_token:
                    return {"error": "Slack token not configured"}

                client = _ensure_slack()(token=self.slack_token)
                result = client.chat_postMessage(channel=channel, text=message)
                return {
                    "success": result["ok"],
                    "type": "slack",
                    "channel": channel,
                    "ts": result["ts"],
                }
            except Exception as exc:
                return {"error": str(exc), "type": "slack"}

    def _register_webhook_tools(self):
        @self.mcp_server.tool()
        def send_webhook(
            url: str,
            data: Dict[str, Any],
            method: str = "POST",
            headers: Optional[Dict[str, str]] = None,
        ) -> Dict[str, Any]:
            """Send data to a webhook URL."""
            try:
                requests = _ensure_requests()
                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers or {"Content-Type": "application/json"},
                )
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response": response.text[:1000] if response.text else None,
                }
            except Exception as exc:
                return {"error": str(exc), "type": "webhook"}
