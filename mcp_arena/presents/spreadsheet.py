"""Spreadsheet MCP server: read/write CSV and Excel via pandas."""
import os
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import pandas as _pd
except ImportError:
    _pd = None


def _ensure_pandas():
    if _pd is None:
        raise ImportError("pandas is required. pip install pandas")
    return _pd


class SpreadsheetMCPServer(BaseMCPServer):
    """Spreadsheet MCP server."""
    _REQUIRED_EXTRAS = {"openpyxl": "spreadsheet", "pandas": "spreadsheet"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "spreadsheet_output")
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)
        super().__init__(
            name="Spreadsheet MCP Server",
            description="MCP server for spreadsheet operations",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def read_spreadsheet(file_path: str) -> Dict[str, Any]:
            """Read a CSV or XLSX file."""
            try:
                pd = _ensure_pandas()
                if file_path.endswith(".csv"):
                    df = pd.read_csv(file_path)
                elif file_path.endswith(".xlsx"):
                    df = pd.read_excel(file_path)
                else:
                    return {"error": "Unsupported file format. Use .csv or .xlsx"}
                return {
                    "success": True,
                    "rows": len(df),
                    "columns": len(df.columns),
                    "columns_list": df.columns.tolist(),
                    "sample_data": df.head().to_dict(),
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def create_spreadsheet(data: list, output_path: str) -> Dict[str, Any]:
            """Create a CSV or XLSX from a list of dicts."""
            try:
                pd = _ensure_pandas()
                df = pd.DataFrame(data)
                if output_path.endswith(".csv"):
                    df.to_csv(output_path, index=False)
                elif output_path.endswith(".xlsx"):
                    df.to_excel(output_path, index=False)
                else:
                    return {"error": "Output path must end with .csv or .xlsx"}
                return {
                    "success": True,
                    "output_path": output_path,
                    "rows": len(df),
                    "columns": len(df.columns),
                }
            except Exception as exc:
                return {"error": str(exc)}

