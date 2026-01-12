from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import base64
from mcp_arena.mcp.server import BaseMCPServer

class SMTPConfig:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool
    use_ssl: bool

class SMTPServer(BaseMCPServer):
    """SMTP MCP Server for sending emails via SMTP protocol."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int = 587,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = True,
        use_ssl: bool = False,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize SMTP MCP Server.
        
        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            use_tls: Use TLS encryption
            use_ssl: Use SSL encryption
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.smtp_config = SMTPConfig(
            host=smtp_host,
            port=smtp_port,
            username=username,
            password=password,
            use_tls=use_tls,
            use_ssl=use_ssl
        )
        
        # Initialize base class
        super().__init__(
            name="SMTP MCP Server",
            description="MCP server for SMTP email operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _get_smtp_connection(self) -> smtplib.SMTP:
        """Create and return an SMTP connection."""
        if self.smtp_config.use_ssl:
            server = smtplib.SMTP_SSL(self.smtp_config.host, self.smtp_config.port)
        else:
            server = smtplib.SMTP(self.smtp_config.host, self.smtp_config.port)
        
        if self.smtp_config.use_tls and not self.smtp_config.use_ssl:
            server.starttls()
        
        if self.smtp_config.username and self.smtp_config.password:
            server.login(self.smtp_config.username, self.smtp_config.password)
        
        return server
    
    def _register_tools(self) -> None:
        """Register all SMTP-related tools."""
        self._register_email_tools()
    
    def _register_email_tools(self):
        @self.mcp_server.tool()
        def send_email(
            from_addr: str,
            to_addrs: List[str],
            subject: str,
            body: str,
            cc_addrs: Optional[List[str]] = None,
            bcc_addrs: Optional[List[str]] = None,
            attachments: Optional[List[Dict[str, Any]]] = None,
            html_body: Optional[str] = None
        ) -> Dict[str, Any]:
            """Send an email via SMTP."""
            # Create message
            if html_body:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(body, 'plain'))
                msg.attach(MIMEText(html_body, 'html'))
            else:
                msg = MIMEMultipart()
                msg.attach(MIMEText(body, 'plain'))
            
            msg['From'] = from_addr
            msg['To'] = ', '.join(to_addrs)
            msg['Subject'] = subject
            
            if cc_addrs:
                msg['Cc'] = ', '.join(cc_addrs)
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(base64.b64decode(attachment['data']))
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename={attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            all_recipients = to_addrs.copy()
            if cc_addrs:
                all_recipients.extend(cc_addrs)
            if bcc_addrs:
                all_recipients.extend(bcc_addrs)
            
            try:
                server = self._get_smtp_connection()
                server.sendmail(from_addr, all_recipients, msg.as_string())
                server.quit()
                
                return {
                    "status": "success",
                    "sent_to": all_recipients,
                    "message": "Email sent successfully"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e)
                }
        
        @self.mcp_server.tool()
        def test_connection() -> Dict[str, Any]:
            """Test SMTP server connection."""
            try:
                server = self._get_smtp_connection()
                server.quit()
                return {
                    "status": "success",
                    "message": "SMTP connection successful"
                }
            except Exception as e:
                return {
                    "status": "error",
                    "error": str(e)
                }