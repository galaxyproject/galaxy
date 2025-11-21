"""
Galaxy AI Agents Module

This module provides AI agent functionality built on pydantic-ai for Galaxy.
Agents provide specialized assistance for workflows, tool errors, data quality, and more.
"""

from .base import (
    AgentType,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from .custom_tool import CustomToolAgent
from .error_analysis import ErrorAnalysisAgent
from .orchestrator import WorkflowOrchestratorAgent
from .registry import (
    AgentRegistry,
    build_default_registry,
)
from .router import QueryRouterAgent
from .tools import ToolRecommendationAgent
try:
    from .data_analysis import DataAnalysisAgent
except ImportError:  # pragma: no cover - optional dependency (e.g. itsdangerous)
    DataAnalysisAgent = None  # type: ignore[assignment]

__all__ = [
    "AgentType",
    "BaseGalaxyAgent",
    "GalaxyAgentDependencies",
    "AgentRegistry",
    "build_default_registry",
    "QueryRouterAgent",
    "ErrorAnalysisAgent",
    "CustomToolAgent",
    "WorkflowOrchestratorAgent",
    "ToolRecommendationAgent",
    "DataAnalysisAgent",
]
