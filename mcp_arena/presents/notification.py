"""
Notification MCP Server
A comprehensive notification server for sending messages across multiple platforms
including email, SMS, Slack, and webhooks.
"""
from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from mcp_arena.mcp.server import BaseMCPServer


class NotificationType(str, str):
    """Notification types."""
    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class NotificationResult:
    """Notification operation result."""
    type: str
    success: bool
    recipient: str
    message: str
    timestamp: str
    error: Optional[str] = None


class NotificationMCPServer(BaseMCPServer):
    """Notification MCP Server for multi-platform messaging."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: int = 587,
        smtp_username: Optional[str] = None,
        smtp_password: Optional[str] = None,
        twilio_sid: Optional[str] = None,
        twilio_token: Optional[str] = None,
        twilio_number: Optional[str] = None,
        slack_token: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Notification MCP Server."""
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username or os.getenv("SMTP_USERNAME")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD")
        self.twilio_sid = twilio_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_token = twilio_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_number = twilio_number or os.getenv("TWILIO_PHONE_NUMBER")
        self.slack_token = slack_token or os.getenv("SLACK_BOT_TOKEN")

        super().__init__(
            name="Notification MCP Server",
            description="MCP server for multi-platform notifications (email, SMS, Slack, webhooks)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _register_tools(self) -> None:
        """Register all notification tools."""
        self._register_email_tools()
        self._register_slack_tools()
        self._register_webhook_tools()

    def _register_email_tools(self):
        """Register email notification tools."""

        @self.mcp_server.tool()
        def send_email(
            to_address: str,
            subject: str,
            body: str,
            from_address: Optional[str] = None,
            is_html: bool = False
        ) -> Dict[str, Any]:
            """Send an email notification."""
            try:
                if not self.smtp_host:
                    return {"error": "SMTP server not configured"}

                from_addr = from_address or self.smtp_username

                msg = MIMEMultipart()
                msg['From'] = from_addr
                msg['To'] = to_address
                msg['Subject'] = subject

                if is_html:
                    msg.attach(MIMEText(body, 'html'))
                else:
                    msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.send_message(msg)

                return {
                    "success": True,
                    "type": "email",
                    "to": to_address,
                    "subject": subject
                }

            except Exception as e:
                return {"error": str(e), "type": "email"}

    def _register_slack_tools(self):
        """Register Slack notification tools."""

        @self.mcp_server.tool()
        def send_slack_message(
            channel: str,
            message: str,
            webhook_url: Optional[str] = None
        ) -> Dict[str, Any]:
            """Send a Slack message."""
            try:
                import requests

                # Use webhook if provided, otherwise try bot token
                if webhook_url:
                    response = requests.post(
                        webhook_url,
                        json={"text": message, "channel": channel}
                    )
                    return {
                        "success": response.status_code == 200,
                        "type": "slack",
                        "channel": channel
                    }

                if not self.slack_token:
                    return {"error": "Slack token not configured"}

                from slack_sdk import WebClient
                client = WebClient(token=self.slack_token)
                result = client.chat_postMessage(channel=channel, text=message)

                return {
                    "success": result['ok'],
                    "type": "slack",
                    "channel": channel,
                    "ts": result['ts']
                }

            except Exception as e:
                return {"error": str(e), "type": "slack"}

    def _register_webhook_tools(self):
        """Register webhook notification tools."""

        @self.mcp_server.tool()
        def send_webhook(
            url: str,
            data: Dict[str, Any],
            method: str = "POST",
            headers: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Send data to a webhook URL."""
            try:
                import requests

                response = requests.request(
                    method=method,
                    url=url,
                    json=data,
                    headers=headers or {"Content-Type": "application/json"}
                )

                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response": response.text[:1000] if response.text else None
                }

            except Exception as e:
                return {"error": str(e), "type": "webhook"}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Notification MCP Server")
    parser.add_argument("--smtp-host", type=str, default=None)
    parser.add_argument("--smtp-port", type=int, default=587)
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    server = NotificationMCPServer(
        smtp_host=args.smtp_host,
        smtp_port=args.smtp_port,
        transport=args.transport,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    print("Starting Notification MCP Server")
    server.run()


if __name__ == "__main__":
    main()
