"""
Agent Performance Profiler for execution metrics tracking.

Provides a structured profiling utility to monitor and analyze agent
execution metrics including timing, success/failure rates, response
characteristics, and token usage.

Usage:
    from mcp_arena.agent.profiler import AgentProfiler, profile_agent

    # --- As a standalone profiler ---
    profiler = AgentProfiler()
    with profiler.profile("my-agent"):
        result = agent.process("Hello")
    profiler.record_result(result)
    print(profiler.get_last_metric())

    # --- As a decorator ---
    @profile_agent(profiler)
    def run_agent(agent, query):
        return agent.process(query)

    # --- Get aggregated stats ---
    print(profiler.get_summary())
"""

import time
import functools
import statistics
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime, timezone


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


class AgentProfiler:
    """Structured performance profiler for agent execution tracking.

    The profiler collects :class:`ExecutionMetric` records and exposes
    helpers to query per-agent and aggregate statistics.

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

    # ------------------------------------------------------------------
    # Context-manager based profiling
    # ------------------------------------------------------------------

    @contextmanager
    def profile(self, agent_name: str = "", **metadata):
        """Context manager that times the enclosed block.

        Args:
            agent_name: Identifier for the agent being profiled.
            **metadata: Arbitrary key-value pairs stored in the metric.

        Yields:
            The :class:`ExecutionMetric` being built (can be mutated).

        On exit the metric is finalised and appended to the history.
        Call :meth:`record_result` *inside* the block or immediately
        after to attach response-level information.
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

    # ------------------------------------------------------------------
    # Manual start / stop API
    # ------------------------------------------------------------------

    def start(self, agent_name: str = "", **metadata) -> None:
        """Begin profiling manually (pair with :meth:`stop`).

        Args:
            agent_name: Identifier for the agent being profiled.
            **metadata: Arbitrary key-value pairs stored in the metric.
        """
        self._current = ExecutionMetric(
            agent_name=agent_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata,
        )
        self._start_time = time.perf_counter()

    def stop(self, *, success: bool = True, error: Optional[str] = None) -> ExecutionMetric:
        """Stop profiling and record the metric.

        Args:
            success: Whether the execution was successful.
            error: Error message if the execution failed.

        Returns:
            The finalised :class:`ExecutionMetric`.

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

    # ------------------------------------------------------------------
    # Result recording helpers
    # ------------------------------------------------------------------

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

        Args:
            result: The agent's response (string, dict, or LLM result object).
            tokens_used: Override for total token count.
            prompt_tokens: Override for prompt token count.
            completion_tokens: Override for completion token count.
        """
        metric = self._current or (self._metrics[-1] if self._metrics else None)
        if metric is None:
            return

        # --- response length ---
        if isinstance(result, str):
            metric.response_length = len(result)
        elif isinstance(result, dict):
            metric.response_length = len(str(result))
        elif hasattr(result, "content"):
            metric.response_length = len(str(result.content))
        else:
            metric.response_length = len(str(result))

        # --- token usage (explicit overrides take priority) ---
        if tokens_used is not None:
            metric.tokens_used = tokens_used
        if prompt_tokens is not None:
            metric.prompt_tokens = prompt_tokens
        if completion_tokens is not None:
            metric.completion_tokens = completion_tokens

        # --- attempt auto-extraction from LLM response objects ---
        if metric.tokens_used is None:
            metric.tokens_used = self._extract_token_usage(result)

    # ------------------------------------------------------------------
    # Querying metrics
    # ------------------------------------------------------------------

    def get_last_metric(self) -> Optional[Dict[str, Any]]:
        """Return the most recently recorded metric as a dict."""
        if not self._metrics:
            return None
        return self._metrics[-1].to_dict()

    def get_metrics(self, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return recorded metrics, optionally filtered by agent name.

        Args:
            agent_name: If provided, only return metrics for this agent.

        Returns:
            List of metric dictionaries.
        """
        metrics = self._metrics
        if agent_name:
            metrics = [m for m in metrics if m.agent_name == agent_name]
        return [m.to_dict() for m in metrics]

    def get_summary(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Return aggregated statistics across recorded metrics.

        Args:
            agent_name: If provided, only summarise metrics for this agent.

        Returns:
            Dictionary with keys: ``total_executions``, ``successful``,
            ``failed``, ``success_rate``, ``avg_execution_time``,
            ``min_execution_time``, ``max_execution_time``,
            ``median_execution_time``, ``total_tokens_used``,
            ``avg_response_length``, ``agents``.
        """
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
        """Return per-agent summary statistics for comparison.

        Returns:
            Dictionary keyed by agent name, each value being the output
            of :meth:`get_summary` for that agent.
        """
        agents = {m.agent_name for m in self._metrics}
        return {name: self.get_summary(agent_name=name) for name in sorted(agents)}

    # ------------------------------------------------------------------
    # Housekeeping
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

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

        # OpenAI-style response with usage attribute
        if hasattr(result, "usage"):
            usage = result.usage
            if hasattr(usage, "total_tokens"):
                return usage.total_tokens
            if isinstance(usage, dict):
                return usage.get("total_tokens")

        # Response wrapper with response_metadata
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


# ------------------------------------------------------------------
# Decorator helper
# ------------------------------------------------------------------


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

    Returns:
        Decorator function.

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
