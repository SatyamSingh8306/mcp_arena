"""Test the friendly missing-extra ImportError on preset construction."""
from __future__ import annotations

import pytest


class TestRequireExtrasHelper:
    def test_empty_dict_is_a_noop(self):
        from mcp_arena.mcp.server import require_extras

        require_extras({})  # must not raise

    def test_satisfied_extras_are_a_noop(self):
        from mcp_arena.mcp.server import require_extras

        # `os` is always importable in the standard library.
        require_extras({"os": "core"})  # must not raise

    def test_missing_extra_raises_with_install_command(self, monkeypatch):
        from mcp_arena.mcp import server as server_mod

        monkeypatch.setattr(server_mod, "_missing_module", lambda name: name == "fake_pkg")

        with pytest.raises(ImportError) as excinfo:
            server_mod.require_extras({"fake_pkg": "fake_extra"})

        msg = str(excinfo.value)
        assert "fake_pkg" in msg
        assert 'pip install "mcp-arena[fake_extra]"' in msg

    def test_multiple_missing_extras_grouped_into_single_install(self, monkeypatch):
        from mcp_arena.mcp.server import require_extras

        with pytest.raises(ImportError) as excinfo:
            require_extras({"foo_pkg": "foo_extra", "bar_pkg": "bar_extra"})

        msg = str(excinfo.value)
        # The install command should pin the right extras
        assert "foo_extra" in msg and "bar_extra" in msg
        # And the message should mention both missing pkgs
        assert "foo_pkg" in msg and "bar_pkg" in msg


class TestPresetStamps:
    """Every preset should declare _REQUIRED_EXTRAS (possibly empty)."""

    @pytest.mark.parametrize("module", [
        "audio", "aws", "bitbucket", "browser", "cloudstorage", "confluence",
        "docker", "generic_api", "github", "gitlab", "image", "jira",
        "local_operation", "mail", "mongo", "notification", "notion", "outlook",
        "pdf", "postgres", "qrcode", "redis", "screencapture", "slack", "smtp",
        "spreadsheet", "vectordb", "video", "webscraping", "whatsapp",
    ])
    def test_preset_has_required_extras_attr(self, module):
        import importlib

        m = importlib.import_module(f"mcp_arena.presents.{module}")
        server_cls = next(
            getattr(m, name)
            for name in dir(m)
            if name.endswith("Server") and name != "BaseMCPServer"
            and isinstance(getattr(m, name), type)
        )
        assert hasattr(server_cls, "_REQUIRED_EXTRAS"), (
            f"{server_cls.__name__} is missing _REQUIRED_EXTRAS — "
            "run scripts/stamp_required_extras.py"
        )
        assert isinstance(server_cls._REQUIRED_EXTRAS, dict)


class TestMissingExtraOnConstruction:
    """Constructing a preset whose required package isn't installed should raise."""

    def test_pdf_raises_friendly_error_when_pymupdf_missing(self, monkeypatch):
        from mcp_arena.mcp import server as server_mod
        from mcp_arena.presents.pdf import PDFMCPServer

        # Pretend fitz is missing.
        monkeypatch.setattr(server_mod, "_missing_module",
                            lambda name: name in ("fitz",))

        with pytest.raises(ImportError) as excinfo:
            PDFMCPServer()

        msg = str(excinfo.value)
        assert "fitz" in msg
        assert 'pip install "mcp-arena[pdf]"' in msg

    def test_browser_raises_friendly_error_when_playwright_missing(self, monkeypatch):
        from mcp_arena.mcp import server as server_mod
        from mcp_arena.presents.browser import BrowserMCPServer

        monkeypatch.setattr(server_mod, "_missing_module",
                            lambda name: name in ("playwright",))

        with pytest.raises(ImportError) as excinfo:
            BrowserMCPServer()

        msg = str(excinfo.value)
        assert "playwright" in msg
        assert 'pip install "mcp-arena[browser]"' in msg

    def test_smtp_succeeds_with_no_extras(self, monkeypatch):
        from mcp_arena.mcp import server as server_mod
        from mcp_arena.presents.smtp import SMTPServer

        # Pretend nothing is missing.
        monkeypatch.setattr(server_mod, "_missing_module", lambda name: False)

        s = SMTPServer(smtp_host="localhost", smtp_port=587)
        assert s.name == "SMTP MCP Server"


class TestCorePresetsAreInstallableWithoutExtras:
    """The presets we promote to core deps should construct with no extras installed."""

    @pytest.fixture(autouse=True)
    def _no_missing(self, monkeypatch):
        # Pretend every Python package is installed — we only care that the
        # constructor *doesn't* ask for an extra that's no longer required.
        from mcp_arena.mcp import server as server_mod
        monkeypatch.setattr(server_mod, "_missing_module", lambda name: False)

    def test_local_operation_constructs(self):
        from mcp_arena.presents.local_operation import LocalOperationsMCPServer

        s = LocalOperationsMCPServer()
        assert s.name == "Local Operations MCP Server"

    def test_generic_api_constructs(self):
        from mcp_arena.presents.generic_api import GenericAPIMCPServer

        s = GenericAPIMCPServer()
        assert s.name == "Generic API MCP Server"

    def test_smtp_constructs(self):
        from mcp_arena.presents.smtp import SMTPServer

        s = SMTPServer(smtp_host="localhost")
        assert s.name == "SMTP MCP Server"
