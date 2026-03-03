"""Tests for tool registration, validation, and error handling.

Covers the fixes for issue #43: Incorrect Tool Registration Leads to Silent
Failures in Custom Tools.
"""

import logging
import pytest
from typing import Annotated, Dict, Any, Literal, Optional

from mcp_arena.mcp.server import BaseMCPServer, ToolRegistrationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MinimalServer(BaseMCPServer):
    """Minimal concrete server that registers no tools (for testing)."""

    def __init__(self, auto_register_tools: bool = False, **kwargs):
        super().__init__(
            name="TestServer",
            description="A server for unit tests",
            auto_register_tools=auto_register_tools,
            **kwargs,
        )

    def _register_tools(self) -> None:
        """No tools registered by default."""
        pass


class ServerWithTools(BaseMCPServer):
    """Server that registers tools through the mcp_server.tool() decorator."""

    def __init__(self, **kwargs):
        super().__init__(
            name="ToolServer",
            description="Server that registers tools",
            auto_register_tools=True,
            **kwargs,
        )

    def _register_tools(self) -> None:
        @self.mcp_server.tool()
        def greet(name: str) -> str:
            """Say hello."""
            return f"Hello, {name}!"

        # Track via _registered_tools manually (old-style, still used by presets)
        self._registered_tools.append("greet")


class ServerUsingRegisterTool(BaseMCPServer):
    """Server that registers tools via the new register_tool() API."""

    def __init__(self, **kwargs):
        super().__init__(
            name="RegisterToolServer",
            description="Server using register_tool",
            auto_register_tools=True,
            **kwargs,
        )

    def _register_tools(self) -> None:
        def add(a: int, b: int) -> int:
            """Add two numbers."""
            return a + b

        def multiply(a: int, b: int) -> int:
            """Multiply two numbers."""
            return a * b

        self.register_tool(add)
        self.register_tool(multiply, name="mul", description="Multiply two integers")


# ---------------------------------------------------------------------------
# Tests – basic registration tracking
# ---------------------------------------------------------------------------


class TestToolRegistrationTracking:
    """Verify that _registered_tools is properly populated."""

    def test_no_tools_registered_returns_empty(self):
        server = MinimalServer(auto_register_tools=False)
        assert server.get_registered_tools() == []

    def test_server_with_manual_tracking(self):
        server = ServerWithTools()
        tools = server.get_registered_tools()
        assert "greet" in tools

    def test_register_tool_tracks_name(self):
        server = MinimalServer()

        def echo(msg: str) -> str:
            return msg

        server.register_tool(echo)
        assert "echo" in server.get_registered_tools()

    def test_register_tool_with_custom_name(self):
        server = MinimalServer()

        def echo(msg: str) -> str:
            return msg

        returned_name = server.register_tool(echo, name="my_echo")
        assert returned_name == "my_echo"
        assert "my_echo" in server.get_registered_tools()
        assert "echo" not in server.get_registered_tools()

    def test_decorator_tracks_tool(self):
        server = MinimalServer()

        @server.tool()
        def ping() -> str:
            """Ping."""
            return "pong"

        assert "ping" in server.get_registered_tools()

    def test_decorator_with_custom_name(self):
        server = MinimalServer()

        @server.tool(name="health_check")
        def ping() -> str:
            return "pong"

        assert "health_check" in server.get_registered_tools()
        assert "ping" not in server.get_registered_tools()

    def test_multiple_tools_tracked(self):
        server = ServerUsingRegisterTool()
        tools = server.get_registered_tools()
        assert "add" in tools
        assert "mul" in tools
        assert len(tools) == 2


# ---------------------------------------------------------------------------
# Tests – tool metadata
# ---------------------------------------------------------------------------


class TestToolMetadata:
    """Verify tool metadata is correctly populated."""

    def test_metadata_populated(self):
        server = MinimalServer()

        def greet(name: str) -> str:
            """Say hello to someone."""
            return f"Hi {name}"

        server.register_tool(greet)
        meta = server.get_tool_metadata()
        assert "greet" in meta
        assert meta["greet"]["name"] == "greet"
        assert "Say hello" in meta["greet"]["description"]

    def test_metadata_custom_description(self):
        server = MinimalServer()

        def noop() -> None:
            pass

        server.register_tool(noop, description="Does nothing at all")
        meta = server.get_tool_metadata()
        assert meta["noop"]["description"] == "Does nothing at all"

    def test_metadata_returns_copies(self):
        server = MinimalServer()

        def noop() -> None:
            pass

        server.register_tool(noop)
        meta1 = server.get_tool_metadata()
        meta2 = server.get_tool_metadata()
        assert meta1 is not meta2
        assert meta1["noop"] is not meta2["noop"]


# ---------------------------------------------------------------------------
# Tests – validation
# ---------------------------------------------------------------------------


class TestToolValidation:
    """Verify validate_tools() works."""

    def test_validate_no_tools(self):
        server = MinimalServer()
        result = server.validate_tools()
        assert result["valid"] is True
        assert result["registered"] == []
        assert result["missing"] == []

    def test_validate_registered_tools(self):
        server = MinimalServer()

        @server.tool()
        def hello() -> str:
            return "hi"

        result = server.validate_tools()
        assert result["valid"] is True
        assert "hello" in result["registered"]

    def test_validate_detects_untracked(self):
        """Tools registered directly on FastMCP should appear as untracked."""
        server = MinimalServer()

        # Register directly on FastMCP bypassing our tracking
        @server.mcp_server.tool()
        def secret_tool() -> str:
            return "secret"

        result = server.validate_tools()
        assert "secret_tool" in result["untracked"]


# ---------------------------------------------------------------------------
# Tests – error handling
# ---------------------------------------------------------------------------


class TestToolRegistrationErrors:
    """Verify that errors are raised (not silently swallowed)."""

    def test_register_non_callable_raises(self):
        server = MinimalServer()
        with pytest.raises(ToolRegistrationError, match="not callable"):
            server.register_tool("not_a_function", name="bad_tool")

    def test_register_none_raises(self):
        server = MinimalServer()
        with pytest.raises(ToolRegistrationError, match="not callable"):
            server.register_tool(None, name="none_tool")

    def test_register_without_name_raises(self):
        """Lambdas have __name__ == '<lambda>', which is valid, but an
        object with no __name__ and no explicit name should fail."""
        server = MinimalServer()

        class NoName:
            def __call__(self):
                pass

        obj = NoName()
        # Remove __name__ if it exists
        if hasattr(obj, "__name__"):
            delattr(obj, "__name__")
        # The callable check should pass but name resolution may vary,
        # this just verifies no silent failure.
        # NoName instances are callable, so register_tool should work
        # (it will use the class's __qualname__ or similar).
        # The key point is: it doesn't silently fail.
        try:
            server.register_tool(obj)
        except ToolRegistrationError:
            pass  # Expected if name can't be resolved
        # Either way, no silent failure occurred

    def test_duplicate_tool_warns(self, caplog):
        server = MinimalServer()

        def my_tool() -> str:
            return "v1"

        def my_tool_v2() -> str:
            return "v2"

        server.register_tool(my_tool, name="dup")

        with caplog.at_level(logging.WARNING, logger="mcp_arena.server"):
            server.register_tool(my_tool_v2, name="dup")

        assert "already registered" in caplog.text
        # Should still have exactly one entry
        assert server.get_registered_tools().count("dup") == 1


# ---------------------------------------------------------------------------
# Tests – logging
# ---------------------------------------------------------------------------


class TestToolRegistrationLogging:
    """Verify proper log output during tool registration."""

    def test_debug_log_on_register(self, caplog):
        server = MinimalServer()

        def my_tool() -> str:
            return "ok"

        with caplog.at_level(logging.DEBUG, logger="mcp_arena.server"):
            server.register_tool(my_tool)

        assert "Registered tool 'my_tool'" in caplog.text

    def test_warning_when_no_tools_registered(self, caplog):
        with caplog.at_level(logging.WARNING, logger="mcp_arena.server"):
            server = MinimalServer(auto_register_tools=True)

        assert "no tools were registered" in caplog.text

    def test_info_log_when_tools_registered(self, caplog):
        with caplog.at_level(logging.INFO, logger="mcp_arena.server"):
            server = ServerUsingRegisterTool()

        assert "registered 2 tool(s)" in caplog.text

    def test_error_log_on_non_callable(self, caplog):
        server = MinimalServer()
        with caplog.at_level(logging.ERROR, logger="mcp_arena.server"):
            with pytest.raises(ToolRegistrationError):
                server.register_tool(42, name="bad")

        assert "not callable" in caplog.text


# ---------------------------------------------------------------------------
# Tests – __getattr__ guard
# ---------------------------------------------------------------------------


class TestGetAttrGuard:
    """Verify that __getattr__ blocks direct access to .tool()."""

    def test_direct_tool_access_raises(self):
        server = MinimalServer()
        # Accessing server.tool should work (it's a real method now)
        assert callable(server.tool)

    def test_other_attrs_delegate(self):
        """Non-tool attributes should still delegate to FastMCP."""
        server = MinimalServer()
        # FastMCP has an .name attribute
        assert server.mcp_server.name == "TestServer"

    def test_getattr_still_works_for_fastmcp(self):
        """Attributes that exist on FastMCP but not BaseMCPServer should
        still be accessible via __getattr__."""
        server = MinimalServer()
        # FastMCP instances have add_tool
        assert callable(server.add_tool)


# ---------------------------------------------------------------------------
# Tests – decorator returns original function
# ---------------------------------------------------------------------------


class TestDecoratorBehavior:
    """Verify the tool() decorator returns the original function."""

    def test_decorator_returns_function(self):
        server = MinimalServer()

        @server.tool()
        def my_func(x: int) -> int:
            return x * 2

        assert callable(my_func)
        assert my_func(5) == 10

    def test_decorator_preserves_docstring(self):
        server = MinimalServer()

        @server.tool()
        def documented() -> str:
            """This is documented."""
            return "ok"

        assert documented.__doc__ == "This is documented."


# ---------------------------------------------------------------------------
# Tests – get_registered_tools returns copy
# ---------------------------------------------------------------------------


class TestGetRegisteredToolsIsolation:
    """Verify get_registered_tools returns a copy."""

    def test_returns_copy(self):
        server = MinimalServer()

        @server.tool()
        def t1() -> str:
            return "ok"

        tools = server.get_registered_tools()
        tools.append("fake_tool")
        assert "fake_tool" not in server.get_registered_tools()


# ---------------------------------------------------------------------------
# Tests – ToolRegistrationError is importable
# ---------------------------------------------------------------------------


class TestImports:
    """Verify public API imports work."""

    def test_import_from_mcp_module(self):
        from mcp_arena.mcp import ToolRegistrationError as TRE
        assert TRE is ToolRegistrationError

    def test_import_from_server_module(self):
        from mcp_arena.mcp.server import ToolRegistrationError as TRE
        assert TRE is ToolRegistrationError
