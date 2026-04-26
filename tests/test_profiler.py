"""Tests for the Agent Performance Profiler (issue #29).

Covers AgentProfiler, ToolProfiler, MemoryProfiler, and the
profile_agent decorator.
"""

import time
import pytest
from mcp_arena.agent.profiler import (
    AgentProfiler,
    ExecutionMetric,
    ToolProfiler,
    ToolMetric,
    MemoryProfiler,
    MemorySnapshot,
    profile_agent,
)


# ══════════════════════════════════════════════════════════════════════════════
# ExecutionMetric
# ══════════════════════════════════════════════════════════════════════════════


class TestExecutionMetric:
    def test_default_values(self):
        m = ExecutionMetric()
        assert m.agent_name == ""
        assert m.execution_time == 0.0
        assert m.success is True
        assert m.error is None
        assert m.response_length is None
        assert m.tokens_used is None
        assert m.metadata == {}

    def test_custom_values(self):
        m = ExecutionMetric(agent_name="a", execution_time=1.5, success=False, error="e")
        assert m.agent_name == "a"
        assert m.success is False

    def test_to_dict(self):
        d = ExecutionMetric(agent_name="x").to_dict()
        assert isinstance(d, dict)
        assert d["agent_name"] == "x"


# ══════════════════════════════════════════════════════════════════════════════
# ToolMetric
# ══════════════════════════════════════════════════════════════════════════════


class TestToolMetric:
    def test_default_values(self):
        m = ToolMetric()
        assert m.tool_name == ""
        assert m.execution_time == 0.0
        assert m.success is True
        assert m.input_size is None
        assert m.output_size is None

    def test_to_dict(self):
        d = ToolMetric(tool_name="calc").to_dict()
        assert d["tool_name"] == "calc"


# ══════════════════════════════════════════════════════════════════════════════
# MemorySnapshot
# ══════════════════════════════════════════════════════════════════════════════


class TestMemorySnapshot:
    def test_default_values(self):
        s = MemorySnapshot()
        assert s.label == ""
        assert s.peak_memory_bytes == 0
        assert s.current_memory_mb == 0.0

    def test_to_dict(self):
        d = MemorySnapshot(label="test").to_dict()
        assert d["label"] == "test"


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — context manager
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentProfilerContext:
    def test_basic_profiling(self):
        p = AgentProfiler()
        with p.profile("agent-a"):
            time.sleep(0.01)
        assert p.total_executions == 1
        last = p.get_last_metric()
        assert last["agent_name"] == "agent-a"
        assert last["success"] is True
        assert last["execution_time"] > 0

    def test_failure_captured(self):
        p = AgentProfiler()
        with pytest.raises(ValueError):
            with p.profile("fail"):
                raise ValueError("boom")
        last = p.get_last_metric()
        assert last["success"] is False
        assert last["error"] == "boom"

    def test_metadata(self):
        p = AgentProfiler()
        with p.profile("m", model="gpt-4"):
            pass
        assert p.get_last_metric()["metadata"]["model"] == "gpt-4"

    def test_timestamp(self):
        p = AgentProfiler()
        with p.profile("t"):
            pass
        assert "T" in p.get_last_metric()["timestamp"]

    def test_disabled(self):
        p = AgentProfiler(enabled=False)
        with p.profile("d"):
            pass
        assert p.total_executions == 0


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — start/stop
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentProfilerStartStop:
    def test_basic(self):
        p = AgentProfiler()
        p.start("x")
        time.sleep(0.01)
        metric = p.stop()
        assert metric.agent_name == "x"
        assert metric.execution_time > 0

    def test_stop_failure(self):
        p = AgentProfiler()
        p.start("y")
        metric = p.stop(success=False, error="bad")
        assert metric.success is False
        assert metric.error == "bad"

    def test_stop_without_start(self):
        p = AgentProfiler()
        with pytest.raises(RuntimeError, match="not started"):
            p.stop()


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — record_result
# ══════════════════════════════════════════════════════════════════════════════


class TestRecordResult:
    def test_string_result(self):
        p = AgentProfiler()
        with p.profile("r"):
            p.record_result("Hello!")
        assert p.get_last_metric()["response_length"] == 6

    def test_dict_result(self):
        p = AgentProfiler()
        with p.profile("d"):
            p.record_result({"k": "v"})
        assert p.get_last_metric()["response_length"] > 0

    def test_explicit_tokens(self):
        p = AgentProfiler()
        with p.profile("tok"):
            p.record_result("r", tokens_used=512, prompt_tokens=100, completion_tokens=412)
        last = p.get_last_metric()
        assert last["tokens_used"] == 512
        assert last["prompt_tokens"] == 100
        assert last["completion_tokens"] == 412

    def test_no_metric_safe(self):
        p = AgentProfiler()
        p.record_result("orphan")  # should not raise


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — querying & summary
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentSummary:
    def test_empty(self):
        p = AgentProfiler()
        s = p.get_summary()
        assert s["total_executions"] == 0

    def test_with_data(self):
        p = AgentProfiler()
        with p.profile("a"):
            p.record_result("ok", tokens_used=10)
        with p.profile("b"):
            p.record_result("fine", tokens_used=20)
        s = p.get_summary()
        assert s["total_executions"] == 2
        assert s["success_rate"] == 1.0
        assert s["total_tokens_used"] == 30

    def test_filtered(self):
        p = AgentProfiler()
        with p.profile("alpha"):
            pass
        with p.profile("beta"):
            pass
        with p.profile("alpha"):
            pass
        s = p.get_summary(agent_name="alpha")
        assert s["total_executions"] == 2

    def test_failures_in_summary(self):
        p = AgentProfiler()
        with p.profile("ok"):
            pass
        try:
            with p.profile("fail"):
                raise RuntimeError("e")
        except RuntimeError:
            pass
        s = p.get_summary()
        assert s["successful"] == 1
        assert s["failed"] == 1
        assert s["success_rate"] == 0.5

    def test_avg_response_length(self):
        p = AgentProfiler()
        with p.profile("a"):
            p.record_result("ab")
        with p.profile("a"):
            p.record_result("abcd")
        assert p.get_summary()["avg_response_length"] == 3.0


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — compare_agents
# ══════════════════════════════════════════════════════════════════════════════


class TestCompareAgents:
    def test_compare(self):
        p = AgentProfiler()
        with p.profile("react"):
            time.sleep(0.01)
        with p.profile("reflection"):
            time.sleep(0.02)
        with p.profile("planning"):
            pass
        cmp = p.compare_agents()
        assert set(cmp.keys()) == {"react", "reflection", "planning"}
        for v in cmp.values():
            assert v["total_executions"] == 1

    def test_compare_empty(self):
        assert AgentProfiler().compare_agents() == {}


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — clear/reset/repr
# ══════════════════════════════════════════════════════════════════════════════


class TestAgentProfilerMisc:
    def test_clear(self):
        p = AgentProfiler()
        with p.profile("t"):
            pass
        p.clear()
        assert p.total_executions == 0

    def test_reset(self):
        p = AgentProfiler()
        with p.profile("t"):
            pass
        p.reset()
        assert p.total_executions == 0

    def test_repr(self):
        r = repr(AgentProfiler())
        assert "AgentProfiler" in r
        assert "enabled=True" in r


# ══════════════════════════════════════════════════════════════════════════════
# AgentProfiler — token extraction
# ══════════════════════════════════════════════════════════════════════════════


class TestTokenExtraction:
    def test_usage_metadata_dict(self):
        class Resp:
            usage_metadata = {"total_tokens": 150}
        p = AgentProfiler()
        with p.profile("t"):
            p.record_result(Resp())
        assert p.get_last_metric()["tokens_used"] == 150

    def test_usage_attr(self):
        class U:
            total_tokens = 200
        class Resp:
            usage = U()
        p = AgentProfiler()
        with p.profile("t"):
            p.record_result(Resp())
        assert p.get_last_metric()["tokens_used"] == 200

    def test_response_metadata(self):
        class Resp:
            response_metadata = {"token_usage": {"total_tokens": 300}}
        p = AgentProfiler()
        with p.profile("t"):
            p.record_result(Resp())
        assert p.get_last_metric()["tokens_used"] == 300

    def test_no_token_info(self):
        p = AgentProfiler()
        with p.profile("t"):
            p.record_result("plain text")
        assert p.get_last_metric()["tokens_used"] is None

    def test_explicit_overrides_auto(self):
        class Resp:
            usage_metadata = {"total_tokens": 100}
        p = AgentProfiler()
        with p.profile("t"):
            p.record_result(Resp(), tokens_used=999)
        assert p.get_last_metric()["tokens_used"] == 999


# ══════════════════════════════════════════════════════════════════════════════
# ToolProfiler
# ══════════════════════════════════════════════════════════════════════════════


class TestToolProfiler:
    def test_basic_profiling(self):
        tp = ToolProfiler()
        with tp.profile_tool("calculator"):
            time.sleep(0.01)
        assert tp.total_calls == 1
        m = tp.get_metrics()[0]
        assert m["tool_name"] == "calculator"
        assert m["success"] is True
        assert m["execution_time"] > 0

    def test_failure(self):
        tp = ToolProfiler()
        with pytest.raises(ZeroDivisionError):
            with tp.profile_tool("bad-tool"):
                1 / 0
        m = tp.get_metrics()[0]
        assert m["success"] is False
        assert "division by zero" in m["error"]

    def test_record_io(self):
        tp = ToolProfiler()
        with tp.profile_tool("io-tool"):
            tp.record_io(input_data="hello", output_data="world!")
        m = tp.get_metrics()[0]
        assert m["input_size"] == 5
        assert m["output_size"] == 6

    def test_record_io_safe_no_metric(self):
        tp = ToolProfiler()
        tp.record_io(input_data="x")  # should not raise

    def test_filter_by_tool_name(self):
        tp = ToolProfiler()
        with tp.profile_tool("a"):
            pass
        with tp.profile_tool("b"):
            pass
        with tp.profile_tool("a"):
            pass
        assert len(tp.get_metrics(tool_name="a")) == 2

    def test_disabled(self):
        tp = ToolProfiler(enabled=False)
        with tp.profile_tool("x"):
            pass
        assert tp.total_calls == 0


class TestToolSummary:
    def test_empty(self):
        tp = ToolProfiler()
        s = tp.get_tool_summary()
        assert s["total_calls"] == 0

    def test_with_data(self):
        tp = ToolProfiler()
        with tp.profile_tool("a"):
            pass
        with tp.profile_tool("b"):
            pass
        s = tp.get_tool_summary()
        assert s["total_calls"] == 2
        assert s["success_rate"] == 1.0

    def test_filtered(self):
        tp = ToolProfiler()
        with tp.profile_tool("target"):
            pass
        with tp.profile_tool("other"):
            pass
        s = tp.get_tool_summary(tool_name="target")
        assert s["total_calls"] == 1
        assert s["tools"] == ["target"]


class TestToolBottlenecks:
    def test_bottlenecks_sorted_by_avg_time(self):
        tp = ToolProfiler()
        with tp.profile_tool("fast"):
            pass
        with tp.profile_tool("slow"):
            time.sleep(0.03)

        bottlenecks = tp.get_bottlenecks()
        assert len(bottlenecks) == 2
        assert bottlenecks[0]["tool_name"] == "slow"
        assert bottlenecks[0]["avg_execution_time"] > bottlenecks[1]["avg_execution_time"]

    def test_bottlenecks_top_n(self):
        tp = ToolProfiler()
        for i in range(10):
            with tp.profile_tool(f"tool-{i}"):
                pass
        assert len(tp.get_bottlenecks(top_n=3)) == 3

    def test_bottlenecks_empty(self):
        tp = ToolProfiler()
        assert tp.get_bottlenecks() == []


class TestToolFailureReport:
    def test_failure_report(self):
        tp = ToolProfiler()
        with tp.profile_tool("reliable"):
            pass
        try:
            with tp.profile_tool("flaky"):
                raise RuntimeError("err")
        except RuntimeError:
            pass

        report = tp.get_failure_report()
        flaky = [r for r in report if r["tool_name"] == "flaky"][0]
        reliable = [r for r in report if r["tool_name"] == "reliable"][0]
        assert flaky["failure_rate"] == 1.0
        assert reliable["failure_rate"] == 0.0
        # flaky should be first (highest failure rate)
        assert report[0]["tool_name"] == "flaky"

    def test_failure_report_empty(self):
        assert ToolProfiler().get_failure_report() == []


class TestToolProfilerMisc:
    def test_clear(self):
        tp = ToolProfiler()
        with tp.profile_tool("x"):
            pass
        tp.clear()
        assert tp.total_calls == 0

    def test_repr(self):
        r = repr(ToolProfiler())
        assert "ToolProfiler" in r


# ══════════════════════════════════════════════════════════════════════════════
# MemoryProfiler
# ══════════════════════════════════════════════════════════════════════════════


class TestMemoryProfiler:
    def test_basic_tracking(self):
        mp = MemoryProfiler()
        with mp.track("test-agent"):
            _ = [i for i in range(1000)]
        assert mp.total_snapshots == 1
        snap = mp.get_last_snapshot()
        assert snap is not None
        assert snap["label"] == "test-agent"
        assert snap["peak_memory_bytes"] > 0
        assert snap["peak_memory_mb"] > 0

    def test_current_memory_recorded(self):
        mp = MemoryProfiler()
        with mp.track("mem"):
            data = bytearray(1024 * 100)  # ~100KB
        snap = mp.get_last_snapshot()
        assert snap["current_memory_bytes"] > 0

    def test_disabled(self):
        mp = MemoryProfiler(enabled=False)
        with mp.track("x"):
            pass
        assert mp.total_snapshots == 0

    def test_filter_by_label(self):
        mp = MemoryProfiler()
        with mp.track("alpha"):
            pass
        with mp.track("beta"):
            pass
        with mp.track("alpha"):
            pass
        assert len(mp.get_snapshots(label="alpha")) == 2


class TestMemorySummary:
    def test_empty(self):
        mp = MemoryProfiler()
        s = mp.get_summary()
        assert s["total_snapshots"] == 0

    def test_with_data(self):
        mp = MemoryProfiler()
        with mp.track("a"):
            _ = bytearray(1024 * 50)
        with mp.track("b"):
            _ = bytearray(1024 * 100)
        s = mp.get_summary()
        assert s["total_snapshots"] == 2
        assert s["avg_peak_memory_mb"] > 0
        assert s["max_peak_memory_mb"] >= s["avg_peak_memory_mb"]

    def test_filtered(self):
        mp = MemoryProfiler()
        with mp.track("target"):
            pass
        with mp.track("other"):
            pass
        s = mp.get_summary(label="target")
        assert s["total_snapshots"] == 1
        assert s["labels"] == ["target"]


class TestMemoryCompare:
    def test_compare_labels(self):
        mp = MemoryProfiler()
        with mp.track("react"):
            _ = bytearray(1024 * 10)
        with mp.track("reflection"):
            _ = bytearray(1024 * 50)
        cmp = mp.compare_labels()
        assert "react" in cmp
        assert "reflection" in cmp

    def test_compare_empty(self):
        assert MemoryProfiler().compare_labels() == {}


class TestMemoryProfilerMisc:
    def test_clear(self):
        mp = MemoryProfiler()
        with mp.track("x"):
            pass
        mp.clear()
        assert mp.total_snapshots == 0

    def test_repr(self):
        r = repr(MemoryProfiler())
        assert "MemoryProfiler" in r


# ══════════════════════════════════════════════════════════════════════════════
# profile_agent decorator
# ══════════════════════════════════════════════════════════════════════════════


class TestProfileAgentDecorator:
    def test_basic(self):
        p = AgentProfiler()

        @profile_agent(p, agent_name="decorated")
        def my_task():
            return "result"

        assert my_task() == "result"
        assert p.total_executions == 1
        last = p.get_last_metric()
        assert last["agent_name"] == "decorated"
        assert last["response_length"] == len("result")

    def test_uses_func_name(self):
        p = AgentProfiler()

        @profile_agent(p)
        def my_func():
            return "ok"

        my_func()
        assert p.get_last_metric()["agent_name"] == "my_func"

    def test_captures_exception(self):
        p = AgentProfiler()

        @profile_agent(p, agent_name="err")
        def failing():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            failing()
        assert p.get_last_metric()["success"] is False

    def test_multiple_calls(self):
        p = AgentProfiler()

        @profile_agent(p, agent_name="multi")
        def task():
            return "x"

        for _ in range(3):
            task()
        assert p.total_executions == 3


# ══════════════════════════════════════════════════════════════════════════════
# Integration: combining all three profilers
# ══════════════════════════════════════════════════════════════════════════════


class TestIntegration:
    """Simulate a realistic workflow using all three profilers together."""

    def test_full_pipeline(self):
        agent_profiler = AgentProfiler()
        tool_profiler = ToolProfiler()
        mem_profiler = MemoryProfiler()

        # Simulate agent execution with tool calls and memory tracking
        with mem_profiler.track("react-agent"):
            with agent_profiler.profile("react-agent"):
                # Tool 1: fast
                with tool_profiler.profile_tool("calculator"):
                    result1 = str(2 + 2)
                    tool_profiler.record_io("2+2", result1)

                # Tool 2: slower
                with tool_profiler.profile_tool("search"):
                    time.sleep(0.02)
                    result2 = "search result"
                    tool_profiler.record_io("query", result2)

                agent_profiler.record_result(f"{result1} {result2}")

        # Agent stats
        assert agent_profiler.total_executions == 1
        assert agent_profiler.get_last_metric()["success"] is True

        # Tool bottleneck identification
        assert tool_profiler.total_calls == 2
        bottlenecks = tool_profiler.get_bottlenecks()
        assert bottlenecks[0]["tool_name"] == "search"

        # Memory analysis
        assert mem_profiler.total_snapshots == 1
        assert mem_profiler.get_last_snapshot()["peak_memory_bytes"] > 0

    def test_agent_type_comparison(self):
        """Compare ReAct vs Reflection vs Planning agent types."""
        profiler = AgentProfiler()

        for agent_type in ["react", "reflection", "planning"]:
            with profiler.profile(agent_type):
                time.sleep(0.01)
                profiler.record_result(f"response from {agent_type}")

        comparison = profiler.compare_agents()
        assert len(comparison) == 3
        for agent_type in ["react", "reflection", "planning"]:
            assert comparison[agent_type]["total_executions"] == 1
            assert comparison[agent_type]["success_rate"] == 1.0
            assert comparison[agent_type]["avg_response_length"] > 0
