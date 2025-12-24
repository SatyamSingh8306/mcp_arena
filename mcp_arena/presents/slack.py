from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import os
import json
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from mcp_arena.mcp.server import BaseMCPServer

@dataclass
class SlackChannelInfo:
    id: str
    name: str
    is_channel: bool
    is_group: bool
    is_im: bool
    is_private: bool
    is_archived: bool
    created: int
    creator: str
    is_general: bool
    name_normalized: str
    num_members: int
    purpose: Dict[str, Any]
    topic: Dict[str, Any]
    latest: Optional[Dict[str, Any]]

@dataclass
class SlackMessageInfo:
    ts: str
    type: str
    user: str
    text: str
    thread_ts: Optional[str]
    reply_count: Optional[int]
    replies: Optional[List[Dict]]
    reactions: List[Dict]
    blocks: List[Dict]
    files: List[Dict]

@dataclass
class SlackUserInfo:
    id: str
    name: str
    real_name: str
    display_name: str
    email: Optional[str]
    is_admin: bool
    is_owner: bool
    is_bot: bool
    tz: str
    tz_label: str
    tz_offset: int
    profile: Dict[str, Any]

class SlackMCPServer(BaseMCPServer):
    """Slack MCP Server for interacting with Slack channels, messages, and users."""
    
    def __init__(
        self,
        token: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Slack MCP Server.
        
        Args:
            token: Slack Bot User OAuth Token. If not provided, will try to get from SLACK_TOKEN env var.
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.__token = token or os.getenv("SLACK_TOKEN")
        if not self.__token:
            raise ValueError(
                "Slack token is required. "
                "Provide it as argument or set SLACK_TOKEN environment variable."
            )
        
        # Initialize Slack client
        self.client = WebClient(token=self.__token)
        
        # Initialize base class
        super().__init__(
            name="Slack MCP Server",
            description="MCP server for interacting with Slack channels, messages, and users.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all Slack-related tools."""
        self._register_channel_tools()
        self._register_message_tools()
        # self._register_user_tools()
        # self._register_file_tools()
        # self._register_conversation_tools()
        # self._register_workspace_tools()

    def _register_channel_tools(self):
        @self.mcp_server.tool()
        def list_channels(
            types: Annotated[str, "Comma-separated list of channel types (public_channel, private_channel, mpim, im)"] = "public_channel",
            exclude_archived: Annotated[bool, "Exclude archived channels"] = True
        ) -> Dict[str, Any]:
            """List Slack channels"""
            try:
                response = self.client.conversations_list(
                    types=types,
                    exclude_archived=exclude_archived
                )
                channels = []
                for channel in response["channels"]:
                    channel_info = SlackChannelInfo(
                        id=channel["id"],
                        name=channel["name"],
                        is_channel=channel.get("is_channel", False),
                        is_group=channel.get("is_group", False),
                        is_im=channel.get("is_im", False),
                        is_private=channel.get("is_private", False),
                        is_archived=channel.get("is_archived", False),
                        created=channel.get("created", 0),
                        creator=channel.get("creator", ""),
                        is_general=channel.get("is_general", False),
                        name_normalized=channel.get("name_normalized", ""),
                        num_members=channel.get("num_members", 0),
                        purpose=channel.get("purpose", {}),
                        topic=channel.get("topic", {}),
                        latest=channel.get("latest")
                    )
                    channels.append(asdict(channel_info))
                
                return {
                    "channels": channels,
                    "count": len(channels)
                }
            except SlackApiError as e:
                return {"error": f"Failed to list channels: {str(e)}"}

        @self.mcp_server.tool()
        def get_channel_info(
            channel_id: Annotated[str, "Slack channel ID"]
        ) -> Dict[str, Any]:
            """Get information about a Slack channel"""
            try:
                response = self.client.conversations_info(channel=channel_id)
                channel = response["channel"]
                
                channel_info = SlackChannelInfo(
                    id=channel["id"],
                    name=channel["name"],
                    is_channel=channel.get("is_channel", False),
                    is_group=channel.get("is_group", False),
                    is_im=channel.get("is_im", False),
                    is_private=channel.get("is_private", False),
                    is_archived=channel.get("is_archived", False),
                    created=channel.get("created", 0),
                    creator=channel.get("creator", ""),
                    is_general=channel.get("is_general", False),
                    name_normalized=channel.get("name_normalized", ""),
                    num_members=channel.get("num_members", 0),
                    purpose=channel.get("purpose", {}),
                    topic=channel.get("topic", {}),
                    latest=channel.get("latest")
                )
                return asdict(channel_info)
            except SlackApiError as e:
                return {"error": f"Failed to get channel info: {str(e)}"}

    def _register_message_tools(self):
        @self.mcp_server.tool()
        def send_message(
            channel: Annotated[str, "Channel ID or name"],
            text: Annotated[str, "Message text"],
            blocks: Annotated[Optional[List[Dict]], "Message blocks"] = None,
            thread_ts: Annotated[Optional[str], "Thread timestamp"] = None
        ) -> Dict[str, Any]:
            """Send a message to a Slack channel"""
            try:
                response = self.client.chat_postMessage(
                    channel=channel,
                    text=text,
                    blocks=blocks,
                    thread_ts=thread_ts
                )
                return {
                    "ts": response["ts"],
                    "channel": response["channel"],
                    "message": response["message"],
                    "success": True
                }
            except SlackApiError as e:
                return {"error": f"Failed to send message: {str(e)}"}

        @self.mcp_server.tool()
        def get_channel_history(
            channel_id: Annotated[str, "Slack channel ID"],
            limit: Annotated[int, "Number of messages to retrieve"] = 100,
            oldest: Annotated[Optional[str], "Start time (timestamp)"] = None,
            latest: Annotated[Optional[str], "End time (timestamp)"] = None
        ) -> Dict[str, Any]:
            """Get message history from a Slack channel"""
            try:
                response = self.client.conversations_history(
                    channel=channel_id,
                    limit=limit,
                    oldest=oldest,
                    latest=latest
                )
                
                messages = []
                for msg in response["messages"]:
                    msg_info = SlackMessageInfo(
                        ts=msg["ts"],
                        type=msg.get("type", "message"),
                        user=msg.get("user", ""),
                        text=msg.get("text", ""),
                        thread_ts=msg.get("thread_ts"),
                        reply_count=msg.get("reply_count"),
                        replies=msg.get("replies"),
                        reactions=msg.get("reactions", []),
                        blocks=msg.get("blocks", []),
                        files=msg.get("files", [])
                    )
                    messages.append(asdict(msg_info))
                
                return {
                    "messages": messages,
                    "has_more": response.get("has_more", False),
                    "pin_count": response.get("pin_count", 0)
                }
            except SlackApiError as e:
                return {"error": f"Failed to get channel history: {str(e)}"}