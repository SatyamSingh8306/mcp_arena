"""
QR Code MCP Server
A comprehensive QR code generation and scanning server using qrcode and opencv.
"""
from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict
import os
import io
import base64
from pathlib import Path
from mcp_arena.mcp.server import BaseMCPServer

# Lazy imports
_qrcode = None
_cv2 = None
_pil = None

def _import_qrcode():
    """Lazily import qrcode."""
    global _qrcode
    if _qrcode is None:
        try:
            import qrcode
            _qrcode = qrcode
        except ImportError:
            raise ImportError(
                "qrcode is required for QRCodeMCPServer. "
                "Install it with: pip install qrcode[pil]"
            )
    return _qrcode

def _import_pil():
    """Lazily import PIL."""
    global _pil
    if _pil is None:
        try:
            from PIL import Image
            _pil = Image
        except ImportError:
            raise ImportError(
                "PIL is required for QR code operations. "
                "Install it with: pip install Pillow"
            )
    return _pil


class QRCodeErrorCorrection(str, str):
    """QR code error correction levels."""
    LOW = "L"
    MEDIUM = "M"
    QUARTILE = "Q"
    HIGH = "H"


class QRCodeFormat(str, str):
    """QR code output formats."""
    PNG = "png"
    JPEG = "jpeg"
    SVG = "svg"
    BASE64 = "base64"


@dataclass
class QRCodeInfo:
    """QR code information."""
    data: str
    version: int
    error_correction: str
    box_size: int
    border: int
    size: int
    format: str


class QRCodeMCPServer(BaseMCPServer):
    """QR Code MCP Server for generation and scanning."""

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        **base_kwargs):

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
            **base_kwargs
        )

    def _register_tools(self) -> None:
        """Register QR code tools."""

        @self.mcp_server.tool()
        def generate_qrcode(
            data: str,
            output_path: Optional[str] = None,
            format: str = "png",
            size: int = 10,
            border: int = 4,
            error_correction: str = "M"
        ) -> Dict[str, Any]:
            """Generate QR code."""
            try:
                qr = _import_qrcode()
                pil = _import_pil()

                qr = qr.QRCode(
                    version=1,
                    error_correction=getattr(qr.constants.ERROR_CORRECT, error_correction),
                    box_size=size,
                    border=border,
                )
                qr.add_data(data)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                if output_path is None:
                    base_name = "qrcode"
                    output_path = os.path.join(self.default_output_dir, f"{base_name}.{format}")

                img.save(output_path)

                return {
                    "success": True,
                    "output_path": output_path,
                    "data": data,
                    "size": size,
                    "format": format
                }
            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def generate_qrcode_base64(data: str) -> Dict[str, Any]:
            """Generate QR code as base64."""
            try:
                qr = _import_qrcode()
                pil = _import_pil()

                qr = qr.QRCode(
                    version=1,
                    error_correction=qr.constants.ERROR_CORRECT_M,
                    box_size=10,
                    border=4,
                )
                qr.add_data(data)
                qr.make(fit=True)

                img = qr.make_image(fill_color="black", back_color="white")

                buffered = io.BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return {
                    "success": True,
                    "data": data,
                    "base64": img_str,
                    "format": "png"
                }
            except Exception as e:
                return {"error": str(e)}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="QR Code MCP Server")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    server = QRCodeMCPServer(
        default_output_dir=args.output_dir,
        transport=args.transport,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    print("Starting QR Code MCP Server")
    server.run()

if __name__ == "__main__":
    main()