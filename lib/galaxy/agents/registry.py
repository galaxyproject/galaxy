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
        """Initialize empty registry."""
        self._agents: dict[str, type[BaseGalaxyAgent]] = {}
        self._agent_metadata: dict[str, dict] = {}
        self._disabled: set[str] = set()

    def register(
        self,
        agent_type: str,
        agent_class: type[BaseGalaxyAgent],
        metadata: Optional[dict] = None,
    ):
        """
        Register an agent type.

        Args:
            agent_type: Unique identifier for the agent
            agent_class: Agent class to register
            metadata: Optional metadata about the agent
        """
        if not issubclass(agent_class, BaseGalaxyAgent):
            raise ValueError(f"Agent class must inherit from BaseGalaxyAgent: {agent_class}")

        self._agents[agent_type] = agent_class
        self._agent_metadata[agent_type] = metadata or {}

        log.debug(f"Registered agent: {agent_type} -> {agent_class.__name__}")

    def unregister(self, agent_type: str):
        """Unregister an agent type."""
        if agent_type in self._agents:
            del self._agents[agent_type]
            if agent_type in self._agent_metadata:
                del self._agent_metadata[agent_type]
            log.debug(f"Unregistered agent: {agent_type}")

    def get_agent(self, agent_type: str, deps: GalaxyAgentDependencies) -> BaseGalaxyAgent:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            deps: Dependencies to inject into the agent

        Returns:
            Agent instance

        Raises:
            ValueError: If agent type is not registered
        """
        if agent_type in self._disabled:
            raise ValueError(f"Agent '{agent_type}' is disabled in configuration")
        if agent_type not in self._agents:
            available = list(self._agents.keys())
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {available}")

        agent_class = self._agents[agent_type]

        try:
            return agent_class(deps)
        except (ImportError, TypeError, ValueError):
            log.exception(f"Failed to create agent {agent_type}")
            raise
        except RuntimeError:
            # Covers issues like missing dependencies or configuration problems
            log.exception(f"Runtime error creating agent {agent_type}")
            raise

    def is_registered(self, agent_type: str) -> bool:
        """Check if an agent type is registered."""
        return agent_type in self._agents

    def list_agents(self) -> list[str]:
        """Get list of registered agent types."""
        return list(self._agents.keys())

    def get_agent_metadata(self, agent_type: str) -> dict:
        """Get metadata for an agent type."""
        return self._agent_metadata.get(agent_type, {})

    def get_agent_info(self, agent_type: str) -> dict:
        """
        Get comprehensive information about an agent.

        Returns:
            Dictionary with agent class, metadata, and other info
        """
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
        """Get information for all registered agents."""
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

    def _register_or_disable(registry: AgentRegistry, agent_type: str, agent_class: type[BaseGalaxyAgent]):
        if _is_enabled(agent_type):
            registry.register(agent_type, agent_class)
        else:
            registry._disabled.add(agent_type)
            log.info(f"Agent '{agent_type}' disabled by configuration, skipping registration")

    registry = AgentRegistry()

    # Router is always registered
    if not _is_enabled(AgentType.ROUTER):
        log.warning("Router agent cannot be disabled — ignoring enabled: false")
    registry.register(AgentType.ROUTER, QueryRouterAgent)

    _register_or_disable(registry, AgentType.ERROR_ANALYSIS, ErrorAnalysisAgent)
    _register_or_disable(registry, AgentType.CUSTOM_TOOL, CustomToolAgent)
    _register_or_disable(registry, AgentType.ORCHESTRATOR, WorkflowOrchestratorAgent)
    _register_or_disable(registry, AgentType.TOOL_RECOMMENDATION, ToolRecommendationAgent)
    return registry
