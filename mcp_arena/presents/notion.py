from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import os
import json

from notion_client import Client as NotionClient
from notion_client.errors import APIResponseError
from mcp_arena.mcp.server import BaseMCPServer

class NotionObjectType(str, Enum):
    DATABASE = "database"
    PAGE = "page"
    BLOCK = "block"
    USER = "user"
    COMMENT = "comment"

@dataclass
class NotionDatabaseInfo:
    id: str
    title: str
    description: Optional[str]
    url: str
    archived: bool
    icon: Optional[Dict[str, Any]]
    cover: Optional[Dict[str, Any]]
    properties: Dict[str, Any]
    parent: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime

@dataclass
class NotionPageInfo:
    id: str
    title: str
    url: str
    archived: bool
    icon: Optional[Dict[str, Any]]
    cover: Optional[Dict[str, Any]]
    properties: Dict[str, Any]
    parent: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime

@dataclass
class NotionBlockInfo:
    id: str
    type: str
    has_children: bool
    content: Dict[str, Any]
    created_time: datetime
    last_edited_time: datetime

class NotionMCPServer(BaseMCPServer):
    """Notion MCP Server for interacting with Notion databases, pages, and blocks."""
    
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
        """Initialize Notion MCP Server.
        
        Args:
            token: Notion integration token. If not provided, will try to get from NOTION_TOKEN env var.
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.__token = token or os.getenv("NOTION_TOKEN")
        if not self.__token:
            raise ValueError(
                "Notion token is required. "
                "Provide it as argument or set NOTION_TOKEN environment variable."
            )
        
        # Initialize Notion client
        self.notion = NotionClient(auth=self.__token)
        
        # Initialize base class
        super().__init__(
            name="Notion MCP Server",
            description="MCP server for interacting with Notion databases, pages, and blocks.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all Notion-related tools."""
        self._register_database_tools()
        self._register_page_tools()
        # self._register_block_tools()
        self._register_search_tools()
        # self._register_user_tools()

    def _register_database_tools(self):
        @self.mcp_server.tool()
        def get_database(
            database_id: Annotated[str, "Notion database ID"]
        ) -> Dict[str, Any]:
            """Get information about a Notion database"""
            try:
                database = self.notion.databases.retrieve(database_id=database_id)
                title = "".join([t["plain_text"] for t in database["title"]]) if database.get("title") else "Untitled"
                
                db_info = NotionDatabaseInfo(
                    id=database["id"],
                    title=title,
                    description=database.get("description", ""),
                    url=database["url"],
                    archived=database["archived"],
                    icon=database.get("icon"),
                    cover=database.get("cover"),
                    properties=database["properties"],
                    parent=database["parent"],
                    created_time=datetime.fromisoformat(database["created_time"].replace("Z", "+00:00")),
                    last_edited_time=datetime.fromisoformat(database["last_edited_time"].replace("Z", "+00:00"))
                )
                return asdict(db_info)
            except APIResponseError as e:
                return {"error": f"Failed to get database: {str(e)}"}

        @self.mcp_server.tool()
        def query_database(
            database_id: Annotated[str, "Notion database ID"],
            filter_properties: Annotated[Optional[List[str]], "Properties to filter"] = None,
            sorts: Annotated[Optional[List[Dict]], "Sort criteria"] = None,
            page_size: Annotated[int, "Number of results per page"] = 100
        ) -> Dict[str, Any]:
            """Query a Notion database"""
            try:
                response = self.notion.databases.query(
                    database_id=database_id,
                    filter_properties=filter_properties,
                    sorts=sorts,
                    page_size=page_size
                )
                return {
                    "results": response.get("results", []),
                    "has_more": response.get("has_more", False),
                    "next_cursor": response.get("next_cursor")
                }
            except APIResponseError as e:
                return {"error": f"Failed to query database: {str(e)}"}

    def _register_page_tools(self):
        @self.mcp_server.tool()
        def create_page(
            parent: Annotated[Dict[str, Any], "Parent database or page"],
            properties: Annotated[Dict[str, Any], "Page properties"],
            children: Annotated[Optional[List[Dict]], "Page content blocks"] = None
        ) -> Dict[str, Any]:
            """Create a new Notion page"""
            try:
                page = self.notion.pages.create(
                    parent=parent,
                    properties=properties,
                    children=children
                )
                return {"id": page["id"], "url": page["url"], "success": True}
            except APIResponseError as e:
                return {"error": f"Failed to create page: {str(e)}"}

        @self.mcp_server.tool()
        def get_page(
            page_id: Annotated[str, "Notion page ID"]
        ) -> Dict[str, Any]:
            """Get information about a Notion page"""
            try:
                page = self.notion.pages.retrieve(page_id=page_id)
                return page
            except APIResponseError as e:
                return {"error": f"Failed to get page: {str(e)}"}

    def _register_search_tools(self):
        @self.mcp_server.tool()
        def search_notion(
            query: Annotated[str, "Search query"],
            filter_property: Annotated[Optional[str], "Filter by object type"] = None,
            page_size: Annotated[int, "Number of results"] = 20
        ) -> Dict[str, Any]:
            """Search Notion"""
            try:
                response = self.notion.search(
                    query=query,
                    filter={"property": "object", "value": filter_property} if filter_property else None,
                    page_size=page_size
                )
                return {
                    "results": response.get("results", []),
                    "has_more": response.get("has_more", False),
                    "next_cursor": response.get("next_cursor")
                }
            except APIResponseError as e:
                return {"error": f"Failed to search: {str(e)}"}


