"""
Tests for the MCP server dashboard and metrics system.

Covers:
- MetricsCollector: recording, querying, thread-safety, reset
- DashboardServer: start/stop lifecycle, HTTP endpoints
- BaseMCPServer integration: enable_dashboard, get_metrics, start/stop dashboard
"""

import json
import time
import threading
import urllib.request
import urllib.error
import pytest

from mcp_arena.mcp.metrics import MetricsCollector
from mcp_arena.mcp.dashboard import DashboardServer, DASHBOARD_HTML


# =========================================================================
# MetricsCollector tests
# =========================================================================


class TestMetricsCollector:
    """Tests for the in-memory MetricsCollector."""

    def test_initial_state(self):
        mc = MetricsCollector(server_name="Test Server")
        m = mc.get_metrics()
        assert m["server_name"] == "Test Server"
        assert m["total_requests"] == 0
        assert m["total_errors"] == 0
        assert m["active_connections"] == 0
        assert m["tools_registered"] == 0
        assert m["error_rate"] == 0.0

    def test_uptime_increases(self):
        mc = MetricsCollector()
        time.sleep(0.05)
        assert mc.uptime >= 0.04

    def test_uptime_formatted(self):
        mc = MetricsCollector()
        fmt = mc.uptime_formatted
        assert isinstance(fmt, str)
        assert "s" in fmt

    def test_record_request_increments_counts(self):
        mc = MetricsCollector()
        mc.record_request("tool_a")
        mc.record_request("tool_a")
        mc.record_request("tool_b")
        m = mc.get_metrics()
        assert m["total_requests"] == 3
        assert m["tools"]["tool_a"]["calls"] == 2
        assert m["tools"]["tool_b"]["calls"] == 1

    def test_record_request_with_latency(self):
        mc = MetricsCollector()
        mc.record_request("tool_x", latency=0.25)
        mc.record_request("tool_x", latency=0.75)
        m = mc.get_metrics()
        assert m["tools"]["tool_x"]["avg_latency_s"] == pytest.approx(0.5, abs=0.01)

    def test_record_request_failure(self):
        mc = MetricsCollector()
        mc.record_request("tool_fail", success=False)
        m = mc.get_metrics()
        assert m["total_errors"] == 1
        assert m["tools"]["tool_fail"]["errors"] == 1
        assert m["error_rate"] == 1.0

    def test_record_error_convenience(self):
        mc = MetricsCollector()
        mc.record_error("tool_err", "something broke", latency=0.1)
        m = mc.get_metrics()
        assert m["total_errors"] == 1
        assert m["tools"]["tool_err"]["errors"] == 1
        recent = m["recent_requests"]
        assert len(recent) == 1
        assert recent[0]["metadata"]["error"] == "something broke"

    def test_active_connections(self):
        mc = MetricsCollector()
        mc.increment_connections()
        mc.increment_connections()
        assert mc.get_metrics()["active_connections"] == 2
        mc.decrement_connections()
        assert mc.get_metrics()["active_connections"] == 1
        mc.decrement_connections()
        mc.decrement_connections()  # should not go below 0
        assert mc.get_metrics()["active_connections"] == 0

    def test_recent_requests_capped(self):
        mc = MetricsCollector(max_recent=5)
        for i in range(10):
            mc.record_request(f"tool_{i}")
        m = mc.get_metrics()
        # get_metrics returns last 20 or less, but internal log capped at 5
        assert len(m["recent_requests"]) <= 5

    def test_error_rate_calculation(self):
        mc = MetricsCollector()
        mc.record_request("ok", success=True)
        mc.record_request("fail", success=False)
        mc.record_request("ok2", success=True)
        m = mc.get_metrics()
        assert m["error_rate"] == pytest.approx(1 / 3, abs=0.01)

    def test_get_tool_summary_sorted(self):
        mc = MetricsCollector()
        mc.record_request("rare")
        mc.record_request("popular")
        mc.record_request("popular")
        mc.record_request("popular")
        summary = mc.get_tool_summary()
        assert summary[0]["tool"] == "popular"
        assert summary[0]["calls"] == 3
        assert summary[1]["tool"] == "rare"

    def test_reset(self):
        mc = MetricsCollector(server_name="Resettable")
        mc.record_request("x")
        mc.record_error("y", "err")
        mc.increment_connections()
        mc.reset()
        m = mc.get_metrics()
        assert m["total_requests"] == 0
        assert m["total_errors"] == 0
        assert m["active_connections"] == 0
        assert m["tools"] == {}
        assert m["server_name"] == "Resettable"  # name preserved

    def test_thread_safety(self):
        mc = MetricsCollector()
        n = 200

        def writer():
            for _ in range(n):
                mc.record_request("parallel_tool", latency=0.001)

        threads = [threading.Thread(target=writer) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        m = mc.get_metrics()
        assert m["total_requests"] == 4 * n

    def test_metadata_in_recent(self):
        mc = MetricsCollector()
        mc.record_request("tool_meta", metadata={"user": "alice"})
        recent = mc.get_metrics()["recent_requests"]
        assert recent[-1]["metadata"]["user"] == "alice"


# =========================================================================
# DashboardServer tests
# =========================================================================


def _get_free_port():
    """Find a free port for testing."""
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class TestDashboardServer:
    """Tests for the DashboardServer HTTP lifecycle and endpoints."""

    def test_start_and_stop(self):
        port = _get_free_port()
        mc = MetricsCollector("Test")
        dash = DashboardServer(mc, port=port)
        assert not dash.is_running
        dash.start()
        assert dash.is_running
        dash.stop()
        assert not dash.is_running

    def test_double_start_is_safe(self):
        port = _get_free_port()
        mc = MetricsCollector("Test")
        dash = DashboardServer(mc, port=port)
        dash.start()
        dash.start()  # must not raise
        assert dash.is_running
        dash.stop()

    def test_url_properties(self):
        port = _get_free_port()
        mc = MetricsCollector("Test")
        dash = DashboardServer(mc, port=port)
        assert str(port) in dash.url
        assert str(port) in dash.metrics_url
        assert "/dashboard" in dash.url
        assert "/metrics" in dash.metrics_url

    def test_metrics_endpoint_returns_json(self):
        port = _get_free_port()
        mc = MetricsCollector("HTTP Test")
        mc.record_request("hello_tool")
        dash = DashboardServer(mc, port=port, server_name="HTTP Test")
        dash.start()
        time.sleep(0.2)  # let server spin up

        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3)
            assert resp.status == 200
            data = json.loads(resp.read().decode())
            assert data["server_name"] == "HTTP Test"
            assert data["total_requests"] == 1
            assert "hello_tool" in data["tools"]
        finally:
            dash.stop()

    def test_dashboard_endpoint_returns_html(self):
        port = _get_free_port()
        mc = MetricsCollector("Dash Test")
        dash = DashboardServer(mc, port=port, server_name="Dash Test")
        dash.start()
        time.sleep(0.2)

        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/dashboard", timeout=3)
            assert resp.status == 200
            html = resp.read().decode()
            assert "Dash Test" in html
            assert "/metrics" in html
        finally:
            dash.stop()

    def test_root_serves_dashboard(self):
        port = _get_free_port()
        mc = MetricsCollector()
        dash = DashboardServer(mc, port=port, server_name="Root")
        dash.start()
        time.sleep(0.2)

        try:
            resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3)
            assert resp.status == 200
            html = resp.read().decode()
            assert "Root" in html
        finally:
            dash.stop()

    def test_404_for_unknown_path(self):
        port = _get_free_port()
        mc = MetricsCollector()
        dash = DashboardServer(mc, port=port)
        dash.start()
        time.sleep(0.2)

        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nonexistent", timeout=3)
            assert False, "Should have raised"
        except urllib.error.HTTPError as e:
            assert e.code == 404
        finally:
            dash.stop()


# =========================================================================
# BaseMCPServer integration tests
# =========================================================================


class TestBaseMCPServerMetrics:
    """Test that metrics and dashboard are wired into BaseMCPServer."""

    def test_server_has_metrics(self):
        from mcp_arena.mcp.server import BaseMCPServer

        # BaseMCPServer is abstract so we need a minimal concrete subclass
        class _Dummy(BaseMCPServer):
            def _register_tools(self):
                pass

        srv = _Dummy(name="Dummy", description="test", auto_register_tools=False)
        assert isinstance(srv.metrics, MetricsCollector)
        m = srv.get_metrics()
        assert m["server_name"] == "Dummy"

    def test_server_start_stop_dashboard(self):
        from mcp_arena.mcp.server import BaseMCPServer

        class _Dummy(BaseMCPServer):
            def _register_tools(self):
                pass

        port = _get_free_port()
        srv = _Dummy(
            name="DashTest",
            description="test",
            auto_register_tools=False,
            enable_dashboard=False,
            dashboard_port=port,
        )
        url = srv.start_dashboard(port=port)
        assert "dashboard" in url
        time.sleep(0.2)

        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3)
        data = json.loads(resp.read().decode())
        assert data["server_name"] == "DashTest"

        srv.stop_dashboard()

    def test_enable_dashboard_flag(self):
        from mcp_arena.mcp.server import BaseMCPServer

        class _Dummy(BaseMCPServer):
            def _register_tools(self):
                pass

        port = _get_free_port()
        srv = _Dummy(
            name="AutoDash",
            description="test",
            auto_register_tools=False,
            enable_dashboard=True,
            dashboard_port=port,
        )
        # Dashboard is not started until run() is called.
        # We can start it manually and verify it works.
        srv.start_dashboard()
        time.sleep(0.2)

        resp = urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics", timeout=3)
        assert resp.status == 200
        srv.stop_dashboard()


# =========================================================================
# DASHBOARD_HTML template tests
# =========================================================================


class TestDashboardHTML:
    """Sanity checks on the embedded HTML template."""

    def test_template_contains_placeholders(self):
        assert "{server_name}" in DASHBOARD_HTML

    def test_template_contains_metrics_fetch(self):
        assert "/metrics" in DASHBOARD_HTML

    def test_template_has_stat_ids(self):
        for stat_id in ("uptime", "totalReqs", "activeConns", "totalErrors", "errorRate", "toolCount"):
            assert stat_id in DASHBOARD_HTML

    def test_template_renders_server_name(self):
        html = DASHBOARD_HTML.replace("{server_name}", "My Cool Server")
        assert "My Cool Server" in html
        assert "{server_name}" not in html
