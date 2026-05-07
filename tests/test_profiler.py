"""Tests for the Agent Performance Profiler (issue #30)."""

import time
import pytest
from mcp_arena.agent.profiler import AgentProfiler, ExecutionMetric, profile_agent


# ── ExecutionMetric tests ─────────────────────────────────────────────────────


class TestExecutionMetric:
    """Tests for the ExecutionMetric dataclass."""

    def test_default_values(self):
        metric = ExecutionMetric()
        assert metric.agent_name == ""
        assert metric.execution_time == 0.0
        assert metric.success is True
        assert metric.error is None
        assert metric.response_length is None
        assert metric.tokens_used is None
        assert metric.prompt_tokens is None
        assert metric.completion_tokens is None
        assert metric.metadata == {}

    def test_custom_values(self):
        metric = ExecutionMetric(
            agent_name="test-agent",
            execution_time=1.5,
            success=False,
            error="timeout",
            response_length=42,
            tokens_used=100,
        )
        assert metric.agent_name == "test-agent"
        assert metric.execution_time == 1.5
        assert metric.success is False
        assert metric.error == "timeout"
        assert metric.response_length == 42
        assert metric.tokens_used == 100

    def test_to_dict(self):
        metric = ExecutionMetric(agent_name="a", execution_time=0.5)
        d = metric.to_dict()
        assert isinstance(d, dict)
        assert d["agent_name"] == "a"
        assert d["execution_time"] == 0.5
        assert "success" in d
        assert "metadata" in d


# ── AgentProfiler context-manager tests ───────────────────────────────────────


class TestProfilerContextManager:
    """Tests for AgentProfiler.profile() context manager."""

    def test_basic_profiling(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-a"):
            time.sleep(0.01)

        assert profiler.total_executions == 1
        last = profiler.get_last_metric()
        assert last is not None
        assert last["agent_name"] == "agent-a"
        assert last["success"] is True
        assert last["execution_time"] > 0

    def test_profiling_captures_failure(self):
        profiler = AgentProfiler()
        with pytest.raises(ValueError):
            with profiler.profile("agent-fail"):
                raise ValueError("boom")

        assert profiler.total_executions == 1
        last = profiler.get_last_metric()
        assert last["success"] is False
        assert last["error"] == "boom"
        assert last["execution_time"] > 0

    def test_metadata_passed_through(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-m", model="gpt-4", run_id=7):
            pass

        last = profiler.get_last_metric()
        assert last["metadata"]["model"] == "gpt-4"
        assert last["metadata"]["run_id"] == 7

    def test_timestamp_recorded(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-t"):
            pass

        last = profiler.get_last_metric()
        assert last["timestamp"] != ""
        # ISO-8601 contains 'T' separator
        assert "T" in last["timestamp"]

    def test_multiple_profiles(self):
        profiler = AgentProfiler()
        for i in range(5):
            with profiler.profile(f"agent-{i}"):
                pass

        assert profiler.total_executions == 5
        metrics = profiler.get_metrics()
        assert len(metrics) == 5

    def test_disabled_profiler(self):
        profiler = AgentProfiler(enabled=False)
        with profiler.profile("agent-disabled"):
            pass

        assert profiler.total_executions == 0
        assert profiler.get_last_metric() is None


# ── AgentProfiler start/stop tests ───────────────────────────────────────────


class TestProfilerStartStop:
    """Tests for manual start/stop profiling API."""

    def test_start_stop_basic(self):
        profiler = AgentProfiler()
        profiler.start("agent-x")
        time.sleep(0.01)
        metric = profiler.stop()

        assert metric.agent_name == "agent-x"
        assert metric.success is True
        assert metric.execution_time > 0
        assert profiler.total_executions == 1

    def test_stop_with_failure(self):
        profiler = AgentProfiler()
        profiler.start("agent-y")
        metric = profiler.stop(success=False, error="bad input")

        assert metric.success is False
        assert metric.error == "bad input"

    def test_stop_without_start_raises(self):
        profiler = AgentProfiler()
        with pytest.raises(RuntimeError, match="not started"):
            profiler.stop()


# ── record_result tests ──────────────────────────────────────────────────────


class TestRecordResult:
    """Tests for AgentProfiler.record_result()."""

    def test_string_result(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-r"):
            profiler.record_result("Hello, world!")

        last = profiler.get_last_metric()
        assert last["response_length"] == len("Hello, world!")

    def test_dict_result(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-d"):
            profiler.record_result({"key": "value"})

        last = profiler.get_last_metric()
        assert last["response_length"] is not None
        assert last["response_length"] > 0

    def test_explicit_token_counts(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-tok"):
            profiler.record_result(
                "result",
                tokens_used=512,
                prompt_tokens=100,
                completion_tokens=412,
            )

        last = profiler.get_last_metric()
        assert last["tokens_used"] == 512
        assert last["prompt_tokens"] == 100
        assert last["completion_tokens"] == 412

    def test_record_after_context(self):
        profiler = AgentProfiler()
        with profiler.profile("agent-after"):
            pass
        profiler.record_result("post-result", tokens_used=256)

        last = profiler.get_last_metric()
        assert last["response_length"] == len("post-result")
        assert last["tokens_used"] == 256

    def test_no_metric_does_not_crash(self):
        profiler = AgentProfiler()
        # Should not raise even with no metrics
        profiler.record_result("orphan")


# ── get_metrics / filtering tests ────────────────────────────────────────────


class TestGetMetrics:
    """Tests for metric querying and filtering."""

    def test_get_metrics_unfiltered(self):
        profiler = AgentProfiler()
        with profiler.profile("a"):
            pass
        with profiler.profile("b"):
            pass

        assert len(profiler.get_metrics()) == 2

    def test_get_metrics_filtered_by_agent(self):
        profiler = AgentProfiler()
        with profiler.profile("alpha"):
            pass
        with profiler.profile("beta"):
            pass
        with profiler.profile("alpha"):
            pass

        alpha = profiler.get_metrics(agent_name="alpha")
        assert len(alpha) == 2
        assert all(m["agent_name"] == "alpha" for m in alpha)

    def test_get_metrics_returns_dicts(self):
        profiler = AgentProfiler()
        with profiler.profile("x"):
            pass

        metrics = profiler.get_metrics()
        assert all(isinstance(m, dict) for m in metrics)


# ── get_summary tests ────────────────────────────────────────────────────────


class TestGetSummary:
    """Tests for aggregated summary statistics."""

    def test_empty_summary(self):
        profiler = AgentProfiler()
        summary = profiler.get_summary()
        assert summary["total_executions"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["agents"] == []

    def test_summary_with_data(self):
        profiler = AgentProfiler()
        with profiler.profile("a"):
            profiler.record_result("ok", tokens_used=10)
        with profiler.profile("b"):
            profiler.record_result("fine", tokens_used=20)

        summary = profiler.get_summary()
        assert summary["total_executions"] == 2
        assert summary["successful"] == 2
        assert summary["failed"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["total_tokens_used"] == 30
        assert summary["avg_execution_time"] > 0
        assert summary["min_execution_time"] > 0
        assert summary["max_execution_time"] >= summary["min_execution_time"]
        assert summary["median_execution_time"] > 0
        assert "a" in summary["agents"]
        assert "b" in summary["agents"]

    def test_summary_with_failures(self):
        profiler = AgentProfiler()
        with profiler.profile("ok-agent"):
            pass
        try:
            with profiler.profile("fail-agent"):
                raise RuntimeError("err")
        except RuntimeError:
            pass

        summary = profiler.get_summary()
        assert summary["successful"] == 1
        assert summary["failed"] == 1
        assert summary["success_rate"] == 0.5

    def test_summary_filtered_by_agent(self):
        profiler = AgentProfiler()
        with profiler.profile("target"):
            profiler.record_result("r1")
        with profiler.profile("other"):
            profiler.record_result("r2")
        with profiler.profile("target"):
            profiler.record_result("r3")

        summary = profiler.get_summary(agent_name="target")
        assert summary["total_executions"] == 2
        assert summary["agents"] == ["target"]

    def test_avg_response_length(self):
        profiler = AgentProfiler()
        with profiler.profile("a"):
            profiler.record_result("ab")  # length 2
        with profiler.profile("a"):
            profiler.record_result("abcd")  # length 4

        summary = profiler.get_summary()
        assert summary["avg_response_length"] == 3.0


# ── compare_agents tests ─────────────────────────────────────────────────────


class TestCompareAgents:
    """Tests for per-agent comparison."""

    def test_compare_multiple_agents(self):
        profiler = AgentProfiler()
        with profiler.profile("fast"):
            pass
        with profiler.profile("slow"):
            time.sleep(0.02)

        comparison = profiler.compare_agents()
        assert "fast" in comparison
        assert "slow" in comparison
        assert comparison["fast"]["total_executions"] == 1
        assert comparison["slow"]["total_executions"] == 1
        # Slow should take longer (or at least not be zero)
        assert comparison["slow"]["avg_execution_time"] > 0

    def test_compare_empty(self):
        profiler = AgentProfiler()
        assert profiler.compare_agents() == {}


# ── clear / reset tests ──────────────────────────────────────────────────────


class TestClearReset:
    """Tests for clearing profiler state."""

    def test_clear(self):
        profiler = AgentProfiler()
        with profiler.profile("tmp"):
            pass
        assert profiler.total_executions == 1

        profiler.clear()
        assert profiler.total_executions == 0
        assert profiler.get_metrics() == []

    def test_reset_alias(self):
        profiler = AgentProfiler()
        with profiler.profile("tmp"):
            pass
        profiler.reset()
        assert profiler.total_executions == 0


# ── profile_agent decorator tests ────────────────────────────────────────────


class TestProfileAgentDecorator:
    """Tests for the @profile_agent decorator."""

    def test_decorator_basic(self):
        profiler = AgentProfiler()

        @profile_agent(profiler, agent_name="decorated")
        def my_task():
            return "result"

        result = my_task()
        assert result == "result"
        assert profiler.total_executions == 1
        last = profiler.get_last_metric()
        assert last["agent_name"] == "decorated"
        assert last["success"] is True
        assert last["response_length"] == len("result")

    def test_decorator_uses_func_name_if_no_agent_name(self):
        profiler = AgentProfiler()

        @profile_agent(profiler)
        def my_function():
            return "ok"

        my_function()
        last = profiler.get_last_metric()
        assert last["agent_name"] == "my_function"

    def test_decorator_captures_exception(self):
        profiler = AgentProfiler()

        @profile_agent(profiler, agent_name="err-agent")
        def failing():
            raise ValueError("oops")

        with pytest.raises(ValueError):
            failing()

        assert profiler.total_executions == 1
        last = profiler.get_last_metric()
        assert last["success"] is False
        assert last["error"] == "oops"

    def test_decorator_multiple_calls(self):
        profiler = AgentProfiler()

        @profile_agent(profiler, agent_name="multi")
        def task():
            return "x"

        for _ in range(3):
            task()

        assert profiler.total_executions == 3


# ── Token extraction tests ───────────────────────────────────────────────────


class TestTokenExtraction:
    """Tests for automatic token usage extraction from LLM responses."""

    def test_extract_from_usage_metadata_dict(self):
        class FakeResponse:
            usage_metadata = {"total_tokens": 150}

        profiler = AgentProfiler()
        with profiler.profile("tok"):
            profiler.record_result(FakeResponse())

        last = profiler.get_last_metric()
        assert last["tokens_used"] == 150

    def test_extract_from_usage_attr(self):
        class FakeUsage:
            total_tokens = 200

        class FakeResponse:
            usage = FakeUsage()

        profiler = AgentProfiler()
        with profiler.profile("tok"):
            profiler.record_result(FakeResponse())

        last = profiler.get_last_metric()
        assert last["tokens_used"] == 200

    def test_extract_from_response_metadata(self):
        class FakeResponse:
            response_metadata = {"token_usage": {"total_tokens": 300}}

        profiler = AgentProfiler()
        with profiler.profile("tok"):
            profiler.record_result(FakeResponse())

        last = profiler.get_last_metric()
        assert last["tokens_used"] == 300

    def test_no_token_info_returns_none(self):
        profiler = AgentProfiler()
        with profiler.profile("plain"):
            profiler.record_result("just a string")

        last = profiler.get_last_metric()
        assert last["tokens_used"] is None

    def test_explicit_overrides_auto(self):
        class FakeResponse:
            usage_metadata = {"total_tokens": 100}

        profiler = AgentProfiler()
        with profiler.profile("override"):
            profiler.record_result(FakeResponse(), tokens_used=999)

        last = profiler.get_last_metric()
        assert last["tokens_used"] == 999


# ── Repr test ─────────────────────────────────────────────────────────────────


class TestRepr:
    def test_repr(self):
        profiler = AgentProfiler()
        r = repr(profiler)
        assert "AgentProfiler" in r
        assert "enabled=True" in r
        assert "total_executions=0" in r
