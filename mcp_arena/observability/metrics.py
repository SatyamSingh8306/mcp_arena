import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import statistics

from mcp_arena.mcp.server import BaseMCPServer

class MetricType(str, Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    timestamp: str
    server_name: str
    tool_name: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

class MCPMetricsCollector:
    """Collects performance metrics from MCP servers."""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.metrics_buffer: List[Metric] = []
        self.max_buffer_size = 5000
        
        # Track counters and gauges
        self.counters: Dict[str, float] = {}
        self.gauges: Dict[str, float] = {}
        
    def record(
        self,
        metric_type: MetricType,
        name: str,
        value: float = 1.0,
        tool_name: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Metric:
        """Record a metric."""
        metric = Metric(
            name=name,
            type=metric_type,
            value=value,
            timestamp=datetime.now().isoformat(),
            server_name=self.server_name,
            tool_name=tool_name,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        self.metrics_buffer.append(metric)
        if len(self.metrics_buffer) > self.max_buffer_size:
            self.metrics_buffer = self.metrics_buffer[-self.max_buffer_size:]
        
        # Update internal state
        if metric_type == MetricType.COUNTER:
            self.counters[name] = self.counters.get(name, 0) + value
        elif metric_type == MetricType.GAUGE:
            self.gauges[name] = value
        
        return metric
    
    def increment_counter(self, name: str, value: float = 1.0, **kwargs) -> Metric:
        """Increment a counter metric."""
        return self.record(MetricType.COUNTER, name, value, **kwargs)
    
    def set_gauge(self, name: str, value: float, **kwargs) -> Metric:
        """Set a gauge metric."""
        return self.record(MetricType.GAUGE, name, value, **kwargs)
    
    def record_timer(self, name: str, duration_ms: float, **kwargs) -> Metric:
        """Record a timer metric."""
        return self.record(MetricType.TIMER, name, duration_ms, **kwargs)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        summary = {
            "server": self.server_name,
            "total_metrics": len(self.metrics_buffer),
            "counters": self.counters,
            "gauges": self.gauges,
            "recent_metrics": []
        }
        
        # Add recent metrics
        recent = self.metrics_buffer[-20:] if self.metrics_buffer else []
        summary["recent_metrics"] = [asdict(m) for m in recent]
        
        # Calculate rates for counters
        summary["counter_rates"] = {}
        for counter_name, total in self.counters.items():
            # Simple rate calculation (could be improved with time window)
            counter_metrics = [m for m in self.metrics_buffer 
                             if m.name == counter_name and m.type == MetricType.COUNTER]
            if len(counter_metrics) > 1:
                first_time = datetime.fromisoformat(counter_metrics[0].timestamp)
                last_time = datetime.fromisoformat(counter_metrics[-1].timestamp)
                time_diff = (last_time - first_time).total_seconds()
                if time_diff > 0:
                    summary["counter_rates"][counter_name] = total / time_diff
        
        return summary
    
    def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """Get metrics for a specific tool."""
        tool_metrics = [m for m in self.metrics_buffer if m.tool_name == tool_name]
        
        if not tool_metrics:
            return {"tool": tool_name, "message": "No metrics found"}
        
        # Group by metric type
        by_type = {}
        for metric in tool_metrics:
            by_type.setdefault(metric.type.value, []).append(metric.value)
        
        # Calculate statistics
        stats = {}
        for metric_type, values in by_type.items():
            if values:
                stats[metric_type] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values)
                }
        
        return {
            "tool": tool_name,
            "total_calls": len([m for m in tool_metrics if m.type == MetricType.COUNTER]),
            "statistics": stats,
            "recent_metrics": [asdict(m) for m in tool_metrics[-10:]]
        }

class MetricsMCPServer(BaseMCPServer):
    """MCP server for collecting and analyzing metrics from all MCP servers."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="MCP Metrics Server",
            description="Centralized metrics collection for MCP servers",
            **kwargs
        )
        self.collectors: Dict[str, MCPMetricsCollector] = {}
        self.metrics_history: Dict[str, List[Metric]] = {}
        
    def _register_tools(self):
        """Register metrics collection tools."""
        
        @self.mcp_server.tool()
        def register_metrics_collector(
            server_name: str
        ) -> Dict[str, Any]:
            """Register an MCP server for metrics collection."""
            collector = MCPMetricsCollector(server_name)
            self.collectors[server_name] = collector
            self.metrics_history[server_name] = []
            
            return {
                "success": True,
                "server": server_name,
                "collector_id": id(collector),
                "message": f"Metrics collector registered for {server_name}"
            }
        
        @self.mcp_server.tool()
        def record_server_metric(
            server_name: str,
            metric_type: str,
            metric_name: str,
            value: float,
            tool_name: Optional[str] = None,
            tags: Optional[Dict[str, str]] = None
        ) -> Dict[str, Any]:
            """Record a metric for a server."""
            if server_name not in self.collectors:
                return {"error": f"Server '{server_name}' not registered for metrics"}
            
            collector = self.collectors[server_name]
            metric = collector.record(
                metric_type=MetricType(metric_type),
                name=metric_name,
                value=value,
                tool_name=tool_name,
                tags=tags
            )
            
            # Also store in history
            self.metrics_history[server_name].append(metric)
            
            return {
                "success": True,
                "metric": asdict(metric),
                "server": server_name
            }
        
        @self.mcp_server.tool()
        def get_server_metrics(
            server_name: str,
            metric_name: Optional[str] = None,
            time_range: str = "last_1h",
            limit: int = 100
        ) -> Dict[str, Any]:
            """Get metrics for a specific server."""
            if server_name not in self.metrics_history:
                return {"error": f"No metrics found for server '{server_name}'"}
            
            metrics = self.metrics_history[server_name]
            
            # Filter by time
            cutoff = self._parse_time_range(time_range)
            filtered_metrics = []
            for metric in metrics:
                metric_time = datetime.fromisoformat(metric.timestamp)
                if metric_time >= cutoff:
                    if metric_name is None or metric.name == metric_name:
                        filtered_metrics.append(metric)
            
            # Apply limit
            filtered_metrics = filtered_metrics[-limit:]
            
            return {
                "server": server_name,
                "metrics": [asdict(m) for m in filtered_metrics],
                "count": len(filtered_metrics),
                "time_range": time_range
            }
        
        @self.mcp_server.tool()
        def analyze_server_performance(
            server_name: str
        ) -> Dict[str, Any]:
            """Analyze performance of an MCP server."""
            if server_name not in self.collectors:
                return {"error": f"Server '{server_name}' not found"}
            
            collector = self.collectors[server_name]
            summary = collector.get_metrics_summary()
            
            # Calculate additional insights
            all_metrics = self.metrics_history.get(server_name, [])
            tool_metrics = {}
            
            for metric in all_metrics:
                if metric.tool_name:
                    tool_metrics.setdefault(metric.tool_name, []).append(metric)
            
            tool_performance = {}
            for tool_name, metrics in tool_metrics.items():
                timer_values = [m.value for m in metrics if m.type == MetricType.TIMER]
                if timer_values:
                    tool_performance[tool_name] = {
                        "call_count": len([m for m in metrics if m.type == MetricType.COUNTER]),
                        "avg_response_time": sum(timer_values) / len(timer_values),
                        "min_response_time": min(timer_values),
                        "max_response_time": max(timer_values)
                    }
            
            return {
                "server": server_name,
                "summary": summary,
                "tool_performance": tool_performance,
                "recommendations": self._generate_recommendations(summary, tool_performance)
            }
        
        @self.mcp_server.tool()
        def compare_servers(
            server_names: List[str],
            metric_name: str
        ) -> Dict[str, Any]:
            """Compare metrics across multiple servers."""
            comparison = {}
            
            for server_name in server_names:
                if server_name in self.metrics_history:
                    server_metrics = [
                        m for m in self.metrics_history[server_name]
                        if m.name == metric_name
                    ]
                    
                    if server_metrics:
                        values = [m.value for m in server_metrics]
                        comparison[server_name] = {
                            "count": len(values),
                            "avg": sum(values) / len(values),
                            "min": min(values),
                            "max": max(values),
                            "recent_value": values[-1] if values else None
                        }
            
            return {
                "metric": metric_name,
                "comparison": comparison,
                "servers_compared": len(comparison)
            }
    
    def _parse_time_range(self, time_range: str) -> datetime:
        """Parse time range string to datetime."""
        now = datetime.now()
        
        if time_range == "last_15m":
            return now - timedelta(minutes=15)
        elif time_range == "last_1h":
            return now - timedelta(hours=1)
        elif time_range == "last_24h":
            return now - timedelta(hours=24)
        elif time_range == "last_7d":
            return now - timedelta(days=7)
        else:
            return now - timedelta(hours=1)
    
    def _generate_recommendations(
        self,
        summary: Dict[str, Any],
        tool_performance: Dict[str, Any]
    ) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []
        
        # Check for high error rates
        error_counter = summary.get("counters", {}).get("errors", 0)
        if error_counter > 100:
            recommendations.append(f"High error count ({error_counter}). Check server logs for issues.")
        
        # Check for slow tools
        for tool_name, perf in tool_performance.items():
            avg_time = perf.get("avg_response_time", 0)
            if avg_time > 1000:  # More than 1 second
                recommendations.append(
                    f"Tool '{tool_name}' is slow (avg {avg_time:.1f}ms). Consider optimization."
                )
        
        # Check memory usage if gauge exists
        memory_usage = summary.get("gauges", {}).get("memory_usage_mb", 0)
        if memory_usage > 500:  # More than 500MB
            recommendations.append(
                f"High memory usage ({memory_usage}MB). Check for memory leaks."
            )
        
        return recommendations