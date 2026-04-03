"""
Cloud Storage MCP Server
A comprehensive cloud storage server for interacting with AWS S3, Google Cloud Storage,
Azure Blob Storage, and other cloud storage providers.
"""
from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict
import os
from pathlib import Path
from mcp_arena.mcp.server import BaseMCPServer

# Lazy imports
_boto3 = None
_google_cloud_storage = None


def _import_boto3():
    """Lazily import boto3."""
    global _boto3
    if _boto3 is None:
        try:
            import boto3
            _boto3 = boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for AWS S3 operations. "
                "Install it with: pip install boto3"
            )
    return _boto3


def _import_gcs():
    """Lazily import Google Cloud Storage."""
    global _google_cloud_storage
    if _google_cloud_storage is None:
        try:
            from google.cloud import storage
            _google_cloud_storage = storage
        except ImportError:
            raise ImportError(
                "google-cloud-storage is required for GCS operations. "
                "Install it with: pip install google-cloud-storage"
            )
    return _google_cloud_storage


class CloudProvider(str, str):
    """Cloud storage providers."""
    AWS_S3 = "aws_s3"
    GOOGLE_GCS = "gcs"
    AZURE = "azure"


@dataclass
class CloudFileInfo:
    """Cloud file information."""
    key: str
    size: int
    last_modified: str
    etag: str
    storage_class: Optional[str] = None


class CloudStorageMCPServer(BaseMCPServer):
    """Cloud Storage MCP Server for multi-cloud storage operations."""

    def __init__(
        self,
        provider: str = "aws_s3",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_region: str = "us-east-1",
        s3_bucket_name: Optional[str] = None,
        gcs_project_id: Optional[str] = None,
        gcs_bucket_name: Optional[str] = None,
        gcs_credentials_path: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Cloud Storage MCP Server."""
        self.provider = CloudProvider(provider)
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = aws_region
        self.s3_bucket_name = s3_bucket_name or os.getenv("S3_BUCKET_NAME")
        self.gcs_project_id = gcs_project_id or os.getenv("GCS_PROJECT_ID")
        self.gcs_bucket_name = gcs_bucket_name or os.getenv("GCS_BUCKET_NAME")
        self.gcs_credentials_path = gcs_credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # Initialize clients on demand
        self._s3_client = None
        self._gcs_client = None

        super().__init__(
            name="Cloud Storage MCP Server",
            description="MCP server for multi-cloud storage operations (AWS S3, Google GCS, Azure Blob)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _get_s3_client(self):
        """Get or create S3 client."""
        if self._s3_client is None:
            boto3 = _import_boto3()
            self._s3_client = boto3.client(
                's3',
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region
            )
        return self._s3_client

    def _get_gcs_client(self):
        """Get or create GCS client."""
        if self._gcs_client is None:
            gcs = _import_gcs()
            if self.gcs_credentials_path:
                self._gcs_client = gcs.Client.from_service_account_json(
                    self.gcs_credentials_path,
                    project=self.gcs_project_id
                )
            else:
                self._gcs_client = gcs.Client(project=self.gcs_project_id)
        return self._gcs_client

    def _register_tools(self) -> None:
        """Register all cloud storage tools."""
        self._register_s3_tools()
        self._register_gcs_tools()
        self._register_common_tools()

    def _register_s3_tools(self):
        """Register AWS S3 tools."""

        @self.mcp_server.tool()
        def s3_list_buckets() -> Dict[str, Any]:
            """List all S3 buckets."""
            try:
                client = self._get_s3_client()
                response = client.list_buckets()

                return {
                    "success": True,
                    "provider": "aws_s3",
                    "buckets": [b['Name'] for b in response['Buckets']]
                }

            except Exception as e:
                return {"error": str(e), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_list_objects(
            bucket: Optional[str] = None,
            prefix: str = ""
        ) -> Dict[str, Any]:
            """List objects in an S3 bucket."""
            try:
                client = self._get_s3_client()
                bucket_name = bucket or self.s3_bucket_name

                if not bucket_name:
                    return {"error": "Bucket name not specified"}

                response = client.list_objects_v2(
                    Bucket=bucket_name,
                    Prefix=prefix
                )

                objects = []
                if 'Contents' in response:
                    for obj in response['Contents']:
                        objects.append({
                            "key": obj['Key'],
                            "size": obj['Size'],
                            "last_modified": str(obj['LastModified'])
                        })

                return {
                    "success": True,
                    "bucket": bucket_name,
                    "prefix": prefix,
                    "count": len(objects),
                    "objects": objects
                }

            except Exception as e:
                return {"error": str(e), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_upload_file(
            local_path: str,
            bucket: Optional[str] = None,
            s3_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Upload a file to S3."""
            try:
                client = self._get_s3_client()
                bucket_name = bucket or self.s3_bucket_name

                if not bucket_name:
                    return {"error": "Bucket name not specified"}

                s3_key = s3_key or os.path.basename(local_path)

                client.upload_file(local_path, bucket_name, s3_key)

                return {
                    "success": True,
                    "bucket": bucket_name,
                    "s3_key": s3_key,
                    "local_path": local_path
                }

            except Exception as e:
                return {"error": str(e), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_download_file(
            s3_key: str,
            local_path: str,
            bucket: Optional[str] = None
        ) -> Dict[str, Any]:
            """Download a file from S3."""
            try:
                client = self._get_s3_client()
                bucket_name = bucket or self.s3_bucket_name

                if not bucket_name:
                    return {"error": "Bucket name not specified"}

                client.download_file(bucket_name, s3_key, local_path)

                return {
                    "success": True,
                    "bucket": bucket_name,
                    "s3_key": s3_key,
                    "local_path": local_path
                }

            except Exception as e:
                return {"error": str(e), "provider": "aws_s3"}

    def _register_gcs_tools(self):
        """Register Google Cloud Storage tools."""

        @self.mcp_server.tool()
        def gcs_list_buckets() -> Dict[str, Any]:
            """List all GCS buckets."""
            try:
                client = self._get_gcs_client()

                buckets = list(client.list_buckets())

                return {
                    "success": True,
                    "provider": "gcs",
                    "buckets": [b.name for b in buckets]
                }

            except Exception as e:
                return {"error": str(e), "provider": "gcs"}

        @self.mcp_server.tool()
        def gcs_upload_file(
            local_path: str,
            bucket: Optional[str] = None,
            gcs_key: Optional[str] = None
        ) -> Dict[str, Any]:
            """Upload a file to GCS."""
            try:
                client = self._get_gcs_client()
                bucket_name = bucket or self.gcs_bucket_name

                if not bucket_name:
                    return {"error": "Bucket name not specified"}

                bucket = client.bucket(bucket_name)
                gcs_key = gcs_key or os.path.basename(local_path)
                blob = bucket.blob(gcs_key)
                blob.upload_from_filename(local_path)

                return {
                    "success": True,
                    "bucket": bucket_name,
                    "gcs_key": gcs_key,
                    "local_path": local_path
                }

            except Exception as e:
                return {"error": str(e), "provider": "gcs"}

    def _register_common_tools(self):
        """Register common cross-provider tools."""

        @self.mcp_server.tool()
        def get_provider_info() -> Dict[str, Any]:
            """Get configured cloud provider information."""
            return {
                "success": True,
                "provider": self.provider,
                "aws_region": self.aws_region,
                "s3_bucket": self.s3_bucket_name,
                "gcs_project": self.gcs_project_id,
                "gcs_bucket": self.gcs_bucket_name
            }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Cloud Storage MCP Server")
    parser.add_argument("--provider", choices=["aws_s3", "gcs"], default="aws_s3")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--bucket", type=str, default=None)
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    server = CloudStorageMCPServer(
        provider=args.provider,
        aws_region=args.region,
        s3_bucket_name=args.bucket,
        transport=args.transport,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    print("Starting Cloud Storage MCP Server")
    server.run()


if __name__ == "__main__":
    main()
