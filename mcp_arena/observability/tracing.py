import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict, field
from contextlib import contextmanager
from enum import Enum

from mcp_arena.mcp.server import BaseMCPServer

class TraceStatus(str, Enum):
    STARTED = "started"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"

@dataclass
class Span:
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    name: str
    server_name: str
    tool_name: str
    start_time: str
    end_time: Optional[str] = None
    duration_ms: Optional[float] = None
    status: TraceStatus = TraceStatus.STARTED
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    error_details: Optional[Dict[str, Any]] = None

@dataclass
class Trace:
    trace_id: str
    root_span_id: str
    server_name: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: Optional[float] = None
    status: TraceStatus = TraceStatus.STARTED
    spans: List[Span] = field(default_factory=list)

class MCPTracer:
    """Distributed tracer for MCP server tool calls."""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
        self.traces: Dict[str, Trace] = {}
        self.spans: Dict[str, Span] = {}
        self.active_traces: Dict[str, Trace] = {}
        self.max_traces = 1000
        
    def start_trace(
        self,
        trace_name: str,
        trace_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Start a new trace."""
        trace_id = trace_id or f"trace_{uuid.uuid4().hex[:8]}"
        root_span_id = f"span_{uuid.uuid4().hex[:8]}"
        
        trace = Trace(
            trace_id=trace_id,
            root_span_id=root_span_id,
            server_name=self.server_name,
            start_time=datetime.now().isoformat(),
            tags=tags or {}
        )
        
        self.traces[trace_id] = trace
        self.active_traces[trace_id] = trace
        
        # Clean old traces if we have too many
        if len(self.traces) > self.max_traces:
            # Remove oldest traces
            trace_ids = list(self.traces.keys())
            for old_id in trace_ids[:len(trace_ids) - self.max_traces]:
                del self.traces[old_id]
                if old_id in self.active_traces:
                    del self.active_traces[old_id]
        
        return trace_id
    
    def start_span(
        self,
        trace_id: str,
        span_name: str,
        tool_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> Span:
        """Start a new span in a trace."""
        if trace_id not in self.traces:
            # Auto-create trace if it doesn't exist
            self.start_trace(f"auto_{span_name}", trace_id)
        
        span_id = f"span_{uuid.uuid4().hex[:8]}"
        span = Span(
            span_id=span_id,
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            name=span_name,
            server_name=self.server_name,
            tool_name=tool_name,
            start_time=datetime.now().isoformat(),
            tags=tags or {}
        )
        
        self.spans[span_id] = span
        self.traces[trace_id].spans.append(span)
        
        return span
    
    def end_span(
        self,
        span_id: str,
        status: TraceStatus = TraceStatus.SUCCESS,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Optional[Span]:
        """End a span."""
        if span_id not in self.spans:
            return None
        
        span = self.spans[span_id]
        span.end_time = datetime.now().isoformat()
        span.status = status
        span.error_details = error_details
        
        # Calculate duration
        start = datetime.fromisoformat(span.start_time)
        end = datetime.fromisoformat(span.end_time)
        span.duration_ms = (end - start).total_seconds() * 1000
        
        return span
    
    def end_trace(
        self,
        trace_id: str,
        status: TraceStatus = TraceStatus.SUCCESS
    ) -> Optional[Trace]:
        """End a trace."""
        if trace_id not in self.traces:
            return None
        
        trace = self.traces[trace_id]
        trace.end_time = datetime.now().isoformat()
        trace.status = status
        
        # Calculate total duration
        start = datetime.fromisoformat(trace.start_time)
        end = datetime.fromisoformat(trace.end_time)
        trace.total_duration_ms = (end - start).total_seconds() * 1000
        
        # Remove from active traces
        if trace_id in self.active_traces:
            del self.active_traces[trace_id]
        
        return trace
    
    @contextmanager
    def span(
        self,
        trace_id: str,
        span_name: str,
        tool_name: str,
        parent_span_id: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ):
        """Context manager for creating spans."""
        span = self.start_span(trace_id, span_name, tool_name, parent_span_id, tags)
        try:
            yield span
            self.end_span(span.span_id, TraceStatus.SUCCESS)
        except Exception as e:
            self.end_span(span.span_id, TraceStatus.ERROR, {"error": str(e)})
            raise
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Get a trace by ID."""
        if trace_id not in self.traces:
            return None
        
        trace = self.traces[trace_id]
        return asdict(trace)
    
    def get_active_traces(self) -> List[Dict[str, Any]]:
        """Get all active traces."""
        return [asdict(trace) for trace in self.active_traces.values()]
    
    def search_traces(
        self,
        tool_name: Optional[str] = None,
        status: Optional[TraceStatus] = None,
        min_duration_ms: Optional[float] = None,
        max_duration_ms: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Search traces by criteria."""
        results = []
        
        for trace in self.traces.values():
            # Check if trace matches criteria
            match = True
            
            if tool_name:
                # Check if any span in the trace uses this tool
                tool_found = any(span.tool_name == tool_name for span in trace.spans)
                if not tool_found:
                    match = False
            
            if status and trace.status != status:
                match = False
            
            if min_duration_ms and trace.total_duration_ms:
                if trace.total_duration_ms < min_duration_ms:
                    match = False
            
            if max_duration_ms and trace.total_duration_ms:
                if trace.total_duration_ms > max_duration_ms:
                    match = False
            
            if match:
                results.append(asdict(trace))
        
        return results

class TracingMCPServer(BaseMCPServer):
    """MCP server for distributed tracing across MCP servers."""
    
    def __init__(self, **kwargs):
        super().__init__(
            name="MCP Tracing Server",
            description="Distributed tracing for MCP server tool calls",
            **kwargs
        )
        self.tracers: Dict[str, MCPTracer] = {}
        
    def _register_tools(self):
        """Register tracing tools."""
        
        @self.mcp_server.tool()
        def register_tracer(
            server_name: str
        ) -> Dict[str, Any]:
            """Register an MCP server for tracing."""
            tracer = MCPTracer(server_name)
            self.tracers[server_name] = tracer
            
            return {
                "success": True,
                "server": server_name,
                "tracer_id": id(tracer),
                "message": f"Tracer registered for {server_name}"
            }
        
        @self.mcp_server.tool()
        def start_server_trace(
            server_name: str,
            trace_name: str,
            trace_id: Optional[str] = None
        ) -> Dict[str, Any]:
            """Start a trace on a server."""
            if server_name not in self.tracers:
                return {"error": f"Server '{server_name}' not registered for tracing"}
            
            tracer = self.tracers[server_name]
            trace_id = tracer.start_trace(trace_name, trace_id)
            
            return {
                "success": True,
                "trace_id": trace_id,
                "server": server_name,
                "trace_name": trace_name
            }
        
        @self.mcp_server.tool()
        def get_trace(
            trace_id: str,
            server_name: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get a trace by ID."""
            if server_name:
                # Search in specific server
                if server_name in self.tracers:
                    tracer = self.tracers[server_name]
                    trace = tracer.get_trace(trace_id)
                    if trace:
                        return {"trace": trace, "found_in": server_name}
            else:
                # Search in all servers
                for s_name, tracer in self.tracers.items():
                    trace = tracer.get_trace(trace_id)
                    if trace:
                        return {"trace": trace, "found_in": s_name}
            
            return {"error": f"Trace '{trace_id}' not found"}
        
        @self.mcp_server.tool()
        def analyze_trace_performance(
            server_name: str,
            trace_id: str
        ) -> Dict[str, Any]:
            """Analyze performance of a specific trace."""
            if server_name not in self.tracers:
                return {"error": f"Server '{server_name}' not found"}
            
            tracer = self.tracers[server_name]
            trace_data = tracer.get_trace(trace_id)
            
            if not trace_data:
                return {"error": f"Trace '{trace_id}' not found"}
            
            # Analyze the trace
            spans = trace_data.get("spans", [])
            if not spans:
                return {"message": "No spans in trace"}
            
            # Find the critical path (longest chain)
            root_span = None
            span_dict = {span["span_id"]: span for span in spans}
            
            for span in spans:
                if span["parent_span_id"] is None:
                    root_span = span
                    break
            
            if not root_span:
                return {"error": "No root span found"}
            
            # Calculate span statistics
            span_durations = [span.get("duration_ms", 0) for span in spans if span.get("duration_ms")]
            
            analysis = {
                "trace_id": trace_id,
                "server": server_name,
                "total_spans": len(spans),
                "total_duration_ms": trace_data.get("total_duration_ms"),
                "span_statistics": {
                    "avg_duration": sum(span_durations) / len(span_durations) if span_durations else 0,
                    "max_duration": max(span_durations) if span_durations else 0,
                    "min_duration": min(span_durations) if span_durations else 0,
                },
                "slowest_spans": [],
                "tool_breakdown": {}
            }
            
            # Find slowest spans
            spans_with_duration = [(span, span.get("duration_ms", 0)) for span in spans]
            spans_with_duration.sort(key=lambda x: x[1], reverse=True)
            analysis["slowest_spans"] = [
                {
                    "span_id": span["span_id"],
                    "name": span["name"],
                    "tool": span["tool_name"],
                    "duration_ms": duration
                }
                for span, duration in spans_with_duration[:5]
            ]
            
            # Group by tool
            for span in spans:
                tool_name = span.get("tool_name", "unknown")
                analysis["tool_breakdown"].setdefault(tool_name, {
                    "count": 0,
                    "total_time": 0
                })
                analysis["tool_breakdown"][tool_name]["count"] += 1
                analysis["tool_breakdown"][tool_name]["total_time"] += span.get("duration_ms", 0)
            
            return analysis
        
        @self.mcp_server.tool()
        def find_slow_traces(
            server_name: str,
            threshold_ms: float = 1000,
            limit: int = 10
        ) -> Dict[str, Any]:
            """Find traces that took longer than threshold."""
            if server_name not in self.tracers:
                return {"error": f"Server '{server_name}' not found"}
            
            tracer = self.tracers[server_name]
            all_traces = []
            
            # Get all traces from the tracer
            # Note: In real implementation, you'd need a method to get all traces
            # For now, we'll return a placeholder
            return {
                "server": server_name,
                "threshold_ms": threshold_ms,
                "message": "Trace search would return slow traces here",
                "sample_criteria": {
                    "min_duration": threshold_ms,
                    "max_results": limit
                }
            }