from langgraph.graph.state import StateGraph,CompiledStateGraph
from langgraph.graph import START,END
from langgraph.prebuilt import ToolNode
from langgraph.types import Command,Interrupt


class BaseAgent(StateGraph):
    def __init__(self, state_schema, context_schema = None, *, input_schema = None, output_schema = None, **kwargs):
        super().__init__(state_schema, context_schema, input_schema=input_schema, output_schema=output_schema, **kwargs)


