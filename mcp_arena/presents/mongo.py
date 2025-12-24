from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from bson import ObjectId, json_util
import json
import os

@dataclass
class MongoDatabaseInfo:
    name: str
    size_on_disk: int
    empty: bool
    collections: List[str]

@dataclass
class MongoCollectionInfo:
    name: str
    count: int
    size: int
    avg_obj_size: int
    storage_size: int
    indexes: List[Dict[str, Any]]
    index_sizes: Dict[str, int]

@dataclass
class QueryOptions:
    limit: int = 100
    skip: int = 0
    sort: Optional[List[tuple]] = None
    projection: Optional[Dict] = None

from mcp_arena.mcp.server import BaseMCPServer

class MongoDBMCPServer(BaseMCPServer):
    """MongoDB MCP Server for interacting with MongoDB databases and collections."""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize MongoDB MCP Server.
        
        Args:
            connection_string: MongoDB connection string. If not provided, will try to get from MONGODB_CONNECTION_STRING env var.
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        self.connection_string = connection_string or os.getenv("MONGODB_CONNECTION_STRING")
        if not self.connection_string:
            raise ValueError(
                "MongoDB connection string is required. "
                "Provide it as argument or set MONGODB_CONNECTION_STRING environment variable."
            )
        
        # Initialize MongoDB client
        self.client = MongoClient(self.connection_string)
        
        # Initialize base class
        super().__init__(
            name="MongoDB MCP Server",
            description="MCP server for interacting with MongoDB databases and collections.",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all MongoDB-related tools."""
        self._register_database_tools()
        self._register_collection_tools()
        self._register_document_tools()
        # self._register_index_tools()
        # self._register_aggregation_tools()

    def _register_database_tools(self):
        @self.mcp_server.tool()
        def list_databases() -> Dict[str, Any]:
            """List all databases"""
            try:
                databases = self.client.list_database_names()
                db_info_list = []
                
                for db_name in databases:
                    if db_name not in ["admin", "local", "config"]:
                        db = self.client[db_name]
                        stats = db.command("dbStats")
                        
                        db_info = MongoDatabaseInfo(
                            name=db_name,
                            size_on_disk=stats.get("sizeOnDisk", 0),
                            empty=stats.get("empty", True),
                            collections=stats.get("collections", [])
                        )
                        db_info_list.append(asdict(db_info))
                
                return {"databases": db_info_list, "count": len(db_info_list)}
            except PyMongoError as e:
                return {"error": f"Failed to list databases: {str(e)}"}

        @self.mcp_server.tool()
        def get_database_info(
            database_name: Annotated[str, "Database name"]
        ) -> Dict[str, Any]:
            """Get information about a specific database"""
            try:
                db = self.client[database_name]
                stats = db.command("dbStats")
                
                db_info = MongoDatabaseInfo(
                    name=database_name,
                    size_on_disk=stats.get("sizeOnDisk", 0),
                    empty=stats.get("empty", True),
                    collections=stats.get("collections", [])
                )
                
                return asdict(db_info)
            except PyMongoError as e:
                return {"error": f"Failed to get database info: {str(e)}"}

    def _register_collection_tools(self):
        @self.mcp_server.tool()
        def list_collections(
            database_name: Annotated[str, "Database name"]
        ) -> Dict[str, Any]:
            """List all collections in a database"""
            try:
                db = self.client[database_name]
                collections = db.list_collection_names()
                
                collection_info_list = []
                for coll_name in collections:
                    coll = db[coll_name]
                    stats = db.command("collStats", coll_name)
                    
                    coll_info = MongoCollectionInfo(
                        name=coll_name,
                        count=stats.get("count", 0),
                        size=stats.get("size", 0),
                        avg_obj_size=stats.get("avgObjSize", 0),
                        storage_size=stats.get("storageSize", 0),
                        indexes=stats.get("indexDetails", []),
                        index_sizes=stats.get("indexSizes", {})
                    )
                    collection_info_list.append(asdict(coll_info))
                
                return {
                    "database": database_name,
                    "collections": collection_info_list,
                    "count": len(collection_info_list)
                }
            except PyMongoError as e:
                return {"error": f"Failed to list collections: {str(e)}"}

        @self.mcp_server.tool()
        def get_collection_info(
            database_name: Annotated[str, "Database name"],
            collection_name: Annotated[str, "Collection name"]
        ) -> Dict[str, Any]:
            """Get information about a specific collection"""
            try:
                db = self.client[database_name]
                stats = db.command("collStats", collection_name)
                
                coll_info = MongoCollectionInfo(
                    name=collection_name,
                    count=stats.get("count", 0),
                    size=stats.get("size", 0),
                    avg_obj_size=stats.get("avgObjSize", 0),
                    storage_size=stats.get("storageSize", 0),
                    indexes=stats.get("indexDetails", []),
                    index_sizes=stats.get("indexSizes", {})
                )
                
                return asdict(coll_info)
            except PyMongoError as e:
                return {"error": f"Failed to get collection info: {str(e)}"}

    def _register_document_tools(self):
        @self.mcp_server.tool()
        def find_documents(
            database_name: Annotated[str, "Database name"],
            collection_name: Annotated[str, "Collection name"],
            query: Annotated[Optional[Dict], "MongoDB query filter"] = None,
            limit: Annotated[int, "Maximum number of documents to return"] = 100,
            skip: Annotated[int, "Number of documents to skip"] = 0,
            sort: Annotated[Optional[str], "Sort specification as JSON"] = None,
            projection: Annotated[Optional[str], "Projection specification as JSON"] = None
        ) -> Dict[str, Any]:
            """Find documents in a collection"""
            try:
                db = self.client[database_name]
                collection = db[collection_name]
                
                # Parse parameters
                query_dict = json.loads(query) if query else {}
                sort_list = json.loads(sort) if sort else None
                projection_dict = json.loads(projection) if projection else None
                
                # Convert string IDs to ObjectId for _id queries
                if "_id" in query_dict and isinstance(query_dict["_id"], str):
                    try:
                        query_dict["_id"] = ObjectId(query_dict["_id"])
                    except:
                        pass
                
                cursor = collection.find(
                    filter=query_dict,
                    limit=limit,
                    skip=skip,
                    sort=sort_list,
                    projection=projection_dict
                )
                
                documents = []
                for doc in cursor:
                    # Convert ObjectId to string for JSON serialization
                    if "_id" in doc and isinstance(doc["_id"], ObjectId):
                        doc["_id"] = str(doc["_id"])
                    documents.append(doc)
                
                total_count = collection.count_documents(query_dict) if query_dict else collection.estimated_document_count()
                
                return {
                    "database": database_name,
                    "collection": collection_name,
                    "documents": documents,
                    "count": len(documents),
                    "total_count": total_count,
                    "limit": limit,
                    "skip": skip
                }
            except (PyMongoError, json.JSONDecodeError) as e:
                return {"error": f"Failed to find documents: {str(e)}"}

        @self.mcp_server.tool()
        def insert_document(
            database_name: Annotated[str, "Database name"],
            collection_name: Annotated[str, "Collection name"],
            document: Annotated[str, "Document to insert as JSON"]
        ) -> Dict[str, Any]:
            """Insert a document into a collection"""
            try:
                db = self.client[database_name]
                collection = db[collection_name]
                
                document_dict = json.loads(document)
                result = collection.insert_one(document_dict)
                
                return {
                    "success": True,
                    "inserted_id": str(result.inserted_id),
                    "database": database_name,
                    "collection": collection_name
                }
            except (PyMongoError, json.JSONDecodeError) as e:
                return {"error": f"Failed to insert document: {str(e)}"}
