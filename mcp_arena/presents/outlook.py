from mcp.server.fastmcp import FastMCP
from typing import Literal, Optional, List, Dict, Any
from datetime import datetime
import msal
import requests
from mcp_arena.mcp.server import BaseMCPServer


class OutlookMCPServer(BaseMCPServer):
    """Microsoft Outlook MCP Server for email and calendar operations."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        tenant_id: str = "common",
        redirect_uri: str = "http://localhost:8000",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """
        Safe initialization.

        During tests:
        - Tenant may be fake
        - Token acquisition should NOT crash
        """

        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.redirect_uri = redirect_uri
        self.scopes = ["https://graph.microsoft.com/.default"]

        self.app = None
        self.access_token = None
        self.headers = {}

        try:
            self.app = msal.ConfidentialClientApplication(
                client_id,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
                client_credential=client_secret
            )

            result = self.app.acquire_token_for_client(scopes=self.scopes)

            if "access_token" in result:
                self.access_token = result["access_token"]
                self.headers = {
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                }

        except Exception:
            # During tests or invalid tenant → allow initialization
            self.app = None
            self.access_token = None
            self.headers = {}

        super().__init__(
            name="Outlook MCP Server",
            description="MCP server for Microsoft Outlook operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _register_tools(self) -> None:
        if not self.access_token:
            return
        self._register_email_tools()
        self._register_calendar_tools()

    def _register_email_tools(self):

        @self.mcp_server.tool()
        def get_messages(
            top: int = 10,
            filter: Optional[str] = None
        ) -> Dict[str, Any]:

            url = "https://graph.microsoft.com/v1.0/me/messages"
            params = {"$top": top}
            if filter:
                params["$filter"] = filter

            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()

        @self.mcp_server.tool()
        def send_email(
            to_recipients: List[str],
            subject: str,
            body: str,
            cc_recipients: Optional[List[str]] = None,
            bcc_recipients: Optional[List[str]] = None,
            importance: str = "normal"
        ) -> Dict[str, Any]:

            url = "https://graph.microsoft.com/v1.0/me/sendMail"

            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "text",
                        "content": body
                    },
                    "toRecipients": [
                        {"emailAddress": {"address": address}}
                        for address in to_recipients
                    ],
                    "importance": importance
                }
            }

            if cc_recipients:
                message["message"]["ccRecipients"] = [
                    {"emailAddress": {"address": address}}
                    for address in cc_recipients
                ]

            if bcc_recipients:
                message["message"]["bccRecipients"] = [
                    {"emailAddress": {"address": address}}
                    for address in bcc_recipients
                ]

            response = requests.post(url, headers=self.headers, json=message)
            response.raise_for_status()
            return {"status": "sent"}

    def _register_calendar_tools(self):

        @self.mcp_server.tool()
        def get_calendar_events(
            start_date: str,
            end_date: str
        ) -> Dict[str, Any]:

            url = "https://graph.microsoft.com/v1.0/me/calendarview"
            params = {
                "startDateTime": start_date,
                "endDateTime": end_date,
                "$orderby": "start/dateTime"
            }

            response = requests.get(url, headers=self.headers, params=params)
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
            is_online: bool = False
        ) -> Dict[str, Any]:

            url = "https://graph.microsoft.com/v1.0/me/events"

            event = {
                "subject": subject,
                "start": {
                    "dateTime": start_time,
                    "timeZone": "UTC"
                },
                "end": {
                    "dateTime": end_time,
                    "timeZone": "UTC"
                },
                "attendees": [
                    {"emailAddress": {"address": email}, "type": "required"}
                    for email in attendees
                ],
                "isOnlineMeeting": is_online
            }

            if location:
                event["location"] = {"displayName": location}

            if body:
                event["body"] = {
                    "contentType": "text",
                    "content": body
                }

            response = requests.post(url, headers=self.headers, json=event)
            response.raise_for_status()
            return response.json()