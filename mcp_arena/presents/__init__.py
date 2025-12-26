import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .github import GithubMCPServer
    from .local_operation import LocalOperationsMCPServer
    from .vectordb import VectorDBMCPServer

def __getattr__(name: str):
    """Lazy import mechanism for optional MCP servers."""
    if name == "LocalOperationsMCPServer":
        return importlib.import_module(".local_operation", __name__).LocalOperationsMCPServer
    elif name == "VectorDBMCPServer":
        return importlib.import_module(".vectordb", __name__).VectorDBMCPServer
    elif name == "GithubMCPServer":
        return importlib.import_module(".github", __name__).GithubMCPServer
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["GithubMCPServer", "LocalOperationsMCPServer", "VectorDBMCPServer"]
