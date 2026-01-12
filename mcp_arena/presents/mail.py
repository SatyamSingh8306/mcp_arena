from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import base64
import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from mcp_arena.mcp.server import BaseMCPServer

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly',
          'https://www.googleapis.com/auth/gmail.send',
          'https://www.googleapis.com/auth/gmail.modify']

class EmailAttachment:
    filename: str
    mime_type: str
    data: bytes

class EmailMessage:
    id: str
    thread_id: str
    subject: str
    sender: str
    recipient: str
    date: datetime
    body: str
    labels: List[str]
    attachments: List[EmailAttachment]

class GmailMCPServer(BaseMCPServer):
    """Gmail MCP Server for email operations."""
    
    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: str = "token.json",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Gmail MCP Server.
        
        Args:
            credentials_path: Path to OAuth2 credentials JSON file
            token_path: Path to store/load OAuth2 token
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        # Initialize Gmail service
        self.creds = None
        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH')
        self.token_path = token_path
        
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not self.credentials_path:
                    raise ValueError("credentials_path is required for initial authentication")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            with open(self.token_path, 'w') as token:
                token.write(self.creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=self.creds)
        
        # Initialize base class
        super().__init__(
            name="Gmail MCP Server",
            description="MCP server for Gmail operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all Gmail-related tools."""
        self._register_email_tools()
    
    def _register_email_tools(self):
        @self.mcp_server.tool()
        def list_messages(
            max_results: int = 10,
            label_ids: Optional[List[str]] = None,
            query: str = ""
        ) -> Dict[str, Any]:
            """List email messages from Gmail."""
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                labelIds=label_ids,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            return {"messages": messages}
        
        @self.mcp_server.tool()
        def get_message(message_id: str) -> Dict[str, Any]:
            """Get a specific email message."""
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            return {"message": message}
        
        @self.mcp_server.tool()
        def send_email(
            to: str,
            subject: str,
            body: str,
            cc: Optional[str] = None,
            bcc: Optional[str] = None,
            attachments: Optional[List[Dict[str, Any]]] = None
        ) -> Dict[str, Any]:
            """Send an email via Gmail."""
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            
            message.attach(MIMEText(body, 'plain'))
            
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(base64.b64decode(attachment['data']))
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={attachment["filename"]}'
                    )
                    message.attach(part)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            send_response = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return {"message_id": send_response['id']}
        
        @self.mcp_server.tool()
        def create_draft(
            to: str,
            subject: str,
            body: str
        ) -> Dict[str, Any]:
            """Create a draft email."""
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            draft_response = self.service.users().drafts().create(
                userId='me',
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return {"draft_id": draft_response['id']}