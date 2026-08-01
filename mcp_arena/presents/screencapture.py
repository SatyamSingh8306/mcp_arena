"""Screen capture MCP server: screenshots and screen-size info."""
import base64
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer

try:
    import pyautogui as _pyautogui
except ImportError:
    _pyautogui = None

try:
    from PIL import Image as _PIL_Image
except ImportError:
    _PIL_Image = None


def _ensure_pyautogui():
    if _pyautogui is None:
        raise ImportError("pyautogui is required. pip install pyautogui")
    return _pyautogui


def _ensure_pil():
    if _PIL_Image is None:
        raise ImportError("Pillow is required. pip install Pillow")
    return _PIL_Image


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


class ScreenCaptureMCPServer(BaseMCPServer):
    """Screen capture MCP server (screenshots and metadata)."""
    _REQUIRED_EXTRAS = {"pyautogui": "screencapture"}

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        screenshot_format: str = "png",
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs,
    ):
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "screenshots")
        self.screenshot_format = screenshot_format
        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Screen Capture MCP Server",
            description="MCP server for screen capture and screenshots",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs,
        )

    def _register_tools(self) -> None:
        self._register_screenshot_tools()
        self._register_display_tools()

    def _register_screenshot_tools(self):
        @self.mcp_server.tool()
        def take_screenshot(
            output_path: Optional[str] = None,
            region: Optional[List[int]] = None,
        ) -> Dict[str, Any]:
            """Take a screenshot of the entire screen or a region."""
            try:
                pyautogui = _ensure_pyautogui()
                if output_path is None:
                    output_path = os.path.join(
                        self.default_output_dir,
                        f"screenshot_{_timestamp()}.{self.screenshot_format}",
                    )
                img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
                img.save(output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "region": region,
                    "size": img.size,
                }
            except Exception as exc:
                return {"error": str(exc)}

        @self.mcp_server.tool()
        def take_screenshot_base64(region: Optional[List[int]] = None) -> Dict[str, Any]:
            """Take a screenshot and return as base64."""
            try:
                pyautogui = _ensure_pyautogui()
                img = pyautogui.screenshot(region=region) if region else pyautogui.screenshot()
                buffered = io.BytesIO()
                img.save(buffered, format=self.screenshot_format.upper())
                return {
                    "success": True,
                    "format": self.screenshot_format,
                    "base64": base64.b64encode(buffered.getvalue()).decode(),
                }
            except Exception as exc:
                return {"error": str(exc)}

    def _register_display_tools(self):
        @self.mcp_server.tool()
        def get_screen_size() -> Dict[str, Any]:
            """Get the screen size (width, height)."""
            try:
                size = _ensure_pyautogui().size()
                return {"success": True, "width": size[0], "height": size[1]}
            except Exception as exc:
                return {"error": str(exc)}

