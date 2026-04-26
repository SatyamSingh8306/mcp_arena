"""
Agent Performance Profiler for execution metrics tracking.

Provides structured profiling utilities to monitor and analyze agent
execution metrics including timing, success/failure rates, response
characteristics, token usage, tool-level bottleneck identification,
and memory usage analysis.

Usage:
    from mcp_arena.agent.profiler import (
        AgentProfiler, ToolProfiler, MemoryProfiler, profile_agent,
    )

    # --- Profile an agent execution ---
    profiler = AgentProfiler()
    with profiler.profile("my-agent"):
        result = agent.process("Hello")
    profiler.record_result(result)
    print(profiler.get_summary())

    # --- Profile individual tools ---
    tool_profiler = ToolProfiler()
    with tool_profiler.profile_tool("calculator"):
        answer = calculator.execute("2+2")
    print(tool_profiler.get_bottlenecks())

    # --- Track memory usage ---
    mem_profiler = MemoryProfiler()
    with mem_profiler.track("my-agent"):
        result = agent.process("complex query")
    print(mem_profiler.get_last_snapshot())
"""

import time
import functools
import statistics
import tracemalloc
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone


# ══════════════════════════════════════════════════════════════════════════════
# Execution Metric
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class ExecutionMetric:
    """A single execution metric record.

    Attributes:
        agent_name: Name or identifier of the agent being profiled.
        execution_time: Wall-clock time in seconds (via ``time.perf_counter``).
        success: Whether the execution completed without error.
        error: Error message if the execution failed.
        response_length: Character length of the response (if available).
        tokens_used: Total token count reported by the LLM (if available).
        prompt_tokens: Prompt/input token count (if available).
        completion_tokens: Completion/output token count (if available).
        timestamp: ISO-8601 timestamp of when the metric was recorded.
        metadata: Arbitrary extra data attached by the caller.
    """

    agent_name: str = ""
    execution_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    response_length: Optional[int] = None
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return the metric as a plain dictionary."""
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Tool Metric
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class ToolMetric:
    """A single tool execution metric.

    Attributes:
        tool_name: Identifier of the tool.
        execution_time: Wall-clock time in seconds.
        success: Whether the tool call succeeded.
        error: Error message on failure.
        input_size: Character length of the input (if available).
        output_size: Character length of the output (if available).
        timestamp: ISO-8601 timestamp.
        metadata: Arbitrary extra data.
    """

    tool_name: str = ""
    execution_time: float = 0.0
    success: bool = True
    error: Optional[str] = None
    input_size: Optional[int] = None
    output_size: Optional[int] = None
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return the metric as a plain dictionary."""
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Memory Snapshot
# ══════════════════════════════════════════════════════════════════════════════


@dataclass
class MemorySnapshot:
    """A memory usage snapshot for an execution.

    Attributes:
        label: Identifier (agent name, tool name, etc.).
        peak_memory_bytes: Peak memory usage in bytes during the block.
        current_memory_bytes: Memory usage at the end of the block.
        peak_memory_mb: Peak memory in megabytes.
        current_memory_mb: Current memory in megabytes.
        timestamp: ISO-8601 timestamp.
        metadata: Arbitrary extra data.
    """

    label: str = ""
    peak_memory_bytes: int = 0
    current_memory_bytes: int = 0
    peak_memory_mb: float = 0.0
    current_memory_mb: float = 0.0
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Return the snapshot as a plain dictionary."""
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Agent Profiler
# ══════════════════════════════════════════════════════════════════════════════


class AgentProfiler:
    """Structured performance profiler for agent execution tracking.

    Collects :class:`ExecutionMetric` records and exposes helpers to
    query per-agent and aggregate statistics.

    Example::

        profiler = AgentProfiler()

        with profiler.profile("my-agent"):
            result = agent.process("What is 2+2?")
        profiler.record_result(result)

        print(profiler.get_last_metric())
        print(profiler.get_summary())
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._metrics: List[ExecutionMetric] = []
        self._current: Optional[ExecutionMetric] = None
        self._start_time: Optional[float] = None
        self.enabled = enabled

    # ── Context-manager profiling ─────────────────────────────────────────

    @contextmanager
    def profile(self, agent_name: str = "", **metadata):
        """Context manager that times the enclosed block.

        Args:
            agent_name: Identifier for the agent being profiled.
            **metadata: Arbitrary key-value pairs stored in the metric.

        Yields:
            The :class:`ExecutionMetric` being built (can be mutated).
        """
        metric = ExecutionMetric(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )
        self._current = metric
        self._start_time = time.perf_counter()

        try:
            yield metric
            metric.success = True
        except Exception as exc:
            metric.success = False
            metric.error = str(exc)
            raise
        finally:
            metric.execution_time = round(
                time.perf_counter() - (self._start_time or 0), 6
            )
            if self.enabled:
                self._metrics.append(metric)
            self._current = None
            self._start_time = None

    # ── Manual start / stop ───────────────────────────────────────────────

    def start(self, agent_name: str = "", **metadata) -> None:
        """Begin profiling manually (pair with :meth:`stop`)."""
        self._current = ExecutionMetric(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )
        self._start_time = time.perf_counter()

    def stop(self, *, success: bool = True, error: Optional[str] = None) -> ExecutionMetric:
        """Stop profiling and record the metric.

        Raises:
            RuntimeError: If :meth:`start` was not called first.
        """
        if self._current is None or self._start_time is None:
            raise RuntimeError("Profiler was not started. Call start() first.")

        metric = self._current
        metric.execution_time = round(
            time.perf_counter() - self._start_time, 6
        )
        metric.success = success
        metric.error = error

        if self.enabled:
            self._metrics.append(metric)

        self._current = None
        self._start_time = None
        return metric

    # ── Result recording ──────────────────────────────────────────────────

    def record_result(
        self,
        result: Any,
        *,
        tokens_used: Optional[int] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
    ) -> None:
        """Attach result information to the current or last metric.

        Inspects *result* to derive ``response_length`` and, when
        possible, token counts.
        """
        metric = self._current or (self._metrics[-1] if self._metrics else None)
        if metric is None:
            return

        # response length
        if isinstance(result, str):
            metric.response_length = len(result)
        elif isinstance(result, dict):
            metric.response_length = len(str(result))
        elif hasattr(result, "content"):
            metric.response_length = len(str(result.content))
        else:
            metric.response_length = len(str(result))

        # token usage (explicit overrides take priority)
        if tokens_used is not None:
            metric.tokens_used = tokens_used
        if prompt_tokens is not None:
            metric.prompt_tokens = prompt_tokens
        if completion_tokens is not None:
            metric.completion_tokens = completion_tokens

        # auto-extraction from LLM response objects
        if metric.tokens_used is None:
            metric.tokens_used = self._extract_token_usage(result)

    # ── Querying metrics ──────────────────────────────────────────────────

    def get_last_metric(self) -> Optional[Dict[str, Any]]:
        """Return the most recently recorded metric as a dict."""
        if not self._metrics:
            return None
        return self._metrics[-1].to_dict()

    def get_metrics(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return recorded metrics, optionally filtered by agent name."""
        metrics = self._metrics
        if agent_name:
            metrics = [m for m in metrics if m.agent_name == agent_name]
        return [m.to_dict() for m in metrics]

    def get_summary(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Return aggregated statistics across recorded metrics."""
        metrics = self._metrics
        if agent_name:
            metrics = [m for m in metrics if m.agent_name == agent_name]

        if not metrics:
            return {
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "min_execution_time": 0.0,
                "max_execution_time": 0.0,
                "median_execution_time": 0.0,
                "total_tokens_used": 0,
                "avg_response_length": 0.0,
                "agents": [],
            }

        times = [m.execution_time for m in metrics]
        successes = sum(1 for m in metrics if m.success)
        failures = len(metrics) - successes
        token_counts = [m.tokens_used for m in metrics if m.tokens_used is not None]
        response_lengths = [m.response_length for m in metrics if m.response_length is not None]
        unique_agents = sorted({m.agent_name for m in metrics})

        return {
            "total_executions": len(metrics),
            "successful": successes,
            "failed": failures,
            "success_rate": round(successes / len(metrics), 4) if metrics else 0.0,
            "avg_execution_time": round(statistics.mean(times), 6),
            "min_execution_time": round(min(times), 6),
            "max_execution_time": round(max(times), 6),
            "median_execution_time": round(statistics.median(times), 6),
            "total_tokens_used": sum(token_counts) if token_counts else 0,
            "avg_response_length": (
                round(statistics.mean(response_lengths), 2) if response_lengths else 0.0
            ),
            "agents": unique_agents,
        }

    def compare_agents(self) -> Dict[str, Dict[str, Any]]:
        """Return per-agent summary statistics for benchmarking.

        Useful for comparing ReAct vs Reflection vs Planning agents.
        """
        agents = {m.agent_name for m in self._metrics}
        return {name: self.get_summary(agent_name=name) for name in sorted(agents)}

    # ── Housekeeping ──────────────────────────────────────────────────────

    @property
    def total_executions(self) -> int:
        """Total number of recorded executions."""
        return len(self._metrics)

    def clear(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()

    def reset(self) -> None:
        """Alias for :meth:`clear`."""
        self.clear()

    # ── Internal helpers ──────────────────────────────────────────────────

    @staticmethod
    def _extract_token_usage(result: Any) -> Optional[int]:
        """Try to extract token usage from an LLM response object."""
        # LangChain AIMessage with usage_metadata
        if hasattr(result, "usage_metadata"):
            usage = result.usage_metadata
            if isinstance(usage, dict):
                return usage.get("total_tokens")
            if hasattr(usage, "total_tokens"):
                return usage.total_tokens

        # OpenAI-style response
        if hasattr(result, "usage"):
            usage = result.usage
            if hasattr(usage, "total_tokens"):
                return usage.total_tokens
            if isinstance(usage, dict):
                return usage.get("total_tokens")

        # response_metadata wrapper
        if hasattr(result, "response_metadata"):
            meta = result.response_metadata
            if isinstance(meta, dict):
                token_usage = meta.get("token_usage") or meta.get("usage")
                if isinstance(token_usage, dict):
                    return token_usage.get("total_tokens")

        return None

    def __repr__(self) -> str:
        return (
            f"AgentProfiler(enabled={self.enabled}, "
            f"total_executions={self.total_executions})"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Tool Profiler — identify bottleneck tools
# ══════════════════════════════════════════════════════════════════════════════


class ToolProfiler:
    """Profile individual tool executions to identify bottlenecks.

    Example::

        tp = ToolProfiler()

        with tp.profile_tool("calculator"):
            calc.execute("2+2")

        with tp.profile_tool("search"):
            search.execute("latest news")

        print(tp.get_bottlenecks())       # slowest tools
        print(tp.get_tool_summary())      # per-tool stats
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._metrics: List[ToolMetric] = []
        self._current: Optional[ToolMetric] = None
        self._start_time: Optional[float] = None
        self.enabled = enabled

    @contextmanager
    def profile_tool(self, tool_name: str, **metadata):
        """Context manager that times a tool execution.

        Args:
            tool_name: Identifier for the tool.
            **metadata: Extra data stored in the metric.

        Yields:
            The :class:`ToolMetric` being built.
        """
        metric = ToolMetric(
            tool_name=tool_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )
        self._current = metric
        self._start_time = time.perf_counter()

        try:
            yield metric
            metric.success = True
        except Exception as exc:
            metric.success = False
            metric.error = str(exc)
            raise
        finally:
            metric.execution_time = round(
                time.perf_counter() - (self._start_time or 0), 6
            )
            if self.enabled:
                self._metrics.append(metric)
            self._current = None
            self._start_time = None

    def record_io(
        self,
        input_data: Any = None,
        output_data: Any = None,
    ) -> None:
        """Record input/output sizes for the current or last tool metric.

        Args:
            input_data: The input passed to the tool.
            output_data: The output returned by the tool.
        """
        metric = self._current or (self._metrics[-1] if self._metrics else None)
        if metric is None:
            return
        if input_data is not None:
            metric.input_size = len(str(input_data))
        if output_data is not None:
            metric.output_size = len(str(output_data))

    def get_metrics(self, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all tool metrics, optionally filtered by tool name."""
        metrics = self._metrics
        if tool_name:
            metrics = [m for m in metrics if m.tool_name == tool_name]
        return [m.to_dict() for m in metrics]

    def get_tool_summary(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """Aggregated statistics for tool executions.

        Args:
            tool_name: If provided, only summarise this tool.

        Returns:
            Dictionary with totals, success rate, and timing stats.
        """
        metrics = self._metrics
        if tool_name:
            metrics = [m for m in metrics if m.tool_name == tool_name]

        if not metrics:
            return {
                "total_calls": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "avg_execution_time": 0.0,
                "min_execution_time": 0.0,
                "max_execution_time": 0.0,
                "total_execution_time": 0.0,
                "tools": [],
            }

        times = [m.execution_time for m in metrics]
        successes = sum(1 for m in metrics if m.success)

        return {
            "total_calls": len(metrics),
            "successful": successes,
            "failed": len(metrics) - successes,
            "success_rate": round(successes / len(metrics), 4),
            "avg_execution_time": round(statistics.mean(times), 6),
            "min_execution_time": round(min(times), 6),
            "max_execution_time": round(max(times), 6),
            "total_execution_time": round(sum(times), 6),
            "tools": sorted({m.tool_name for m in metrics}),
        }

    def get_bottlenecks(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Identify the slowest tools by average execution time.

        Args:
            top_n: Number of tools to return (default 5).

        Returns:
            List of dicts sorted by ``avg_execution_time`` descending,
            each containing ``tool_name``, ``avg_execution_time``,
            ``total_calls``, ``total_execution_time``, and
            ``max_execution_time``.
        """
        tool_names = {m.tool_name for m in self._metrics}
        rankings: List[Dict[str, Any]] = []

        for name in tool_names:
            tool_metrics = [m for m in self._metrics if m.tool_name == name]
            times = [m.execution_time for m in tool_metrics]
            rankings.append({
                "tool_name": name,
                "avg_execution_time": round(statistics.mean(times), 6),
                "total_calls": len(tool_metrics),
                "total_execution_time": round(sum(times), 6),
                "max_execution_time": round(max(times), 6),
            })

        rankings.sort(key=lambda r: r["avg_execution_time"], reverse=True)
        return rankings[:top_n]

    def get_failure_report(self) -> List[Dict[str, Any]]:
        """Return tools ranked by failure rate.

        Returns:
            List of dicts sorted by ``failure_rate`` descending, each
            containing ``tool_name``, ``total_calls``, ``failures``,
            and ``failure_rate``.
        """
        tool_names = {m.tool_name for m in self._metrics}
        report: List[Dict[str, Any]] = []

        for name in tool_names:
            tool_metrics = [m for m in self._metrics if m.tool_name == name]
            failures = sum(1 for m in tool_metrics if not m.success)
            report.append({
                "tool_name": name,
                "total_calls": len(tool_metrics),
                "failures": failures,
                "failure_rate": round(failures / len(tool_metrics), 4),
            })

        report.sort(key=lambda r: r["failure_rate"], reverse=True)
        return report

    @property
    def total_calls(self) -> int:
        """Total number of recorded tool calls."""
        return len(self._metrics)

    def clear(self) -> None:
        """Clear all recorded tool metrics."""
        self._metrics.clear()

    def __repr__(self) -> str:
        return f"ToolProfiler(enabled={self.enabled}, total_calls={self.total_calls})"


# ══════════════════════════════════════════════════════════════════════════════
# Memory Profiler — memory usage analysis
# ══════════════════════════════════════════════════════════════════════════════


class MemoryProfiler:
    """Track memory usage during agent or tool execution.

    Uses :mod:`tracemalloc` to capture peak and current memory usage
    within profiled blocks.

    Example::

        mp = MemoryProfiler()

        with mp.track("react-agent"):
            agent.process("compute something heavy")

        print(mp.get_last_snapshot())
        print(mp.get_summary())
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self._snapshots: List[MemorySnapshot] = []
        self.enabled = enabled

    @contextmanager
    def track(self, label: str = "", **metadata):
        """Context manager that captures memory usage for the block.

        Args:
            label: Identifier (agent name, tool name, etc.).
            **metadata: Extra data stored in the snapshot.

        Yields:
            The :class:`MemorySnapshot` being built.

        Note:
            Uses ``tracemalloc``. If tracemalloc is already running it
            will take a nested snapshot; otherwise it starts and stops
            tracing around the block.
        """
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()

        # Reset peak to get an accurate peak for this block only
        tracemalloc.reset_peak()

        snapshot = MemorySnapshot(
            label=label,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )

        try:
            yield snapshot
        finally:
            current, peak = tracemalloc.get_traced_memory()

            snapshot.current_memory_bytes = current
            snapshot.peak_memory_bytes = peak
            snapshot.current_memory_mb = round(current / (1024 * 1024), 4)
            snapshot.peak_memory_mb = round(peak / (1024 * 1024), 4)

            if self.enabled:
                self._snapshots.append(snapshot)

            if not was_tracing:
                tracemalloc.stop()

    def get_last_snapshot(self) -> Optional[Dict[str, Any]]:
        """Return the most recent memory snapshot as a dict."""
        if not self._snapshots:
            return None
        return self._snapshots[-1].to_dict()

    def get_snapshots(self, label: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return snapshots, optionally filtered by label."""
        snapshots = self._snapshots
        if label:
            snapshots = [s for s in snapshots if s.label == label]
        return [s.to_dict() for s in snapshots]

    def get_summary(self, label: Optional[str] = None) -> Dict[str, Any]:
        """Aggregated memory statistics.

        Args:
            label: If provided, only summarise snapshots with this label.

        Returns:
            Dictionary with peak, average, and per-label memory stats.
        """
        snapshots = self._snapshots
        if label:
            snapshots = [s for s in snapshots if s.label == label]

        if not snapshots:
            return {
                "total_snapshots": 0,
                "avg_peak_memory_mb": 0.0,
                "max_peak_memory_mb": 0.0,
                "avg_current_memory_mb": 0.0,
                "labels": [],
            }

        peaks = [s.peak_memory_mb for s in snapshots]
        currents = [s.current_memory_mb for s in snapshots]

        return {
            "total_snapshots": len(snapshots),
            "avg_peak_memory_mb": round(statistics.mean(peaks), 4),
            "max_peak_memory_mb": round(max(peaks), 4),
            "avg_current_memory_mb": round(statistics.mean(currents), 4),
            "labels": sorted({s.label for s in snapshots}),
        }

    def compare_labels(self) -> Dict[str, Dict[str, Any]]:
        """Per-label memory summary for comparison.

        Useful for comparing memory across agent types.
        """
        labels = {s.label for s in self._snapshots}
        return {lbl: self.get_summary(label=lbl) for lbl in sorted(labels)}

    @property
    def total_snapshots(self) -> int:
        """Total number of recorded snapshots."""
        return len(self._snapshots)

    def clear(self) -> None:
        """Clear all recorded snapshots."""
        self._snapshots.clear()

    def __repr__(self) -> str:
        return f"MemoryProfiler(enabled={self.enabled}, total_snapshots={self.total_snapshots})"


# ══════════════════════════════════════════════════════════════════════════════
# Decorator helper
# ══════════════════════════════════════════════════════════════════════════════


def profile_agent(
    profiler: AgentProfiler,
    agent_name: str = "",
) -> Callable:
    """Decorator that profiles a function's execution.

    The decorated function's return value is passed to
    :meth:`AgentProfiler.record_result` automatically.

    Args:
        profiler: The :class:`AgentProfiler` instance to use.
        agent_name: Agent identifier stored in the metric.

    Example::

        profiler = AgentProfiler()

        @profile_agent(profiler, agent_name="react")
        def run_query(agent, query):
            return agent.process(query)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            name = agent_name or func.__name__
            with profiler.profile(name):
                result = func(*args, **kwargs)
                profiler.record_result(result)
            return result

        return wrapper

    return decorator
