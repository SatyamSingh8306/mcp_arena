from mcp.server.fastmcp import FastMCP
from typing import Literal, Annotated, Optional, List, Dict, Any, Union
from datetime import datetime, date
from dataclasses import dataclass, asdict, field
from enum import Enum
import boto3
from mcp_arena.mcp.server import BaseMCPServer

class S3ObjectInfo:
    key: str
    size: int
    last_modified: datetime
    storage_class: str
    etag: str

class S3MCPServer(BaseMCPServer):
    """AWS S3 MCP Server for S3 bucket and object operations."""
    
    def __init__(
        self,
        region_name: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize S3 MCP Server.
        
        Args:
            region_name: AWS region name (defaults to AWS default region)
            aws_access_key_id: AWS access key ID
            aws_secret_access_key: AWS secret access key
            aws_session_token: AWS session token
            endpoint_url: Custom S3 endpoint URL (for local/minio)
            host: Host to run server on
            port: Port to run server on
            transport: Transport type
            debug: Enable debug mode
            auto_register_tools: Automatically register tools on initialization
            **base_kwargs: Additional arguments for BaseMCPServer
        """
        # Initialize S3 client with provided credentials or use AWS default
        session_params = {}
        if region_name:
            session_params['region_name'] = region_name
        if aws_access_key_id and aws_secret_access_key:
            session_params['aws_access_key_id'] = aws_access_key_id
            session_params['aws_secret_access_key'] = aws_secret_access_key
            if aws_session_token:
                session_params['aws_session_token'] = aws_session_token
        
        session = boto3.Session(**session_params)
        
        s3_params = {}
        if endpoint_url:
            s3_params['endpoint_url'] = endpoint_url
        
        self.s3 = session.client('s3', **s3_params)
        
        # Initialize base class
        super().__init__(
            name="S3 MCP Server",
            description="MCP server for AWS S3 operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )
    
    def _register_tools(self) -> None:
        """Register all S3-related tools."""
        self._register_bucket_tools()
        # self._register_object_tools()
        # self._register_policy_tools()
        # self._register_versioning_tools()
        # self._register_lifecycle_tools()

    def _register_bucket_tools(self):
        @self.mcp_server.tool()
        def list_buckets() -> Dict[str, Any]:
            """List all S3 buckets"""
            response = self.s3.list_buckets()
            return {"buckets": [b["Name"] for b in response["Buckets"]]}

        @self.mcp_server.tool()
        def list_objects(bucket: str, prefix: str = "") -> Dict[str, Any]:
            """List objects in an S3 bucket"""
            response = self.s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
            objects = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    obj_info = S3ObjectInfo(
                        key=obj["Key"],
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        storage_class=obj.get("StorageClass", "STANDARD"),
                        etag=obj["ETag"]
                    )
                    objects.append(asdict(obj_info))
            return {"objects": objects}