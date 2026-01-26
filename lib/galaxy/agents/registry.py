"""
Agent registry for managing available AI agents.
"""

import logging
from typing import (
    Optional,
)

from .base import (
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

log = logging.getLogger(__name__)


class AgentRegistry:
    """Registry for managing available AI agents."""

    def __init__(self):
        self._agents: dict[str, type[BaseGalaxyAgent]] = {}
        self._agent_metadata: dict[str, dict] = {}

    def register(
        self,
        agent_type: str,
        agent_class: type[BaseGalaxyAgent],
        metadata: Optional[dict] = None,
    ):
        if not issubclass(agent_class, BaseGalaxyAgent):
            raise ValueError(f"Agent class must inherit from BaseGalaxyAgent: {agent_class}")

        self._agents[agent_type] = agent_class
        self._agent_metadata[agent_type] = metadata or {}

        log.debug(f"Registered agent: {agent_type} -> {agent_class.__name__}")

    def unregister(self, agent_type: str):
        if agent_type in self._agents:
            del self._agents[agent_type]
            if agent_type in self._agent_metadata:
                del self._agent_metadata[agent_type]
            log.debug(f"Unregistered agent: {agent_type}")

    def get_agent(self, agent_type: str, deps: GalaxyAgentDependencies) -> BaseGalaxyAgent:
        if agent_type not in self._agents:
            available = list(self._agents.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available}")

        agent_class = self._agents[agent_type]

        try:
            return agent_class(deps)
        except (ImportError, TypeError, ValueError, RuntimeError):
            log.exception(f"Failed to create agent {agent_type}")
            raise

    def is_registered(self, agent_type: str) -> bool:
        return agent_type in self._agents

    def list_agents(self) -> list[str]:
        return list(self._agents.keys())

    def get_agent_metadata(self, agent_type: str) -> dict:
        return self._agent_metadata.get(agent_type, {})

    def get_agent_info(self, agent_type: str) -> dict:
        """Get info about an agent including class, metadata, and description."""
        if agent_type not in self._agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_class = self._agents[agent_type]
        metadata = self._agent_metadata.get(agent_type, {})

        return {
            "agent_type": agent_type,
            "class_name": agent_class.__name__,
            "module": agent_class.__module__,
            "metadata": metadata,
            "description": getattr(agent_class, "__doc__", "").strip() if agent_class.__doc__ else None,
        }

    def list_agent_info(self) -> list[dict]:
        return [self.get_agent_info(agent_type) for agent_type in self._agents.keys()]


def build_default_registry(config=None) -> AgentRegistry:
    """Create an AgentRegistry with all default Galaxy agents.

    Args:
        config: Optional app config. When provided, agents with
            ``enabled: false`` in ``inference_services`` are skipped.
            The router agent is always registered regardless of config.
    """
    from .base import AgentType
    from .custom_tool import CustomToolAgent
    from .error_analysis import ErrorAnalysisAgent
    from .gtn_training import GTNTrainingAgent
    from .history import HistoryAgent
    from .orchestrator import WorkflowOrchestratorAgent
    from .router import QueryRouterAgent
    from .tools import ToolRecommendationAgent

    inference_config: dict = {}
    if config is not None:
        inference_config = getattr(config, "inference_services", {}) or {}

    def _is_enabled(agent_type: str) -> bool:
        agent_cfg = inference_config.get(agent_type, {})
        if isinstance(agent_cfg, dict):
            return agent_cfg.get("enabled", True)
        return True

    def _register_if_enabled(registry: AgentRegistry, agent_type: str, agent_class: type[BaseGalaxyAgent]):
        if _is_enabled(agent_type):
            registry.register(agent_type, agent_class)
        else:
            log.info(f"Agent '{agent_type}' disabled by configuration, skipping registration")

    registry = AgentRegistry()

    # Router is always registered
    if not _is_enabled(AgentType.ROUTER):
        log.warning("Router agent cannot be disabled — ignoring enabled: false")
    registry.register(AgentType.ROUTER, QueryRouterAgent)

    _register_if_enabled(registry, AgentType.ERROR_ANALYSIS, ErrorAnalysisAgent)
    _register_if_enabled(registry, AgentType.CUSTOM_TOOL, CustomToolAgent)
    _register_if_enabled(registry, AgentType.ORCHESTRATOR, WorkflowOrchestratorAgent)
    _register_if_enabled(registry, AgentType.TOOL_RECOMMENDATION, ToolRecommendationAgent)
    _register_if_enabled(registry, AgentType.HISTORY, HistoryAgent)
    _register_if_enabled(registry, AgentType.GTN_TRAINING, GTNTrainingAgent)
    return registry
