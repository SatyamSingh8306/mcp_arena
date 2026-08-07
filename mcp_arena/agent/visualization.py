"""
Agent behavior visualization helpers for MCP Arena.

Generates text-based and structured representations of agent execution:
- Decision flowcharts (Mermaid markdown)
- Timeline views showing execution bottlenecks
- Dependency graphs of tool usage
- Multi-agent interaction graphs
"""

from typing import Any, Dict, List, Optional
from mcp_arena.agent.debugger import ExecutionTrace, StepType


def generate_mermaid_flowchart(trace: ExecutionTrace) -> str:
    """
    Generate a Mermaid flowchart diagram of the agent's decision path.
    
    Can be rendered in GitHub markdown, Jupyter notebooks, or any
    Mermaid-compatible viewer.
    
    Args:
        trace: The execution trace to visualize
        
    Returns:
        Mermaid diagram as a string
    """
    lines = ["```mermaid", "flowchart TD"]
    
    node_shapes = {
        StepType.THOUGHT: ('([" ', ' "])', "thought"),
        StepType.ACTION: ('[" ', ' "]', "action"),
        StepType.OBSERVATION: ('[/" ', ' "/]', "observation"),
        StepType.REFLECTION: ('{{ " ', ' " }}', "reflection"),
        StepType.PLAN: ('>" ', ' "]', "plan"),
        StepType.TOOL_CALL: ('["🔧 ', ' "]', "tool_call"),
        StepType.TOOL_RESULT: ('["📤 ', ' "]', "tool_result"),
        StepType.RESPONSE: ('[["💬 ', ' "]]', "response"),
        StepType.ERROR: ('["❌ ', ' "]', "error"),
    }
    
    lines.append(f'    START(("🚀 Query"))')
    
    for i, step in enumerate(trace.steps):
        shape = node_shapes.get(step.step_type, ('[" ', ' "]', "default"))
        summary = step.content[:50].replace('"', "'")
        node_id = f"S{step.step_number}"
        lines.append(f'    {node_id}{shape[0]}{step.step_type.value}: {summary}{shape[1]}')
    
    # Edges
    if trace.steps:
        lines.append(f'    START --> S{trace.steps[0].step_number}')
        for i in range(len(trace.steps) - 1):
            src = f"S{trace.steps[i].step_number}"
            dst = f"S{trace.steps[i+1].step_number}"
            label = ""
            if trace.steps[i].duration_ms > 0:
                label = f"|{trace.steps[i].duration_ms:.0f}ms|"
            lines.append(f'    {src} -->{label} {dst}')
        
        lines.append(f'    S{trace.steps[-1].step_number} --> END(("✅ Done"))')
    
    # Styling
    lines.append("")
    lines.append("    classDef thought fill:#e1f5fe,stroke:#01579b")
    lines.append("    classDef action fill:#fff3e0,stroke:#e65100")
    lines.append("    classDef tool_call fill:#f3e5f5,stroke:#4a148c")
    lines.append("    classDef tool_result fill:#e8f5e9,stroke:#1b5e20")
    lines.append("    classDef response fill:#e8eaf6,stroke:#1a237e")
    lines.append("    classDef error fill:#ffebee,stroke:#b71c1c")
    lines.append("    classDef reflection fill:#fff8e1,stroke:#f57f17")
    
    for step in trace.steps:
        shape = node_shapes.get(step.step_type)
        if shape:
            class_name = shape[2]
            lines.append(f"    class S{step.step_number} {class_name}")
    
    lines.append("```")
    return "\n".join(lines)


def generate_timeline(trace: ExecutionTrace) -> str:
    """
    Generate a text-based timeline view showing execution bottlenecks.
    
    Args:
        trace: The execution trace to visualize
        
    Returns:
        Formatted timeline string
    """
    if not trace.steps:
        return "No steps recorded."
    
    lines = []
    lines.append(f"Timeline: {trace.trace_id}")
    lines.append(f"Total: {trace.duration_ms:.1f}ms | Steps: {len(trace.steps)}")
    lines.append("=" * 70)
    
    max_duration = max((s.duration_ms for s in trace.steps), default=1) or 1
    bar_width = 40
    
    for step in trace.steps:
        bar_len = int((step.duration_ms / max_duration) * bar_width) if max_duration > 0 else 0
        bar = "█" * bar_len + "░" * (bar_width - bar_len)
        
        icon = {
            StepType.THOUGHT: "💭",
            StepType.ACTION: "⚡",
            StepType.TOOL_CALL: "🔧",
            StepType.TOOL_RESULT: "📤",
            StepType.RESPONSE: "💬",
            StepType.ERROR: "❌",
            StepType.REFLECTION: "🔄",
            StepType.OBSERVATION: "👁",
            StepType.PLAN: "📋",
        }.get(step.step_type, "•")
        
        label = step.content[:30]
        time_str = f"{step.duration_ms:>8.1f}ms"
        
        lines.append(f"  {icon} {step.step_number:>2}. [{bar}] {time_str}  {label}")
    
    # Highlight bottlenecks  
    sorted_steps = sorted(trace.steps, key=lambda s: s.duration_ms, reverse=True)
    slow_steps = [s for s in sorted_steps if s.duration_ms > 0][:3]
    
    if slow_steps:
        lines.append("")
        lines.append("Bottlenecks:")
        for s in slow_steps:
            lines.append(f"  ⚠ Step {s.step_number} ({s.step_type.value}): {s.duration_ms:.1f}ms")
    
    return "\n".join(lines)


def generate_tool_dependency_graph(trace: ExecutionTrace) -> str:
    """
    Generate a Mermaid diagram showing tool usage dependencies.
    
    Args:
        trace: The execution trace to build the graph from
        
    Returns:
        Mermaid diagram string
    """
    tool_calls = trace.get_tool_usage()
    
    if not tool_calls:
        return "No tool calls recorded."
    
    lines = ["```mermaid", "graph LR"]
    
    # Count tool usage
    tool_counts: Dict[str, int] = {}
    for tc in tool_calls:
        name = tc["tool"]
        tool_counts[name] = tool_counts.get(name, 0) + 1
    
    # Nodes for each unique tool
    for tool_name, count in tool_counts.items():
        safe_name = tool_name.replace(" ", "_").replace("-", "_")
        lines.append(f'    {safe_name}["{tool_name} ({count}x)"]')
    
    # Show sequential dependencies between tool calls
    for i in range(len(tool_calls) - 1):
        src = tool_calls[i]["tool"].replace(" ", "_").replace("-", "_")
        dst = tool_calls[i + 1]["tool"].replace(" ", "_").replace("-", "_")
        lines.append(f'    {src} --> {dst}')
    
    lines.append("```")
    return "\n".join(lines)


def generate_execution_report(trace: ExecutionTrace) -> str:
    """
    Generate a full Markdown execution report combining all visualizations.
    
    Args:
        trace: The execution trace to report on
        
    Returns:
        Markdown formatted report
    """
    sections = []
    
    sections.append(f"# Agent Execution Report")
    sections.append(f"**Trace ID:** {trace.trace_id}")
    sections.append(f"**Query:** {trace.query}")
    sections.append(f"**Status:** {trace.status}")
    sections.append(f"**Duration:** {trace.duration_ms:.1f}ms")
    sections.append(f"**Steps:** {len(trace.steps)}")
    sections.append(f"**Tokens:** {trace.token_usage.total_tokens}")
    sections.append(f"**Est. Cost:** ${trace.token_usage.estimated_cost_usd:.6f}")
    sections.append("")
    
    sections.append("## Decision Flowchart")
    sections.append(generate_mermaid_flowchart(trace))
    sections.append("")
    
    sections.append("## Execution Timeline")
    sections.append("```")
    sections.append(generate_timeline(trace))
    sections.append("```")
    sections.append("")
    
    tool_graph = generate_tool_dependency_graph(trace)
    if "No tool calls" not in tool_graph:
        sections.append("## Tool Usage")
        sections.append(tool_graph)
        sections.append("")
    
    if trace.result:
        sections.append("## Result")
        sections.append(f"```\n{trace.result}\n```")
    
    return "\n".join(sections)
