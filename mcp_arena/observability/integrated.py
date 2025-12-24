"""
Integrated observability server that combines logging, metrics, and tracing.
"""

from .logging import MCPLogger, LogLevel
from .metrics import MCPMetricsCollector, MetricType
from .tracing import MCPTracer, TraceStatus
import time 
from typing import Dict, Any

class IntegratedObservabilityServer:
    """Integrated observability for an MCP server."""
    
    def __init__(self, server_name: str, server_type: str):
        self.server_name = server_name
        self.server_type = server_type
        
        # Initialize all observability components
        self.logger = MCPLogger(server_name, server_type)
        self.metrics = MCPMetricsCollector(server_name)
        self.tracer = MCPTracer(server_name)
        
        # Track current trace context
        self.current_trace_id = None
        self.current_span_id = None
    
    def instrument_tool(self, tool_func, tool_name: str):
        """Decorator to instrument an MCP tool with observability."""
        def instrumented_tool(*args, **kwargs):
            # Start trace if not already started
            if not self.current_trace_id:
                self.current_trace_id = self.tracer.start_trace(
                    f"tool_call_{tool_name}"
                )
            
            # Start span for this tool call
            with self.tracer.span(
                self.current_trace_id,
                f"call_{tool_name}",
                tool_name,
                parent_span_id=self.current_span_id
            ) as span:
                self.current_span_id = span.span_id
                
                # Log tool start
                self.logger.info(
                    f"Starting tool: {tool_name}",
                    tool_name=tool_name,
                    request_id=self.current_trace_id
                )
                
                # Record metrics start
                start_time = time.time()
                self.metrics.increment_counter(
                    f"tool_{tool_name}_calls",
                    tool_name=tool_name
                )
                
                try:
                    # Execute the tool
                    result = tool_func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # Record success
                    self.metrics.record_timer(
                        f"tool_{tool_name}_duration",
                        duration_ms,
                        tool_name=tool_name
                    )
                    self.logger.info(
                        f"Tool {tool_name} completed successfully in {duration_ms:.1f}ms",
                        tool_name=tool_name,
                        request_id=self.current_trace_id,
                        duration_ms=duration_ms
                    )
                    
                    return result
                    
                except Exception as e:
                    # Record error
                    duration_ms = (time.time() - start_time) * 1000
                    self.metrics.increment_counter(
                        f"tool_{tool_name}_errors",
                        tool_name=tool_name
                    )
                    self.logger.error(
                        f"Tool {tool_name} failed after {duration_ms:.1f}ms: {str(e)}",
                        tool_name=tool_name,
                        request_id=self.current_trace_id,
                        duration_ms=duration_ms,
                        error_details={"error": str(e), "type": type(e).__name__}
                    )
                    raise
        
        return instrumented_tool
    
    def get_observability_summary(self) -> Dict[str, Any]:
        """Get comprehensive observability summary."""
        return {
            "server": self.server_name,
            "type": self.server_type,
            "logging": {
                "buffer_size": len(self.logger.log_buffer),
                "recent_levels": [log.level.value for log in self.logger.log_buffer[-10:]]
            },
            "metrics": self.metrics.get_metrics_summary(),
            "tracing": {
                "total_traces": len(self.tracer.traces),
                "active_traces": len(self.tracer.active_traces)
            }
        }