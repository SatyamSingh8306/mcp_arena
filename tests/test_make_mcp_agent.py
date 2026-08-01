"""Test the make_mcp_agent builder and the ToolRegistry."""
from unittest.mock import MagicMock

import pytest


class FakeMCPServer:
    """Stand-in for BaseMCPServer that controls its `__class__.__module__`."""

    def __init__(self, name="srv", transport="stdio", host="127.0.0.1", port=8000, module="audio"):
        self.name = name
        self.transport = transport
        self.host = host
        self.port = port
        # Pretend to be mcp_arena.presents.<module> so _config_for picks it up.
        self.__class__ = type(
            "FakeMCPServerCls",
            (),
            {"__module__": f"mcp_arena.presents.{module}"},
        )


class TestConfigFor:
    def test_stdio_config_uses_python_module_invocation(self):
        from mcp_arena.agent.builder import _config_for

        cfg = _config_for(FakeMCPServer(transport="stdio", module="audio"))
        assert cfg["transport"] == "stdio"
        assert cfg["args"] == ["-m", "mcp_arena.presents.audio"]
        assert cfg["command"].endswith("python") or cfg["command"].endswith("python.exe")

    def test_http_streamable_config(self):
        from mcp_arena.agent.builder import _config_for

        cfg = _config_for(FakeMCPServer(transport="streamable-http", host="0.0.0.0", port=9000))
        assert cfg["transport"] == "streamable_http"
        assert cfg["url"] == "http://0.0.0.0:9000/mcp"

    def test_sse_config(self):
        from mcp_arena.agent.builder import _config_for

        cfg = _config_for(FakeMCPServer(transport="sse", port=7000))
        assert cfg["transport"] == "sse"
        assert cfg["url"].endswith("/sse")

    def test_unknown_transport_raises(self):
        from mcp_arena.agent.builder import _config_for

        with pytest.raises(ValueError, match="Unsupported transport"):
            _config_for(FakeMCPServer(transport="carrier-pigeon"))


class TestMakeMcpAgent:
    @pytest.mark.asyncio
    async def test_requires_at_least_one_server(self):
        from mcp_arena.agent import make_mcp_agent

        with pytest.raises(ValueError, match="at least one"):
            await make_mcp_agent("openai:gpt-4o", [])

    @pytest.mark.asyncio
    async def test_returns_create_agent_result(self, monkeypatch):
        """make_mcp_agent should call MultiServerMCPClient.get_tools() and forward to create_agent."""
        fake_agent = MagicMock(name="compiled_agent")
        fake_tools = [MagicMock(name="tool_a"), MagicMock(name="tool_b")]

        async def fake_get_tools(self):
            return fake_tools

        monkeypatch.setattr(
            "langchain_mcp_adapters.client.MultiServerMCPClient.get_tools", fake_get_tools
        )

        captured = {}

        def fake_create_agent(model, tools, *, system_prompt=None, **kwargs):
            captured["model"] = model
            captured["tools"] = tools
            captured["system_prompt"] = system_prompt
            captured["kwargs"] = kwargs
            return fake_agent

        monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)

        llm = MagicMock(name="llm")
        srv_a = FakeMCPServer(name="alpha", transport="stdio")
        srv_b = FakeMCPServer(name="beta", transport="stdio")

        from mcp_arena.agent import make_mcp_agent

        agent = await make_mcp_agent(
            llm,
            [srv_a, srv_b],
            system_prompt="hi",
            state_schema=None,
        )

        assert agent is fake_agent
        assert captured["model"] is llm
        assert captured["tools"] == fake_tools
        assert captured["system_prompt"] == "hi"
        assert captured["kwargs"] == {"state_schema": None}

    @pytest.mark.asyncio
    async def test_name_filter_drops_unlisted_tools(self, monkeypatch):
        tool_a, tool_b = MagicMock(name="a"), MagicMock(name="b")
        tool_a.name = "keep_me"
        tool_b.name = "drop_me"

        async def fake_get_tools(self):
            return [tool_a, tool_b]

        monkeypatch.setattr(
            "langchain_mcp_adapters.client.MultiServerMCPClient.get_tools", fake_get_tools
        )

        captured = {}

        def fake_create_agent(model, tools, **kwargs):
            captured["tools"] = tools
            return MagicMock()

        monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)

        from mcp_arena.agent import make_mcp_agent

        await make_mcp_agent(
            "openai:gpt-4o",
            [FakeMCPServer()],
            names=["keep_me"],
        )

        assert [t.name for t in captured["tools"]] == ["keep_me"]

    @pytest.mark.asyncio
    async def test_forwards_arbitrary_kwargs_to_create_agent(self, monkeypatch):
        """Anything not handled by make_mcp_agent itself should land on create_agent."""
        async def fake_get_tools(self):
            return [MagicMock(name="t")]

        monkeypatch.setattr(
            "langchain_mcp_adapters.client.MultiServerMCPClient.get_tools", fake_get_tools
        )

        captured = {}

        def fake_create_agent(model, tools, *, system_prompt=None, **kwargs):
            captured["system_prompt"] = system_prompt
            captured["kwargs"] = kwargs
            return MagicMock()

        monkeypatch.setattr("langchain.agents.create_agent", fake_create_agent)

        from mcp_arena.agent import make_mcp_agent

        checkpoint = MagicMock(name="checkpointer")
        store = MagicMock(name="store")
        middleware = [MagicMock(name="mw")]

        class MyState: ...
        class MyContext: ...
        class MyResponseFormat: ...

        await make_mcp_agent(
            "openai:gpt-4o",
            [FakeMCPServer()],
            system_prompt="hi",
            checkpointer=checkpoint,
            store=store,
            middleware=middleware,
            state_schema=MyState,
            context_schema=MyContext,
            response_format=MyResponseFormat,
            debug=True,
            name="test_agent",
            interrupt_before=["tools"],
            interrupt_after=["model"],
        )

        kw = captured["kwargs"]
        assert kw["checkpointer"] is checkpoint
        assert kw["store"] is store
        assert kw["middleware"] is middleware
        assert kw["state_schema"] is MyState
        assert kw["context_schema"] is MyContext
        assert kw["response_format"] is MyResponseFormat
        assert kw["debug"] is True
        assert kw["name"] == "test_agent"
        assert kw["interrupt_before"] == ["tools"]
        assert kw["interrupt_after"] == ["model"]
        assert captured["system_prompt"] == "hi"


class TestToolRegistry:
    def test_register_server_pulls_named_tools(self):
        from mcp_arena.agent import ToolRegistry

        def add(a, b):
            "Add two numbers."
            return a + b

        server = MagicMock()
        server.name = "math"
        server._registered_tools = {"add": add}

        r = ToolRegistry().register_server(server)
        assert r.names() == ["add"]
        spec = r.list()[0]
        assert spec.source == "math"
        assert "Add" in spec.description

    def test_keep_and_drop_chain(self):
        from mcp_arena.agent import ToolRegistry

        r = ToolRegistry()
        for name in ("a", "b", "c"):
            r._tools[name] = MagicMock(name=f"spec-{name}")
        r.keep("a", "c").drop("c")
        assert r.names() == ["a"]

    def test_rename_updates_spec_name(self):
        from mcp_arena.agent import ToolRegistry

        spec = MagicMock()
        spec.name = "old"
        r = ToolRegistry()
        r._tools["old"] = spec
        r.rename("old", "new")
        assert r.names() == ["new"]
        assert spec.name == "new"

    def test_to_openai_emits_function_schema(self):
        from mcp_arena.agent import ToolRegistry, ToolSpec

        r = ToolRegistry()
        r._tools["foo"] = ToolSpec(
            name="foo",
            description="foo desc",
            source="srv",
            function=lambda: None,
            parameters={"type": "object", "properties": {"x": {"type": "integer"}}},
        )
        schema = r.to_openai()[0]
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "foo"
        assert schema["function"]["parameters"]["properties"]["x"]["type"] == "integer"

    def test_get_callables_returns_name_to_function(self):
        from mcp_arena.agent import ToolRegistry, ToolSpec

        def add(a, b):
            return a + b

        r = ToolRegistry()
        r._tools["add"] = ToolSpec(
            name="add", description="", source="srv", function=add, parameters={}
        )
        assert r.get_callables()["add"](2, 3) == 5

    def test_from_source_keeps_only_one_server(self):
        from mcp_arena.agent import ToolRegistry, ToolSpec

        r = ToolRegistry()
        r._tools["a"] = ToolSpec(name="a", description="", source="x", function=lambda: None, parameters={})
        r._tools["b"] = ToolSpec(name="b", description="", source="y", function=lambda: None, parameters={})
        r.from_source("x")
        assert r.names() == ["a"]
