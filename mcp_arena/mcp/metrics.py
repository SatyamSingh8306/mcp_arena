"""
In-memory metrics collection for MCP servers.

Tracks server uptime, request counts, tool usage, errors,
and active connections for monitoring and debugging.
"""

import time
import threading
from collections import defaultdict
from typing import Dict, Any, Optional, List


class MetricsCollector:
    """Collects and exposes real-time metrics for an MCP server.
    
    Thread-safe in-memory metrics store that tracks:
    - Server start time and uptime
    - Total requests served
    - Active connections
    - Per-tool usage counts and latency
    - Error counts (total and per-tool)
    - Recent request log
    
    Example:
        >>> metrics = MetricsCollector(server_name="GitHub MCP Server")
        >>> metrics.record_request("get_user_info")
        >>> metrics.record_request("list_repos")
        >>> metrics.record_error("create_issue", "Auth failed")
        >>> print(metrics.get_metrics())
    """

    def __init__(self, server_name: str = "MCP Server", max_recent: int = 100):
        """Initialize the metrics collector.
        
        Args:
            server_name: Name of the server being monitored.
            max_recent: Maximum number of recent requests to keep in the log.
        """
        self._server_name = server_name
        self._start_time = time.time()
        self._max_recent = max_recent
        self._lock = threading.Lock()

        # Core counters
        self._total_requests: int = 0
        self._active_connections: int = 0
        self._total_errors: int = 0

        # Per-tool tracking
        self._tool_usage: Dict[str, int] = defaultdict(int)
        self._tool_errors: Dict[str, int] = defaultdict(int)
        self._tool_total_latency: Dict[str, float] = defaultdict(float)

        # Recent request log
        self._recent_requests: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Recording methods
    # ------------------------------------------------------------------

    def record_request(
        self,
        tool_name: str,
        latency: Optional[float] = None,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a completed tool request.
        
        Args:
            tool_name: Name of the tool that was invoked.
            latency: Request duration in seconds (optional).
            success: Whether the request succeeded.
            metadata: Additional metadata to store in the log entry.
        """
        with self._lock:
            self._total_requests += 1
            self._tool_usage[tool_name] += 1

            if latency is not None:
                self._tool_total_latency[tool_name] += latency

            if not success:
                self._total_errors += 1
                self._tool_errors[tool_name] += 1

            entry: Dict[str, Any] = {
                "tool": tool_name,
                "timestamp": time.time(),
                "success": success,
            }
            if latency is not None:
                entry["latency"] = round(latency, 4)
            if metadata:
                entry["metadata"] = metadata

            self._recent_requests.append(entry)
            if len(self._recent_requests) > self._max_recent:
                self._recent_requests = self._recent_requests[-self._max_recent:]

    def record_error(
        self,
        tool_name: str,
        error_message: str = "",
        latency: Optional[float] = None,
    ) -> None:
        """Convenience method to record a failed request.
        
        Args:
            tool_name: Name of the tool that failed.
            error_message: Description of the error.
            latency: Request duration in seconds (optional).
        """
        self.record_request(
            tool_name=tool_name,
            latency=latency,
            success=False,
            metadata={"error": error_message} if error_message else None,
        )

    def increment_connections(self) -> None:
        """Record a new active connection."""
        with self._lock:
            self._active_connections += 1

    def decrement_connections(self) -> None:
        """Record a closed connection."""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    @property
    def uptime(self) -> float:
        """Server uptime in seconds."""
        return time.time() - self._start_time

    @property
    def uptime_formatted(self) -> str:
        """Human-readable uptime string."""
        seconds = int(self.uptime)
        days, seconds = divmod(seconds, 86400)
        hours, seconds = divmod(seconds, 3600)
        minutes, seconds = divmod(seconds, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")
        return " ".join(parts)

    def get_metrics(self) -> Dict[str, Any]:
        """Return a snapshot of all metrics as a JSON-serializable dictionary.
        
        Returns:
            Dictionary containing all server metrics.
        """
        with self._lock:
            tool_details = {}
            for tool_name in sorted(self._tool_usage.keys()):
                count = self._tool_usage[tool_name]
                errors = self._tool_errors.get(tool_name, 0)
                total_lat = self._tool_total_latency.get(tool_name, 0.0)
                avg_lat = round(total_lat / count, 4) if count > 0 else 0.0
                tool_details[tool_name] = {
                    "calls": count,
                    "errors": errors,
                    "avg_latency_s": avg_lat,
                }

            return {
                "server_name": self._server_name,
                "start_time": self._start_time,
                "uptime_seconds": round(self.uptime, 2),
                "uptime_formatted": self.uptime_formatted,
                "total_requests": self._total_requests,
                "total_errors": self._total_errors,
                "active_connections": self._active_connections,
                "error_rate": round(
                    self._total_errors / self._total_requests, 4
                ) if self._total_requests > 0 else 0.0,
                "tools": tool_details,
                "tools_registered": len(self._tool_usage),
                "recent_requests": list(self._recent_requests[-20:]),
            }

    def get_tool_summary(self) -> List[Dict[str, Any]]:
        """Return a sorted list of tool usage summaries.
        
        Returns:
            List of dicts sorted by call count (descending).
        """
        with self._lock:
            summaries = []
            for tool_name in self._tool_usage:
                count = self._tool_usage[tool_name]
                errors = self._tool_errors.get(tool_name, 0)
                total_lat = self._tool_total_latency.get(tool_name, 0.0)
                summaries.append({
                    "tool": tool_name,
                    "calls": count,
                    "errors": errors,
                    "avg_latency_s": round(total_lat / count, 4) if count > 0 else 0.0,
                })
            summaries.sort(key=lambda x: x["calls"], reverse=True)
            return summaries

    def reset(self) -> None:
        """Reset all metrics (keeps server_name and start_time)."""
        with self._lock:
            self._total_requests = 0
            self._active_connections = 0
            self._total_errors = 0
            self._tool_usage.clear()
            self._tool_errors.clear()
            self._tool_total_latency.clear()
            self._recent_requests.clear()
