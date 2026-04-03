"""
Screen Capture MCP Server
A comprehensive screen capture server for taking screenshots and screen recordings.
"""
from typing import Optional, Dict, Any, List, Literal, Union
from dataclasses import dataclass, asdict
import os
import base64
from pathlib import Path
from mcp_arena.mcp.server import BaseMCPServer

# Lazy imports
_pyautogui = None


def _import_pyautogui():
    """Lazily import PyAutoGUI."""
    global _pyautogui
    if _pyautogui is None:
        try:
            import pyautogui
            _pyautogui = pyautogui
        except ImportError:
            raise ImportError(
                "PyAutoGUI is required for screen capture. "
                "Install it with: pip install pyautogui"
            )
    return _pyautogui


class ScreenCaptureMCPServer(BaseMCPServer):
    """Screen Capture MCP Server for screenshots and screen recording."""

    def __init__(
        self,
        default_output_dir: Optional[str] = None,
        screenshot_format: str = "png",
        screenshot_quality: int = 9,
        host: str = "127.0.0.1",
        port: int = 8000,
        transport: Literal['stdio', 'sse', 'streamable-http'] = "stdio",
        debug: bool = False,
        auto_register_tools: bool = True,
        **base_kwargs
    ):
        """Initialize Screen Capture MCP Server."""
        self.default_output_dir = default_output_dir or os.path.join(os.getcwd(), "screenshots")
        self.screenshot_format = screenshot_format
        self.screenshot_quality = screenshot_quality

        Path(self.default_output_dir).mkdir(parents=True, exist_ok=True)

        super().__init__(
            name="Screen Capture MCP Server",
            description="MCP server for screen capture, screenshots, and screen recording",
            host=host,
            port=port,
            transport=transport,
            debug=debug,
            auto_register_tools=auto_register_tools,
            **base_kwargs
        )

    def _register_tools(self) -> None:
        """Register all screen capture tools."""
        self._register_screenshot_tools()
        self._register_display_tools()

    def _register_screenshot_tools(self):
        """Register screenshot tools."""

        @self.mcp_server.tool()
        def take_screenshot(
            output_path: Optional[str] = None,
            region: Optional[List[int]] = None
        ) -> Dict[str, Any]:
            """Take a screenshot of the entire screen or a region."""
            try:
                pyautogui = _import_pyautogui()

                if output_path is None:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(self.default_output_dir, f"screenshot_{timestamp}.{self.screenshot_format}")

                if region:
                    # region is [left, top, width, height]
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()

                screenshot.save(output_path)

                return {
                    "success": True,
                    "output_path": output_path,
                    "region": region,
                    "size": screenshot.size
                }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def take_region_screenshot(
            left: int,
            top: int,
            width: int,
            height: int,
            output_path: Optional[str] = None
        ) -> Dict[str, Any]:
            """Take a screenshot of a specific screen region."""
            try:
                pyautogui = _import_pyautogui()

                if output_path is None:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(self.default_output_dir, f"region_{timestamp}.{self.screenshot_format}")

                screenshot = pyautogui.screenshot(region=(left, top, width, height))
                screenshot.save(output_path)

                return {
                    "success": True,
                    "output_path": output_path,
                    "region": {"left": left, "top": top, "width": width, "height": height}
                }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def take_screenshot_base64(
            region: Optional[List[int]] = None
        ) -> Dict[str, Any]:
            """Take a screenshot and return as base64 encoded string."""
            try:
                pyautogui = _import_pyautogui()
                import io
                from PIL import Image

                if region:
                    screenshot = pyautogui.screenshot(region=region)
                else:
                    screenshot = pyautogui.screenshot()

                buffered = io.BytesIO()
                screenshot.save(buffered, format=self.screenshot_format.upper())
                img_str = base64.b64encode(buffered.getvalue()).decode()

                return {
                    "success": True,
                    "format": self.screenshot_format,
                    "base64": img_str
                }

            except Exception as e:
                return {"error": str(e)}

    def _register_display_tools(self):
        """Register display information tools."""

        @self.mcp_server.tool()
        def get_screen_size() -> Dict[str, Any]:
            """Get the screen size (width, height)."""
            try:
                pyautogui = _import_pyautogui()
                size = pyautogui.size()

                return {
                    "success": True,
                    "width": size[0],
                    "height": size[1]
                }

            except Exception as e:
                return {"error": str(e)}

        @self.mcp_server.tool()
        def get_screenshot_objects_count() -> Dict[str, Any]:
            """Get the number of screenshots in the output directory."""
            try:
                if not os.path.exists(self.default_output_dir):
                    return {"success": True, "count": 0, "path": self.default_output_dir}

                files = [f for f in os.listdir(self.default_output_dir)
                        if f.endswith(('.png', '.jpg', '.jpeg'))]

                return {
                    "success": True,
                    "count": len(files),
                    "path": self.default_output_dir,
                    "files": files
                }

            except Exception as e:
                return {"error": str(e)}


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Screen Capture MCP Server")
    parser.add_argument("--output-dir", type=str, default=None)
    parser.add_argument("--screenshot-format", choices=["png", "jpg"], default="png")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--debug", action="store_true")

    args = parser.parse_args()

    server = ScreenCaptureMCPServer(
        default_output_dir=args.output_dir,
        screenshot_format=args.screenshot_format,
        transport=args.transport,
        host=args.host,
        port=args.port,
        debug=args.debug
    )

    print("Starting Screen Capture MCP Server")
    server.run()


if __name__ == "__main__":
    main()
