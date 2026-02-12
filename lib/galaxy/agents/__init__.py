"""
Galaxy AI Agents Module

Provides AI agent functionality built on pydantic-ai for Galaxy.
"""

from .base import (
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from .custom_tool import CustomToolAgent
from .error_analysis import ErrorAnalysisAgent
from .history_analyzer import HistoryAnalyzerAgent
from .orchestrator import WorkflowOrchestratorAgent
from .registry import AgentRegistry
from .router import QueryRouterAgent
from .tools import ToolRecommendationAgent

__all__ = [
    "AgentType",
    "BaseGalaxyAgent",
    "GalaxyAgentDependencies",
    "AgentRegistry",
    "QueryRouterAgent",
    "ErrorAnalysisAgent",
    "CustomToolAgent",
    "WorkflowOrchestratorAgent",
    "ToolRecommendationAgent",
    "HistoryAnalyzerAgent",
]

agent_registry = AgentRegistry()

agent_registry.register(AgentType.ROUTER, QueryRouterAgent)
agent_registry.register(AgentType.ERROR_ANALYSIS, ErrorAnalysisAgent)
agent_registry.register(AgentType.CUSTOM_TOOL, CustomToolAgent)
agent_registry.register(AgentType.ORCHESTRATOR, WorkflowOrchestratorAgent)
agent_registry.register(AgentType.TOOL_RECOMMENDATION, ToolRecommendationAgent)
agent_registry.register(AgentType.HISTORY_ANALYZER, HistoryAnalyzerAgent)
