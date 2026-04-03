import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .github import GithubMCPServer
    from .local_operation import LocalOperationsMCPServer
    from .vectordb import VectorDBMCPServer
    from .browser import BrowserMCPServer
    from .video import VideoMCPServer
    from .image import ImageMCPServer
    from .audio import AudioMCPServer
    from .pdf import PDFMCPServer
    from .webscraping import WebScrapingMCPServer
    from .spreadsheet import SpreadsheetMCPServer
    from .cloudstorage import CloudStorageMCPServer
    from .qrcode import QRCodeMCPServer
    from .notification import NotificationMCPServer
    from .screencapture import ScreenCaptureMCPServer

# Server class mappings for lazy loading
_SERVER_MODULES = {
    "GithubMCPServer": ".github",
    "LocalOperationsMCPServer": ".local_operation",
    "VectorDBMCPServer": ".vectordb",
    "BrowserMCPServer": ".browser",
    "VideoMCPServer": ".video",
    "ImageMCPServer": ".image",
    "AudioMCPServer": ".audio",
    "PDFMCPServer": ".pdf",
    "WebScrapingMCPServer": ".webscraping",
    "SpreadsheetMCPServer": ".spreadsheet",
    "CloudStorageMCPServer": ".cloudstorage",
    "QRCodeMCPServer": ".qrcode",
    "NotificationMCPServer": ".notification",
    "ScreenCaptureMCPServer": ".screencapture",
}

def __getattr__(name: str):
    """Lazy import mechanism for optional MCP servers."""
    if name in _SERVER_MODULES:
        module = importlib.import_module(_SERVER_MODULES[name], __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = list(_SERVER_MODULES.keys())