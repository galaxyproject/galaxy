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
from .data_analysis import DataAnalysisAgent
# from .dspy_agent import DSPyGalaxyAgent
from .error_analysis import ErrorAnalysisAgent
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
    "DataAnalysisAgent",
    # "DataAnalysisDSPyAgent",
]

# Global agent registry instance
agent_registry = AgentRegistry()

# Register default agents
agent_registry.register(AgentType.ROUTER, QueryRouterAgent)
agent_registry.register(AgentType.ERROR_ANALYSIS, ErrorAnalysisAgent)
agent_registry.register(AgentType.CUSTOM_TOOL, CustomToolAgent)
agent_registry.register(AgentType.ORCHESTRATOR, WorkflowOrchestratorAgent)
agent_registry.register(AgentType.TOOL_RECOMMENDATION, ToolRecommendationAgent)
agent_registry.register(AgentType.DATA_ANALYSIS, DataAnalysisAgent)
# agent_registry.register(AgentType.DATA_ANALYSIS_DSPY, DataAnalysisDSPyAgent)  # Disabled while DSPy agent is offline.
