"""
Agent registry for managing available AI agents.
"""

import logging
from typing import (
    Dict,
    List,
    Optional,
    Type,
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
        self._agents: Dict[str, Type[BaseGalaxyAgent]] = {}
        self._agent_metadata: Dict[str, Dict] = {}

    def register(self, agent_type: str, agent_class: Type[BaseGalaxyAgent], metadata: Optional[Dict] = None):
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

    def list_agents(self) -> List[str]:
        """Get list of registered agent types."""
        return list(self._agents.keys())

    def get_agent_metadata(self, agent_type: str) -> Dict:
        """Get metadata for an agent type."""
        return self._agent_metadata.get(agent_type, {})

    def get_agent_info(self, agent_type: str) -> Dict:
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

    def list_agent_info(self) -> List[Dict]:
        """Get information for all registered agents."""
        return [self.get_agent_info(agent_type) for agent_type in self._agents.keys()]


# Global registry instance
_global_registry = AgentRegistry()


def get_global_registry() -> AgentRegistry:
    """Get the global agent registry instance."""
    return _global_registry


def register_agent(agent_type: str, agent_class: Type[BaseGalaxyAgent], metadata: Optional[Dict] = None):
    """Register an agent in the global registry."""
    _global_registry.register(agent_type, agent_class, metadata)


def get_agent(agent_type: str, deps: GalaxyAgentDependencies) -> BaseGalaxyAgent:
    """Create an agent from the global registry."""
    return _global_registry.get_agent(agent_type, deps)
