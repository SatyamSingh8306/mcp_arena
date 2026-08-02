"""Lazy loader for MCP server presets.

A user importing one preset must not trigger imports for unrelated presets
(e.g. `from .github import GithubMCPServer` should not pull in `cv2` from
`browser.py`). `__getattr__` defers each module's import until the class
is actually requested.

The class-to-module map is derived from filesystem discovery at import
time, so adding a new preset requires only dropping a file in this
directory.
"""
import ast
import importlib
from pathlib import Path

_THIS_DIR = Path(__file__).parent
_SERVER_MODULES: dict[str, str] = {}


def _discover_presets() -> dict[str, str]:
    """Scan this directory for `*MCPServer` class definitions."""
    found: dict[str, str] = {}
    for py_file in _THIS_DIR.glob("*.py"):
        if py_file.name.startswith("_") or py_file.name == "base.py":
            continue
        module_stem = py_file.stem
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            # ponytail: matches both `*MCPServer` (convention) and bare
            # `*Server` (legacy — `smtp.py` predates the rename).
            if isinstance(node, ast.ClassDef) and node.name.endswith("Server"):
                found[node.name] = module_stem
                break
    return found


_SERVER_MODULES.update(_discover_presets())


def __getattr__(name: str):
    """Lazy import mechanism for MCP server presets."""
    module_stem = _SERVER_MODULES.get(name)
    if module_stem is not None:
        module = importlib.import_module(f".{module_stem}", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(_SERVER_MODULES.keys())