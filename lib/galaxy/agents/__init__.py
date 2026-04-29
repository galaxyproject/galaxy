"""
Galaxy AI Agents Module

AI agents built on pydantic-ai for Galaxy.
"""

from .base import (
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from .custom_tool import CustomToolAgent
from .error_analysis import ErrorAnalysisAgent
from .history import HistoryAgent
from .orchestrator import WorkflowOrchestratorAgent
from .page_assistant import PageAssistantAgent
from .registry import (
    AgentRegistry,
    build_default_registry,
)
from .router import QueryRouterAgent
from .tools import ToolRecommendationAgent

__all__ = [
    "AgentType",
    "BaseGalaxyAgent",
    "GalaxyAgentDependencies",
    "AgentRegistry",
    "build_default_registry",
    "QueryRouterAgent",
    "ErrorAnalysisAgent",
    "CustomToolAgent",
    "PageAssistantAgent",
    "WorkflowOrchestratorAgent",
    "ToolRecommendationAgent",
    "HistoryAgent",
]
