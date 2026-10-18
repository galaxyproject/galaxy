"""
Agent registry for managing available AI agents.
"""

import logging
from typing import TYPE_CHECKING

from galaxy.agents.base import (
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)

if TYPE_CHECKING:
    from galaxy.config import GalaxyAppConfiguration

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
        metadata: dict | None = None,
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

    def get_capability_blurb(self, agent_type: str) -> str | None:
        """Return the agent's user-facing capability blurb, or None.

        Returns None when the agent type is not registered (e.g. disabled in this
        deployment, since disabled agents are never registered) or defines no blurb.
        The router uses this to advertise only capabilities that actually work here.
        A registry that never populates ``_agents`` (the static test backend) returns
        None for every type -- correct, since no live router prompt is rendered there.
        """
        agent_class = self._agents.get(agent_type)
        return getattr(agent_class, "capability_blurb", None) if agent_class else None

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
    from galaxy.agents.base import AgentType
    from galaxy.agents.custom_tool import CustomToolAgent
    from galaxy.agents.error_analysis import ErrorAnalysisAgent
    from galaxy.agents.gtn_training import GTNTrainingAgent
    from galaxy.agents.history import HistoryAgent
    from galaxy.agents.orchestrator import WorkflowOrchestratorAgent
    from galaxy.agents.page_assistant import PageAssistantAgent
    from galaxy.agents.router import QueryRouterAgent
    from galaxy.agents.tools import ToolRecommendationAgent

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
    _register_if_enabled(registry, AgentType.PAGE_ASSISTANT, PageAssistantAgent)
    return registry


def build_registry(config: "GalaxyAppConfiguration") -> AgentRegistry:
    """Build an AgentRegistry based on config.

    Uses StaticAgentRegistry when inference_services.static_responses is set,
    otherwise builds the default registry with real agents.
    """
    inference_config = getattr(config, "inference_services", None) or {}
    static_responses = inference_config.get("static_responses") if isinstance(inference_config, dict) else None
    if static_responses:
        # galaxy.agents.static_backend imports AgentRegistry from this module.
        from galaxy.agents.static_backend import StaticAgentRegistry

        log.info(f"Static agent backend loaded: {static_responses}")
        return StaticAgentRegistry(static_responses)
    return build_default_registry(config)
