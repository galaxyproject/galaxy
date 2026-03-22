"""Static agent backend for deterministic testing without LLM calls.

Provides StaticAgent and StaticAgentRegistry that return canned responses
from YAML rules. Swap at the DI container level — no mocks, no pydantic-ai.
"""

import re
from typing import (
    Any,
    Optional,
)

import yaml

from .base import (
    ActionSuggestion,
    AgentResponse,
    BaseGalaxyAgent,
    GalaxyAgentDependencies,
)
from .registry import AgentRegistry


class StaticAgent(BaseGalaxyAgent):
    """Agent that returns canned responses from YAML rules.

    Subclasses BaseGalaxyAgent but skips pydantic-ai Agent creation entirely.
    Only process() is meaningful — all other BaseGalaxyAgent methods are stubs.
    """

    agent_type = "static"  # overridden per-instance

    def __init__(
        self,
        agent_type_str: str,
        rules: list[dict[str, Any]],
        fallback: dict[str, Any],
        defaults: dict[str, Any],
    ):
        # Intentionally skip super().__init__() — no pydantic-ai Agent needed.
        self.agent_type = agent_type_str
        self._rules = rules
        self._fallback = fallback
        self._defaults = defaults

    def _create_agent(self):
        raise NotImplementedError("StaticAgent does not use pydantic-ai")

    def get_system_prompt(self) -> str:
        return ""

    async def process(self, query: str, context: Optional[dict[str, Any]] = None) -> AgentResponse:
        for rule in self._rules:
            if self._rule_matches(rule.get("match", {}), query, context):
                return self._make_response(rule["response"])
        return self._make_response(self._fallback)

    def _rule_matches(self, match: dict[str, Any], query: str, context: Optional[dict[str, Any]]) -> bool:
        if "agent_type" in match and match["agent_type"] != self.agent_type:
            return False
        if "query" in match and not re.search(match["query"], query):
            return False
        if "context" in match:
            if not context:
                return False
            for field, pattern in match["context"].items():
                if field not in context or not re.search(pattern, str(context[field])):
                    return False
        return True

    def _make_response(self, resp: dict[str, Any]) -> AgentResponse:
        raw_suggestions = resp.get("suggestions", [])
        suggestions = [ActionSuggestion(**s) for s in raw_suggestions]
        return AgentResponse(
            content=resp.get("content", self._fallback.get("content", "")),
            confidence=resp.get("confidence", self._defaults.get("confidence", "medium")),
            agent_type=resp.get("agent_type", self.agent_type),
            suggestions=suggestions,
            metadata={**resp.get("metadata", {}), "static_backend": True},
            reasoning=resp.get("reasoning"),
        )


class StaticAgentRegistry(AgentRegistry):
    """Registry that returns StaticAgent instances from YAML config.

    Subclasses AgentRegistry so it's type-compatible with the DI container.
    """

    def __init__(self, config_path: str):
        super().__init__()
        with open(config_path) as f:
            self._config: dict[str, Any] = yaml.safe_load(f) or {}
        self._rules: list[dict[str, Any]] = self._config.get("rules", [])
        self._fallback: dict[str, Any] = self._config.get("fallback", {})
        self._defaults: dict[str, Any] = self._config.get("defaults", {})

        # Collect known agent_types from rules
        self._known_types: set[str] = set()
        for rule in self._rules:
            match = rule.get("match", {})
            if "agent_type" in match:
                self._known_types.add(match["agent_type"])

    def get_agent(self, agent_type: str, deps: GalaxyAgentDependencies) -> StaticAgent:
        """Return a StaticAgent that matches rules for this agent_type."""
        applicable = [r for r in self._rules if r.get("match", {}).get("agent_type", agent_type) == agent_type]
        return StaticAgent(agent_type, applicable, self._fallback, self._defaults)

    def is_registered(self, agent_type: str) -> bool:
        return agent_type in self._known_types or bool(self._fallback)

    def list_agents(self) -> list[str]:
        return sorted(self._known_types)

    def get_agent_info(self, agent_type: str) -> dict[str, Any]:
        return {
            "agent_type": agent_type,
            "class_name": "StaticAgent",
            "module": "galaxy.agents.static_backend",
            "metadata": {"static_backend": True},
            "description": "Static test agent",
        }

    def list_agent_info(self) -> list[dict[str, Any]]:
        return [self.get_agent_info(t) for t in sorted(self._known_types)]
