"""WhatsApp MCP server via Twilio."""
import json
import os
from typing import Any, Dict, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    from twilio.rest import Client as _TwilioClient
except ImportError:
    _TwilioClient = None


def _ensure_twilio():
    if _TwilioClient is None:
        raise ImportError("twilio is required. pip install twilio")
    return _TwilioClient


class WhatsAppMCPServer(BaseMCPServer):
    """WhatsApp messaging MCP server (Twilio)."""
    _REQUIRED_EXTRAS = {"twilio": "whatsapp"}

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        from_number: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.whatsapp_number = (
            whatsapp_number or from_number or os.getenv("TWILIO_WHATSAPP_NUMBER")
        )
        # Public alias used by some clients/tests.
        self.from_number = self.whatsapp_number

        if not (self.account_sid and self.auth_token and self.whatsapp_number):
            raise ValueError("Twilio credentials and WhatsApp number are required")

        self.client = _ensure_twilio()(self.account_sid, self.auth_token)

        super().__init__(
            name="WhatsApp MCP Server",
            description="MCP server for WhatsApp messaging via Twilio",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def send_message(to: str, body: str, media_url: Optional[str] = None) -> Dict[str, Any]:
            """Send a WhatsApp message."""
            try:
                params = {"from": self.whatsapp_number, "to": f"whatsapp:{to}", "body": body}
                if media_url:
                    params["media_url"] = [media_url]
                msg = self.client.messages.create(**params)
                return {
                    "message_sid": msg.sid,
                    "status": msg.status,
                    "to": msg.to,
                    "from": msg.from_,
                    "body": msg.body,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def send_template_message(
            to: str,
            template_name: str,
            template_variables: Dict[str, str],
            language: str = "en",
        ) -> Dict[str, Any]:
            """Send a WhatsApp template message."""
            try:
                msg = self.client.messages.create(
                    from_=self.whatsapp_number,
                    to=f"whatsapp:{to}",
                    content_sid=f"HX{template_name}",
                    content_variables=json.dumps(template_variables),
                )
                return {"message_sid": msg.sid, "status": msg.status}
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def get_message_status(message_sid: str) -> Dict[str, Any]:
            """Get the status of a WhatsApp message."""
            try:
                msg = self.client.messages(message_sid).fetch()
                return {
                    "sid": msg.sid,
                    "status": msg.status,
                    "date_sent": msg.date_sent.isoformat() if msg.date_sent else None,
                    "error_code": msg.error_code,
                    "error_message": msg.error_message,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def list_templates() -> Dict[str, Any]:
            """List placeholder templates (real API not yet wired)."""
            return {
                "templates": [
                    {"name": "welcome_message", "language": "en", "status": "approved"},
                    {"name": "order_confirmation", "language": "en", "status": "approved"},
                    {"name": "appointment_reminder", "language": "en", "status": "approved"},
                ]
            }

