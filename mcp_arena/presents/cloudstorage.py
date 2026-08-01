"""Cloud storage MCP server: AWS S3 and Google Cloud Storage."""
import os
from typing import Any, Dict, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import boto3 as _boto3
except ImportError:
    _boto3 = None

try:
    from google.cloud import storage as _gcs
except ImportError:
    _gcs = None


def _ensure_boto3():
    if _boto3 is None:
        raise ImportError("boto3 is required. pip install boto3")
    return _boto3


def _ensure_gcs():
    if _gcs is None:
        raise ImportError("google-cloud-storage is required. pip install google-cloud-storage")
    return _gcs


class CloudStorageMCPServer(BaseMCPServer):
    """Cloud storage MCP server (AWS S3, Google GCS)."""
    _REQUIRED_EXTRAS = {"boto3": "cloudstorage", "google.cloud.storage": "cloudstorage"}

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
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.provider = provider
        self.aws_access_key_id = aws_access_key_id or os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = aws_region
        self.s3_bucket_name = s3_bucket_name or os.getenv("S3_BUCKET_NAME")
        self.gcs_project_id = gcs_project_id or os.getenv("GCS_PROJECT_ID")
        self.gcs_bucket_name = gcs_bucket_name or os.getenv("GCS_BUCKET_NAME")
        self.gcs_credentials_path = gcs_credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        self._s3_client = None
        self._gcs_client = None

        super().__init__(
            name="Cloud Storage MCP Server",
            description="MCP server for multi-cloud storage operations (AWS S3, Google GCS)",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _get_s3_client(self):
        if self._s3_client is None:
            boto3 = _ensure_boto3()
            self._s3_client = boto3.client(
                "s3",
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.aws_region,
            )
        return self._s3_client

    def _get_gcs_client(self):
        if self._gcs_client is None:
            gcs = _ensure_gcs()
            if self.gcs_credentials_path:
                self._gcs_client = gcs.Client.from_service_account_json(
                    self.gcs_credentials_path,
                    project=self.gcs_project_id,
                )
            else:
                self._gcs_client = gcs.Client(project=self.gcs_project_id)
        return self._gcs_client

    def _register_tools(self) -> None:
        self._register_s3_tools()
        self._register_gcs_tools()
        self._register_common_tools()

    def _register_s3_tools(self):
        @self.mcp_server.tool()
        def s3_list_buckets() -> Dict[str, Any]:
            """List all S3 buckets."""
            try:
                response = self._get_s3_client().list_buckets()
                return {
                    "success": True,
                    "provider": "aws_s3",
                    "buckets": [b["Name"] for b in response["Buckets"]],
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_list_objects(bucket: Optional[str] = None, prefix: str = "") -> Dict[str, Any]:
            """List objects in an S3 bucket."""
            try:
                bucket_name = bucket or self.s3_bucket_name
                if not bucket_name:
                    return {"error": "Bucket name not specified"}
                response = self._get_s3_client().list_objects_v2(Bucket=bucket_name, Prefix=prefix)
                objects = [
                    {"key": o["Key"], "size": o["Size"], "last_modified": str(o["LastModified"])}
                    for o in response.get("Contents", [])
                ]
                return {
                    "success": True,
                    "bucket": bucket_name,
                    "prefix": prefix,
                    "count": len(objects),
                    "objects": objects,
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_upload_file(
            local_path: str,
            bucket: Optional[str] = None,
            s3_key: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Upload a file to S3."""
            try:
                bucket_name = bucket or self.s3_bucket_name
                if not bucket_name:
                    return {"error": "Bucket name not specified"}
                s3_key = s3_key or os.path.basename(local_path)
                self._get_s3_client().upload_file(local_path, bucket_name, s3_key)
                return {
                    "success": True,
                    "bucket": bucket_name,
                    "s3_key": s3_key,
                    "local_path": local_path,
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "aws_s3"}

        @self.mcp_server.tool()
        def s3_download_file(
            s3_key: str,
            local_path: str,
            bucket: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Download a file from S3."""
            try:
                bucket_name = bucket or self.s3_bucket_name
                if not bucket_name:
                    return {"error": "Bucket name not specified"}
                self._get_s3_client().download_file(bucket_name, s3_key, local_path)
                return {
                    "success": True,
                    "bucket": bucket_name,
                    "s3_key": s3_key,
                    "local_path": local_path,
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "aws_s3"}

    def _register_gcs_tools(self):
        @self.mcp_server.tool()
        def gcs_list_buckets() -> Dict[str, Any]:
            """List all GCS buckets."""
            try:
                buckets = list(self._get_gcs_client().list_buckets())
                return {
                    "success": True,
                    "provider": "gcs",
                    "buckets": [b.name for b in buckets],
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "gcs"}

        @self.mcp_server.tool()
        def gcs_upload_file(
            local_path: str,
            bucket: Optional[str] = None,
            gcs_key: Optional[str] = None,
        ) -> Dict[str, Any]:
            """Upload a file to GCS."""
            try:
                bucket_name = bucket or self.gcs_bucket_name
                if not bucket_name:
                    return {"error": "Bucket name not specified"}
                gcs_key = gcs_key or os.path.basename(local_path)
                blob = self._get_gcs_client().bucket(bucket_name).blob(gcs_key)
                blob.upload_from_filename(local_path)
                return {
                    "success": True,
                    "bucket": bucket_name,
                    "gcs_key": gcs_key,
                    "local_path": local_path,
                }
            except Exception as exc:
                return {"error": str(exc), "provider": "gcs"}

    def _register_common_tools(self):
        @self.mcp_server.tool()
        def get_provider_info() -> Dict[str, Any]:
            """Get configured cloud provider information."""
            return {
                "success": True,
                "provider": self.provider,
                "aws_region": self.aws_region,
                "s3_bucket": self.s3_bucket_name,
                "gcs_project": self.gcs_project_id,
                "gcs_bucket": self.gcs_bucket_name,
            }

