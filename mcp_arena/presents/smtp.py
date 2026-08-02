"""SMTP MCP server: send email via arbitrary SMTP server."""
import base64
import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer


class SMTPServer(BaseMCPServer):
    """SMTP MCP server."""
    _REQUIRED_EXTRAS = {}

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
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl

        super().__init__(
            name="SMTP MCP Server",
            description="MCP server for SMTP email operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _connect(self) -> smtplib.SMTP:
        server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) if self.use_ssl \
            else smtplib.SMTP(self.smtp_host, self.smtp_port)
        if self.use_tls and not self.use_ssl:
            server.starttls()
        if self.username and self.password:
            server.login(self.username, self.password)
        return server

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def send_email(
            from_addr: str,
            to_addrs: List[str],
            subject: str,
            body: str,
            cc_addrs: Optional[List[str]] = None,
            bcc_addrs: Optional[List[str]] = None,
            attachments: Optional[List[Dict[str, Any]]] = None,
            html_body: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Send an email via SMTP."""
            msg = MIMEMultipart("alternative" if html_body else "mixed")
            if html_body:
                msg.attach(MIMEText(body, "plain"))
                msg.attach(MIMEText(html_body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            msg["From"] = from_addr
            msg["To"] = ", ".join(to_addrs)
            msg["Subject"] = subject
            if cc_addrs:
                msg["Cc"] = ", ".join(cc_addrs)

            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(base64.b64decode(attachment["data"]))
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename={attachment["filename"]}',
                    )
                    msg.attach(part)

            all_recipients = list(to_addrs)
            if cc_addrs:
                all_recipients.extend(cc_addrs)
            if bcc_addrs:
                all_recipients.extend(bcc_addrs)

            try:
                server = self._connect()
                try:
                    server.sendmail(from_addr, all_recipients, msg.as_string())
                finally:
                    server.quit()
                return {"status": "success", "sent_to": all_recipients, "message": "Email sent successfully"}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

        @self.mcp_server.tool()
        def test_connection() -> Dict[str, Any]:
            """Test SMTP server connection."""
            try:
                server = self._connect()
                server.quit()
                return {"status": "success", "message": "SMTP connection successful"}
            except Exception as exc:
                return {"status": "error", "error": str(exc)}

