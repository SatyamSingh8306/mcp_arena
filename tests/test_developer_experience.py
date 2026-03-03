"""
Tests for Developer Experience Enhancement features:
- Template Library
- Agent Debugger / Tracing
- Execution Visualization 
- Deployment file generation
"""

import os
import json
import tempfile
import shutil
import pytest


# ─── Template Library Tests ───────────────────────────────────────────────────

class TestTemplateLibrary:
    """Tests for the agent template system."""

    def test_list_templates(self):
        """Templates registry returns available templates."""
        from mcp_arena.templates import list_templates
        templates = list_templates()
        assert isinstance(templates, list)
        assert len(templates) >= 3
        assert "support-bot" in templates
        assert "code-reviewer" in templates
        assert "researcher" in templates

    def test_get_template_valid(self):
        """Getting a valid template returns an instance."""
        from mcp_arena.templates import get_template
        tmpl = get_template("support-bot")
        assert tmpl is not None
        assert tmpl.name == "support-bot"

    def test_get_template_invalid(self):
        """Getting an unknown template raises ValueError."""
        from mcp_arena.templates import get_template
        with pytest.raises(ValueError, match="Unknown template"):
            get_template("nonexistent-template")

    def test_template_info(self):
        """Template get_info() returns correct metadata."""
        from mcp_arena.templates import get_template
        tmpl = get_template("code-reviewer")
        info = tmpl.get_info()
        assert info["name"] == "code-reviewer"
        assert "description" in info
        assert "parameters" in info
        assert isinstance(info["parameters"], list)

    def test_support_bot_properties(self):
        """Support bot template has correct properties."""
        from mcp_arena.templates import get_template
        tmpl = get_template("support-bot")
        assert tmpl.name == "support-bot"
        assert "support" in tmpl.description.lower()
        assert "max_reflections" in tmpl.parameters
        assert "system_prompt" in tmpl.parameters

    def test_code_reviewer_properties(self):
        """Code reviewer template has correct properties."""
        from mcp_arena.templates import get_template
        tmpl = get_template("code-reviewer")
        assert tmpl.name == "code-reviewer"
        assert "root_dir" in tmpl.parameters

    def test_researcher_properties(self):
        """Researcher template has correct properties."""
        from mcp_arena.templates import get_template
        tmpl = get_template("researcher")
        assert tmpl.name == "researcher"
        assert "max_steps" in tmpl.parameters


# ─── Debugger Tests ───────────────────────────────────────────────────────────

class TestAgentDebugger:
    """Tests for the agent debugging/tracing system."""

    def test_create_debugger(self):
        """Debugger can be instantiated."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        assert dbg is not None

    def test_start_trace(self):
        """Starting a trace creates a valid ExecutionTrace."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        trace = dbg.start_trace("test query")
        assert trace.query == "test query"
        assert trace.status == "running"
        assert len(trace.steps) == 0

    def test_start_trace_custom_id(self):
        """Can start a trace with a custom ID."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        trace = dbg.start_trace("q", trace_id="my-trace-1")
        assert trace.trace_id == "my-trace-1"

    def test_log_steps(self):
        """Steps are correctly recorded in order."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q")
        dbg.log_step(trace, StepType.THOUGHT, "thinking...")
        dbg.log_step(trace, StepType.TOOL_CALL, "calculator", tool_name="calc")
        dbg.log_step(trace, StepType.RESPONSE, "answer")
        assert len(trace.steps) == 3
        assert trace.steps[0].step_type == StepType.THOUGHT
        assert trace.steps[1].step_type == StepType.TOOL_CALL
        assert trace.steps[2].step_type == StepType.RESPONSE
        assert trace.steps[0].step_number == 1
        assert trace.steps[2].step_number == 3

    def test_complete_trace(self):
        """Completing a trace sets status and result."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q")
        dbg.log_step(trace, StepType.RESPONSE, "done")
        trace.complete("the result")
        assert trace.status == "completed"
        assert trace.result == "the result"
        assert trace.end_time is not None

    def test_fail_trace(self):
        """Failing a trace sets status correctly."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q")
        trace.fail("something went wrong")
        assert trace.status == "failed"
        assert trace.result == "something went wrong"

    def test_list_traces(self):
        """All traces are listed with summaries."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        dbg.start_trace("query 1")
        dbg.start_trace("query 2")
        traces = dbg.list_traces()
        assert len(traces) == 2

    def test_replay(self):
        """Replay returns all steps in order."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q", trace_id="replay-test")
        dbg.log_step(trace, StepType.THOUGHT, "step1")
        dbg.log_step(trace, StepType.RESPONSE, "step2")
        trace.complete("done")
        
        steps = dbg.replay("replay-test")
        assert len(steps) == 2
        assert steps[0].content == "step1"
        assert steps[1].content == "step2"

    def test_replay_not_found(self):
        """Replay raises error for unknown trace."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        with pytest.raises(ValueError, match="Trace not found"):
            dbg.replay("nonexistent")

    def test_export_trace_json(self):
        """Export produces valid JSON."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q", trace_id="export-test")
        dbg.log_step(trace, StepType.THOUGHT, "thinking")
        trace.complete("done")
        
        exported = dbg.export_trace("export-test")
        data = json.loads(exported)
        assert data["trace_id"] == "export-test"
        assert data["status"] == "completed"
        assert len(data["steps"]) == 1

    def test_token_usage_tracking(self):
        """Token usage is accumulated correctly."""
        from mcp_arena.agent.debugger import TokenUsage
        usage = TokenUsage()
        usage.add(prompt=100, completion=50, cost=0.001)
        usage.add(prompt=200, completion=100, cost=0.002)
        assert usage.prompt_tokens == 300
        assert usage.completion_tokens == 150
        assert usage.total_tokens == 450
        assert abs(usage.estimated_cost_usd - 0.003) < 1e-10

    def test_execution_summary(self):
        """Execution summary identifies bottlenecks."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q", trace_id="summary-test")
        dbg.log_step(trace, StepType.THOUGHT, "fast", duration_ms=5)
        dbg.log_step(trace, StepType.TOOL_CALL, "slow tool", duration_ms=500)
        dbg.log_step(trace, StepType.RESPONSE, "answer", duration_ms=10)
        trace.complete("done")
        
        summary = dbg.get_execution_summary("summary-test")
        assert summary["total_steps"] == 3
        assert summary["bottlenecks"][0]["step"] == 2  # slowest step
        assert summary["bottlenecks"][0]["duration_ms"] == 500

    def test_on_step_callback(self):
        """Callback is invoked for each step."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        recorded = []
        dbg = AgentDebugger(on_step=lambda s: recorded.append(s))
        trace = dbg.start_trace("q")
        dbg.log_step(trace, StepType.THOUGHT, "one")
        dbg.log_step(trace, StepType.RESPONSE, "two")
        assert len(recorded) == 2

    def test_clear_traces(self):
        """Clearing removes all traces."""
        from mcp_arena.agent.debugger import AgentDebugger
        dbg = AgentDebugger()
        dbg.start_trace("a")
        dbg.start_trace("b")
        assert len(dbg.list_traces()) == 2
        dbg.clear()
        assert len(dbg.list_traces()) == 0

    def test_print_trace(self):
        """print_trace returns a readable string."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("test")
        dbg.log_step(trace, StepType.THOUGHT, "hello")
        trace.complete("ok")
        output = dbg.print_trace(trace)
        assert "test" in output
        assert "thought" in output

    def test_trace_timeline(self):
        """Timeline view is correctly structured."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q")
        dbg.log_step(trace, StepType.THOUGHT, "step1", duration_ms=10)
        dbg.log_step(trace, StepType.RESPONSE, "step2", duration_ms=20)
        
        timeline = trace.get_timeline()
        assert len(timeline) == 2
        assert timeline[0]["type"] == "thought"
        assert "relative_time_ms" in timeline[0]

    def test_tool_usage_tracking(self):
        """Tool usage dependency info is correct."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("q")
        dbg.log_step(trace, StepType.TOOL_CALL, "search", tool_name="search", args={"q": "test"})
        dbg.log_step(trace, StepType.TOOL_CALL, "calc", tool_name="calculator", args={"expr": "1+1"})
        
        tools = trace.get_tool_usage()
        assert len(tools) == 2
        assert tools[0]["tool"] == "search"
        assert tools[1]["tool"] == "calculator"


# ─── Visualization Tests ─────────────────────────────────────────────────────

class TestVisualization:
    """Tests for agent behavior visualization."""

    def _make_trace(self):
        """Helper to create a sample trace for testing."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        dbg = AgentDebugger()
        trace = dbg.start_trace("What is 2+2?", trace_id="viz-test")
        dbg.log_step(trace, StepType.THOUGHT, "I need to calculate", duration_ms=5)
        dbg.log_step(trace, StepType.TOOL_CALL, "calculator", 
                     duration_ms=50, tool_name="calculator", args={"expr": "2+2"})
        dbg.log_step(trace, StepType.TOOL_RESULT, "4", 
                     duration_ms=10, tool_name="calculator")
        dbg.log_step(trace, StepType.RESPONSE, "The answer is 4", duration_ms=3)
        trace.complete("The answer is 4")
        return trace

    def test_mermaid_flowchart(self):
        """Mermaid flowchart is generated correctly."""
        from mcp_arena.agent.visualization import generate_mermaid_flowchart
        trace = self._make_trace()
        chart = generate_mermaid_flowchart(trace)
        assert "```mermaid" in chart
        assert "flowchart TD" in chart
        assert "START" in chart
        assert "END" in chart

    def test_timeline_output(self):
        """Timeline output has expected format."""
        from mcp_arena.agent.visualization import generate_timeline
        trace = self._make_trace()
        timeline = generate_timeline(trace)
        assert "Timeline:" in timeline
        assert "viz-test" in timeline
        assert "Bottlenecks" in timeline

    def test_tool_dependency_graph(self):
        """Tool dependency graph is generated."""
        from mcp_arena.agent.visualization import generate_tool_dependency_graph
        trace = self._make_trace()
        graph = generate_tool_dependency_graph(trace)
        assert "```mermaid" in graph
        assert "calculator" in graph

    def test_execution_report(self):
        """Full execution report includes all sections."""
        from mcp_arena.agent.visualization import generate_execution_report
        trace = self._make_trace()
        report = generate_execution_report(trace)
        assert "# Agent Execution Report" in report
        assert "Decision Flowchart" in report
        assert "Execution Timeline" in report
        assert "Tool Usage" in report
        assert "Result" in report

    def test_empty_trace_timeline(self):
        """Timeline handles empty traces."""
        from mcp_arena.agent.debugger import AgentDebugger
        from mcp_arena.agent.visualization import generate_timeline
        dbg = AgentDebugger()
        trace = dbg.start_trace("empty")
        result = generate_timeline(trace)
        assert "No steps recorded" in result

    def test_no_tools_dependency_graph(self):
        """Tool dependency graph handles traces with no tool calls."""
        from mcp_arena.agent.debugger import AgentDebugger, StepType
        from mcp_arena.agent.visualization import generate_tool_dependency_graph
        dbg = AgentDebugger()
        trace = dbg.start_trace("no tools")
        dbg.log_step(trace, StepType.THOUGHT, "thinking only")
        result = generate_tool_dependency_graph(trace)
        assert "No tool calls" in result


# ─── Deployment Tests ─────────────────────────────────────────────────────────

class TestDeployment:
    """Tests for deployment file generation."""

    def test_generate_dockerfile(self):
        """Dockerfile is generated correctly."""
        from mcp_arena.deployment.docker import generate_dockerfile
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_dockerfile(tmpdir)
            assert os.path.exists(path)
            with open(path, "r") as f:
                content = f.read()
            assert "FROM python" in content
            assert "mcp-arena" in content
            assert "EXPOSE" in content

    def test_generate_docker_compose(self):
        """docker-compose.yml is generated correctly."""
        from mcp_arena.deployment.docker import generate_docker_compose
        with tempfile.TemporaryDirectory() as tmpdir:
            path = generate_docker_compose(tmpdir)
            assert os.path.exists(path)
            with open(path, "r") as f:
                content = f.read()
            assert "services:" in content
            assert "mcp-agent" in content

    def test_dockerfile_content(self):
        """Dockerfile has all expected sections."""
        from mcp_arena.deployment.docker import DOCKERFILE_TEMPLATE
        assert "FROM python" in DOCKERFILE_TEMPLATE
        assert "WORKDIR /app" in DOCKERFILE_TEMPLATE
        assert "pip install mcp-arena" in DOCKERFILE_TEMPLATE
        assert "requirements.txt" in DOCKERFILE_TEMPLATE
        assert "EXPOSE" in DOCKERFILE_TEMPLATE
        assert "ENTRYPOINT" in DOCKERFILE_TEMPLATE

    def test_docker_compose_content(self):
        """docker-compose.yml has correct structure."""
        from mcp_arena.deployment.docker import DOCKER_COMPOSE_TEMPLATE
        assert "version:" in DOCKER_COMPOSE_TEMPLATE
        assert "services:" in DOCKER_COMPOSE_TEMPLATE
        assert "OPENAI_API_KEY" in DOCKER_COMPOSE_TEMPLATE
