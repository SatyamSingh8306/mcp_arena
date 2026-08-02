"""Outlook MCP server: email and calendar via Microsoft Graph."""
from typing import Any, Dict, List, Literal, Optional

import msal
import requests

from mcp_arena.mcp.server import BaseMCPServer

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class OutlookMCPServer(BaseMCPServer):
    """Microsoft Outlook MCP server (email + calendar)."""
    _REQUIRED_EXTRAS = {"msal": "outlook", "requests": "outlook"}

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str = "common",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.scopes = ["https://graph.microsoft.com/.default"]

        # Lazy MSAL client + token: don't hit AAD at construction time.
        # Tests construct with stub creds; real token is fetched on first call.
        self._msal_app: Optional[msal.ConfidentialClientApplication] = None
        self.headers: Dict[str, str] = {
            "Authorization": "Bearer pending",
            "Content-Type": "application/json",
        }

        super().__init__(
            name="Outlook MCP Server",
            description="MCP server for Microsoft Outlook operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _get_headers(self) -> Dict[str, str]:
        """Acquire (or refresh) an MSAL access token and return auth headers."""
        if self._msal_app is None:
            try:
                self._msal_app = msal.ConfidentialClientApplication(
                    self.client_id,
                    authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                    client_credential=self.client_secret,
                )
            except Exception:
                # Offline / test env — keep stub headers so tool calls degrade
                # gracefully rather than blowing up at construction time.
                return self.headers
        try:
            result = self._msal_app.acquire_token_for_client(scopes=self.scopes)
            if result and "access_token" in result:
                self.headers = {
                    "Authorization": f"Bearer {result['access_token']}",
                    "Content-Type": "application/json",
                }
        except Exception:
            pass
        return self.headers

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def get_messages(top: int = 10, filter: Optional[str] = None) -> Dict[str, Any]:
            """Get email messages from Outlook."""
            params = {"$top": top}
            if filter:
                params["$filter"] = filter
            response = requests.get(
                f"{GRAPH_BASE}/me/messages",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

        @self.mcp_server.tool()
        def send_email(
            to_recipients: List[str],
            subject: str,
            body: str,
            cc_recipients: Optional[List[str]] = None,
            bcc_recipients: Optional[List[str]] = None,
            importance: str = "normal",
        ) -> Dict[str, Any]:
            """Send an email via Outlook."""
            message = {
                "message": {
                    "subject": subject,
                    "body": {"contentType": "text", "content": body},
                    "toRecipients": [{"emailAddress": {"address": addr}} for addr in to_recipients],
                    "importance": importance,
                }
            }
            if cc_recipients:
                message["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in cc_recipients
                ]
            if bcc_recipients:
                message["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": addr}} for addr in bcc_recipients
                ]
            response = requests.post(
                f"{GRAPH_BASE}/me/sendMail",
                headers=self._get_headers(),
                json=message,
            )
            response.raise_for_status()
            return {"status": "sent"}

        @self.mcp_server.tool()
        def get_calendar_events(start_date: str, end_date: str) -> Dict[str, Any]:
            """Get calendar events in a date range."""
            params = {
                "startDateTime": start_date,
                "endDateTime": end_date,
                "$orderby": "start/dateTime",
            }
            response = requests.get(
                f"{GRAPH_BASE}/me/calendarview",
                headers=self._get_headers(),
                params=params,
            )
            response.raise_for_status()
            return response.json()

        @self.mcp_server.tool()
        def create_calendar_event(
            subject: str,
            start_time: str,
            end_time: str,
            attendees: List[str],
            location: Optional[str] = None,
            body: Optional[str] = None,
            is_online: bool = False,
        ) -> Dict[str, Any]:
            """Create a calendar event."""
            event = {
                "subject": subject,
                "start": {"dateTime": start_time, "timeZone": "UTC"},
                "end": {"dateTime": end_time, "timeZone": "UTC"},
                "attendees": [
                    {"emailAddress": {"address": email}, "type": "required"}
                    for email in attendees
                ],
                "isOnlineMeeting": is_online,
            }
            if location:
                event["location"] = {"displayName": location}
            if body:
                event["body"] = {"contentType": "text", "content": body}
            response = requests.post(
                f"{GRAPH_BASE}/me/events",
                headers=self._get_headers(),
                json=event,
            )
            response.raise_for_status()
            return response.json()

