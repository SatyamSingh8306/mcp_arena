"""
Debugging and tracing module for MCP Arena agents.

Provides step-by-step execution tracing, token/cost tracking,
and time-travel replay capabilities for agent interactions.
"""

import time
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Types of agent execution steps."""
    THOUGHT = "thought"
    ACTION = "action"
    OBSERVATION = "observation"
    REFLECTION = "reflection"
    PLAN = "plan"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    RESPONSE = "response"
    ERROR = "error"


@dataclass
class ExecutionStep:
    """A single step in the agent's execution trace."""
    step_number: int
    step_type: StepType
    content: str
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "step_type": self.step_type.value,
            "content": self.content,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


@dataclass
class TokenUsage:
    """Tracks token consumption and costs."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    
    def add(self, prompt: int = 0, completion: int = 0, cost: float = 0.0):
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += prompt + completion
        self.estimated_cost_usd += cost

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
        }


@dataclass
class ExecutionTrace:
    """Complete execution trace for one agent interaction."""
    trace_id: str
    query: str
    steps: List[ExecutionStep] = field(default_factory=list)
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: str = "running"
    result: Optional[str] = None
    
    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
        
    def add_step(self, step_type: StepType, content: str, 
                 duration_ms: float = 0.0, **metadata) -> ExecutionStep:
        step = ExecutionStep(
            step_number=len(self.steps) + 1,
            step_type=step_type,
            content=content,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        self.steps.append(step)
        return step
    
    def complete(self, result: str):
        self.end_time = time.time()
        self.status = "completed"
        self.result = result
        
    def fail(self, error: str):
        self.end_time = time.time()
        self.status = "failed"
        self.result = error
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "status": self.status,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "duration_ms": round(self.duration_ms, 2),
            "steps": [s.to_dict() for s in self.steps],
            "token_usage": self.token_usage.to_dict(),
            "result": self.result,
        }
    
    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get a timeline view suitable for visualization."""
        timeline = []
        for step in self.steps:
            timeline.append({
                "step": step.step_number,
                "type": step.step_type.value,
                "duration_ms": step.duration_ms,
                "summary": step.content[:100] + ("..." if len(step.content) > 100 else ""),
                "relative_time_ms": (step.timestamp - self.start_time) * 1000,
            })
        return timeline
    
    def get_tool_usage(self) -> List[Dict[str, Any]]:
        """Get a dependency graph of tool usage."""
        tools = []
        for step in self.steps:
            if step.step_type == StepType.TOOL_CALL:
                tool_name = step.metadata.get("tool_name", "unknown")
                tools.append({
                    "step": step.step_number,
                    "tool": tool_name,
                    "args": step.metadata.get("args", {}),
                    "duration_ms": step.duration_ms,
                })
        return tools


class AgentDebugger:
    """
    Real-time debugger for agent execution.
    
    Features:
    - Step-through execution tracing
    - Live token/cost tracking
    - Request/response inspector
    - Time-travel replay of interactions
    
    Usage:
        debugger = AgentDebugger()
        
        # Start a trace
        trace = debugger.start_trace("What is 2+2?")
        trace.add_step(StepType.THOUGHT, "I need to calculate 2+2")
        trace.add_step(StepType.TOOL_CALL, "calculator", tool_name="calculator", args={"expr": "2+2"})
        trace.add_step(StepType.TOOL_RESULT, "4", tool_name="calculator")
        trace.add_step(StepType.RESPONSE, "The answer is 4")
        trace.complete("The answer is 4")
        
        # Inspect
        debugger.print_trace(trace)
        
        # Replay
        for step in debugger.replay(trace.trace_id):
            print(step)
    """
    
    def __init__(self, 
                 enable_logging: bool = True,
                 breakpoints: Optional[List[StepType]] = None,
                 on_step: Optional[Callable[[ExecutionStep], None]] = None):
        self._traces: Dict[str, ExecutionTrace] = {}
        self._enable_logging = enable_logging
        self._breakpoints = set(breakpoints or [])
        self._on_step_callback = on_step
        self._trace_counter = 0
    
    def start_trace(self, query: str, trace_id: Optional[str] = None) -> ExecutionTrace:
        """Start a new execution trace."""
        self._trace_counter += 1
        if trace_id is None:
            trace_id = f"trace_{self._trace_counter}_{int(time.time())}"
        
        trace = ExecutionTrace(trace_id=trace_id, query=query)
        self._traces[trace_id] = trace
        
        if self._enable_logging:
            logger.info(f"[DEBUG] Started trace {trace_id} for query: {query[:80]}")
        
        return trace
    
    def log_step(self, trace: ExecutionTrace, step_type: StepType, 
                 content: str, duration_ms: float = 0.0, **metadata) -> ExecutionStep:
        """Log an execution step and invoke callbacks."""
        step = trace.add_step(step_type, content, duration_ms, **metadata)
        
        if self._enable_logging:
            logger.info(
                f"[DEBUG] [{trace.trace_id}] Step {step.step_number} "
                f"({step_type.value}): {content[:80]}"
            )
        
        if self._on_step_callback:
            self._on_step_callback(step)
            
        # Breakpoint support
        if step_type in self._breakpoints:
            logger.warning(
                f"[BREAKPOINT] Paused at step {step.step_number} ({step_type.value})")
        
        return step
    
    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Retrieve a trace by ID."""
        return self._traces.get(trace_id)
    
    def list_traces(self) -> List[Dict[str, Any]]:
        """List all traces with summary info."""
        return [
            {
                "trace_id": t.trace_id,
                "query": t.query[:60],
                "status": t.status,
                "steps": len(t.steps),
                "duration_ms": round(t.duration_ms, 2),
                "tokens": t.token_usage.total_tokens,
            }
            for t in self._traces.values()
        ]
    
    def replay(self, trace_id: str) -> List[ExecutionStep]:
        """
        Time-travel replay: return all steps of a past trace in order.
        Useful for debugging what the agent did.
        """
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        return list(trace.steps)
    
    def export_trace(self, trace_id: str, format: str = "json") -> str:
        """Export a trace to JSON string."""
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
        return json.dumps(trace.to_dict(), indent=2)
    
    def get_execution_summary(self, trace_id: str) -> Dict[str, Any]:
        """Get a summary of execution including bottlenecks."""
        trace = self._traces.get(trace_id)
        if not trace:
            raise ValueError(f"Trace not found: {trace_id}")
            
        step_durations = [(s.step_number, s.step_type.value, s.duration_ms) 
                          for s in trace.steps if s.duration_ms > 0]
        step_durations.sort(key=lambda x: x[2], reverse=True)
        
        type_counts = {}
        for step in trace.steps:
            t = step.step_type.value
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "trace_id": trace_id,
            "total_steps": len(trace.steps),
            "total_duration_ms": round(trace.duration_ms, 2),
            "step_type_counts": type_counts,
            "bottlenecks": [
                {"step": s[0], "type": s[1], "duration_ms": s[2]} 
                for s in step_durations[:5]
            ],
            "token_usage": trace.token_usage.to_dict(),
        }
    
    def print_trace(self, trace: ExecutionTrace) -> str:
        """Format a trace for console display."""
        lines = []
        lines.append(f"=== Trace: {trace.trace_id} ===")
        lines.append(f"Query: {trace.query}")
        lines.append(f"Status: {trace.status}")
        lines.append(f"Duration: {trace.duration_ms:.1f}ms")
        lines.append(f"Steps: {len(trace.steps)}")
        lines.append(f"Tokens: {trace.token_usage.total_tokens}")
        lines.append("")
        
        for step in trace.steps:
            prefix = {
                StepType.THOUGHT: "💭",
                StepType.ACTION: "⚡",
                StepType.OBSERVATION: "👁",
                StepType.REFLECTION: "🔄",
                StepType.PLAN: "📋",
                StepType.TOOL_CALL: "🔧",
                StepType.TOOL_RESULT: "📤",
                StepType.RESPONSE: "💬",
                StepType.ERROR: "❌",
            }.get(step.step_type, "•")
            
            line = f"  {prefix} Step {step.step_number} [{step.step_type.value}]"
            if step.duration_ms > 0:
                line += f" ({step.duration_ms:.1f}ms)"
            line += f": {step.content[:120]}"
            lines.append(line)
        
        output = "\n".join(lines)
        return output
    
    def clear(self):
        """Clear all traces."""
        self._traces.clear()
        self._trace_counter = 0
