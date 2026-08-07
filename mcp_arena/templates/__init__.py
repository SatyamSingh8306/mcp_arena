from .base import AgentTemplate
from .standard import SupportBotTemplate, CodeReviewerTemplate, ResearcherTemplate

__all__ = ["AgentTemplate", "SupportBotTemplate", "CodeReviewerTemplate", "ResearcherTemplate"]

_template_registry = {
    "support-bot": SupportBotTemplate,
    "code-reviewer": CodeReviewerTemplate,
    "researcher": ResearcherTemplate
}

def get_template(name: str) -> AgentTemplate:
    """Get a template instance by name."""
    template_class = _template_registry.get(name)
    if not template_class:
        raise ValueError(f"Unknown template: {name}. Available: {list(_template_registry.keys())}")
    return template_class()

def list_templates() -> list[str]:
    """List available template names."""
    return list(_template_registry.keys())
