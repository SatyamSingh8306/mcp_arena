from typing import List, Dict, Any, Callable
from mcp_arena.agent.factory import AgentBuilder
from mcp_arena.agent.interfaces import IAgent
from mcp_arena.templates.base import AgentTemplate

# Import tools
from mcp_arena.tools.filesystem import FileSystemTool
from mcp_arena.tools.calculator import CalculatorTool
from mcp_arena.tools.time_tool import TimeTool
from mcp_arena.tools.web import WebTool

# Optional search tool if available
try:
    from mcp_arena.tools.search import SearchTool
except ImportError:
    SearchTool = None


class SupportBotTemplate(AgentTemplate):
    """A helpful support bot using reflection for better responses."""
    
    @property
    def name(self) -> str:
        return "support-bot"
        
    @property
    def description(self) -> str:
        return "A conversational agent designed for customer support with reflection capabilities."
    
    @property
    def parameters(self) -> List[str]:
        return ["max_reflections", "system_prompt"]
        
    def build(self, **kwargs) -> IAgent:
        max_reflections = kwargs.get("max_reflections", 2)
        system_prompt = kwargs.get("system_prompt", "You are a helpful and patient support assistant.")
        
        # Using reflection agent for thoughtful responses
        return (AgentBuilder("reflection")
                .with_memory("conversation", max_reflections=max_reflections)
                .with_config(system_prompt=system_prompt)
                .build())


class CodeReviewerTemplate(AgentTemplate):
    """An agent that can read files and provide code reviews."""
    
    @property
    def name(self) -> str:
        return "code-reviewer"
        
    @property
    def description(self) -> str:
        return "An agent equipped with file system tools to review code."
    
    @property
    def parameters(self) -> List[str]:
        return ["root_dir", "system_prompt", "max_steps"]
        
    def build(self, **kwargs) -> IAgent:
        root_dir = kwargs.get("root_dir", ".")
        max_steps = kwargs.get("max_steps", 10)
        sys_prompt = kwargs.get("system_prompt", 
            "You are an expert code reviewer. Analyze the code for bugs, security issues, and style improvements."
        )
        
        return (AgentBuilder("react")
                .with_memory("conversation", max_steps=max_steps)
                .with_tool(FileSystemTool(base_path=root_dir))
                .with_config(system_prompt=sys_prompt)
                .build())


class ResearcherTemplate(AgentTemplate):
    """An agent that can search web and analyze information."""
    
    @property
    def name(self) -> str:
        return "researcher"
        
    @property
    def description(self) -> str:
        return "An agent with web access, time, and calculation capabilities for research tasks."
    
    @property
    def parameters(self) -> List[str]:
        return ["system_prompt", "max_steps"]
        
    def build(self, **kwargs) -> IAgent:
        max_steps = kwargs.get("max_steps", 15)
        sys_prompt = kwargs.get("system_prompt", 
            "You are a thorough researcher. Use tools to find accurate information and synthesize it."
        )
        
        builder = (AgentBuilder("react")
                   .with_memory("conversation", max_steps=max_steps)
                   .with_tool(WebTool())
                   .with_tool(CalculatorTool())
                   .with_tool(TimeTool())
                   .with_config(system_prompt=sys_prompt))
                   
        # If the user provides a search function
        search_func = kwargs.get("search_function")
        if search_func and SearchTool:
            builder.with_tool(SearchTool(search_function=search_func))
            
        return builder.build()
