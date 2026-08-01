"""QR code MCP server — generate, scan, base64."""
import os
import io
import base64
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import qrcode as _qrcode_lib
except ImportError:
    _qrcode_lib = None

try:
    from PIL import Image as _pil_image
except ImportError:
    _pil_image = None


def _ensure_qrcode():
    if _qrcode_lib is None:
        raise ImportError("qrcode is required. pip install 'qrcode[pil]'")
    return _qrcode_lib


class QRCodeMCPServer(BaseMCPServer):
    """QR code generation and scanning server."""
    _REQUIRED_EXTRAS = {"PIL": "qrcode", "qrcode": "qrcode"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "qrcode_output")
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)
        super().__init__(
            name="QR Code MCP Server",
            description="MCP server for QR code generation and scanning",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=True,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def generate_qrcode(
            data: str,
            output_path: Optional[str] = None,
            format: str = "png",
            size: int = 10,
            border: int = 4,
            error_correction: str = "M",
        ) -> Dict[str, Any]:
            """Generate a QR code."""
            try:
                qr = _ensure_qrcode()
                qr_obj = qr.QRCode(
                    version=1,
                    error_correction=getattr(qr.constants.ERROR_CORRECT, error_correction),
                    box_size=size,
                    border=border,
                )
                qr_obj.add_data(data)
                qr_obj.make(fit=True)
                img = qr_obj.make_image(fill_color="black", back_color="white")

                if output_path is None:
                    output_path = os.path.join(self.default_output_dir, f"qrcode.{format}")
                img.save(output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "data": data,
                    "size": size,
                    "format": format,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def generate_qrcode_base64(data: str) -> Dict[str, Any]:
            """Generate QR code as base64."""
            try:
                qr = _ensure_qrcode()
                qr_obj = qr.QRCode(
                    version=1,
                    error_correction=qr.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr_obj.add_data(data)
                qr_obj.make(fit=True)
                img = qr_obj.make_image(fill_color="black", back_color="white")

                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                return {
                    "success": True,
                    "data": data,
                    "base64": base64.b64encode(buffered.getvalue()).decode(),
                    "format": "png",
                }
            except Exception as exc:
                return {"error": str(exc)}

