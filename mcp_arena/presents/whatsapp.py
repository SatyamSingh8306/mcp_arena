from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import os
import json
from twilio.rest import Client
from mcp_arena.mcp.server import BaseMCPServer

class WhatsAppMessage:
    sid: str
    from_number: str
    to_number: str
    body: str
    status: str
    date_sent: datetime
    media_url: Optional[str]

class WhatsAppMCPServer(BaseMCPServer):
    """WhatsApp MCP Server using Twilio API."""
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize WhatsApp MCP Server.
        
        Args:
            account_sid: Twilio account SID
            auth_token: Twilio auth token
            whatsapp_number: WhatsApp business number (format: whatsapp:+14155238886)
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.account_sid = account_sid or os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = auth_token or os.getenv('TWILIO_AUTH_TOKEN')
        self.whatsapp_number = whatsapp_number or os.getenv('TWILIO_WHATSAPP_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.whatsapp_number]):
            raise ValueError("Twilio credentials and WhatsApp number are required")
        
        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)
        
        # Initialize base class
        super().__init__(
            name="WhatsApp MCP Server",
            description="MCP server for WhatsApp messaging via Twilio",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all WhatsApp-related tools."""
        self._register_message_tools()
        self._register_template_tools()
    
    def _register_message_tools(self):
        @self.mcp_server.tool()
        def send_message(
            to: str,
            body: str,
            media_url: Optional[str] = None
        ) -> Dict[str, Any]:
            """Send a WhatsApp message."""
            try:
                message_params = {
                    "from": self.whatsapp_number,
                    "to": f"whatsapp:{to}",
                    "body": body
                }
                
                if media_url:
                    message_params["media_url"] = [media_url]
                
                message = self.client.messages.create(**message_params)
                
                return {
                    "message_sid": message.sid,
                    "status": message.status,
                    "to": message.to,
                    "from": message.from_,
                    "body": message.body
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def send_template_message(
            to: str,
            template_name: str,
            template_variables: Dict[str, str],
            language: str = "en"
        ) -> Dict[str, Any]:
            """Send a WhatsApp template message."""
            try:
                from twilio.base.exceptions import TwilioRestException
                
                # For template messages, we need to use the messaging service
                message = self.client.messages.create(
                    from_=self.whatsapp_number,
                    to=f"whatsapp:{to}",
                    content_sid=f"HX{template_name}",  # Template SID format
                    content_variables=json.dumps(template_variables)
                )
                
                return {
                    "message_sid": message.sid,
                    "status": message.status
                }
            except Exception as e:
                return {"error": str(e)}
        
        @self.mcp_server.tool()
        def get_message_status(message_sid: str) -> Dict[str, Any]:
            """Get the status of a WhatsApp message."""
            try:
                message = self.client.messages(message_sid).fetch()
                return {
                    "sid": message.sid,
                    "status": message.status,
                    "date_sent": message.date_sent.isoformat() if message.date_sent else None,
                    "error_code": message.error_code,
                    "error_message": message.error_message
                }
            except Exception as e:
                return {"error": str(e)}
    
    def _register_template_tools(self):
        @self.mcp_server.tool()
        def list_templates() -> Dict[str, Any]:
            """List available WhatsApp message templates."""
            # Note: This requires additional API calls or setup
            # Templates are managed in Facebook Business Manager
            # This is a placeholder implementation
            return {
                "templates": [
                    {"name": "welcome_message", "language": "en", "status": "approved"},
                    {"name": "order_confirmation", "language": "en", "status": "approved"},
                    {"name": "appointment_reminder", "language": "en", "status": "approved"}
                ]
            }