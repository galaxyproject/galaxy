"""Unit tests for the static agent backend (YAML rule matching)."""

import os
import tempfile

import pytest
import yaml

from galaxy.agents.base import (
    AgentResponse,
    BaseGalaxyAgent,
    ConfidenceLevel,
)
from galaxy.agents.static_backend import (
    StaticAgent,
    StaticAgentRegistry,
)


@pytest.fixture
def sample_config():
    return {
        "defaults": {"confidence": "medium"},
        "rules": [
            {
                "match": {"agent_type": "router", "query": "(?i)hello|hi"},
                "response": {
                    "content": "Hello! How can I help?",
                    "confidence": "high",
                    "agent_type": "router",
                },
            },
            {
                "match": {"agent_type": "router", "query": "(?i)rna.?seq"},
                "response": {
                    "content": "Galaxy has RNA-seq tools including HISAT2.",
                    "confidence": "high",
                    "agent_type": "router",
                },
            },
            {
                "match": {"agent_type": "error_analysis"},
                "response": {
                    "content": "This error is a tool configuration issue.",
                    "confidence": "high",
                    "agent_type": "error_analysis",
                },
            },
            {
                "match": {"agent_type": "router"},
                "response": {
                    "content": "I can help with Galaxy workflows and tools.",
                    "confidence": "medium",
                    "agent_type": "router",
                },
            },
        ],
        "fallback": {
            "content": "Static backend: no matching rule.",
            "confidence": "low",
            "agent_type": "unknown",
        },
    }


@pytest.fixture
def yaml_config_path(sample_config):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        yaml.dump(sample_config, f)
        path = f.name
    yield path
    os.unlink(path)


@pytest.fixture
def static_registry(yaml_config_path):
    return StaticAgentRegistry(yaml_config_path)


# --- StaticAgent tests ---


class TestStaticAgent:
    def _make_agent(self, agent_type, rules, fallback=None, defaults=None):
        fallback = fallback or {"content": "fallback", "confidence": "low", "agent_type": "unknown"}
        defaults = defaults or {"confidence": "medium"}
        return StaticAgent(agent_type, rules, fallback, defaults)

    @pytest.mark.asyncio
    async def test_exact_agent_type_match(self):
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {"content": "Router response", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("anything")
        assert response.content == "Router response"
        assert response.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_query_regex_match(self):
        rules = [
            {
                "match": {"query": "(?i)hello|hi"},
                "response": {"content": "Greeting!", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("Hello there")
        assert response.content == "Greeting!"

    @pytest.mark.asyncio
    async def test_query_regex_case_insensitive(self):
        rules = [
            {
                "match": {"query": "(?i)hello"},
                "response": {"content": "Hi!", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("HELLO WORLD")
        assert response.content == "Hi!"

    @pytest.mark.asyncio
    async def test_combined_match(self):
        """Both agent_type and query must match (AND semantics)."""
        rules = [
            {
                "match": {"agent_type": "router", "query": "(?i)hello"},
                "response": {"content": "Router hello", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        # Both match
        response = await agent.process("hello")
        assert response.content == "Router hello"

    @pytest.mark.asyncio
    async def test_combined_match_query_mismatch(self):
        """agent_type matches but query doesn't — should fall through."""
        rules = [
            {
                "match": {"agent_type": "router", "query": "(?i)hello"},
                "response": {"content": "Router hello", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("goodbye")
        assert response.content == "fallback"

    @pytest.mark.asyncio
    async def test_fallthrough_to_catchall(self):
        """Specific rule fails, generic catchall matches."""
        rules = [
            {
                "match": {"agent_type": "router", "query": "(?i)hello"},
                "response": {"content": "Hello!", "confidence": "high", "agent_type": "router"},
            },
            {
                "match": {"agent_type": "router"},
                "response": {"content": "Generic router", "confidence": "medium", "agent_type": "router"},
            },
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("something else")
        assert response.content == "Generic router"
        assert response.confidence == ConfidenceLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_fallback_when_nothing_matches(self):
        rules = [
            {
                "match": {"agent_type": "error_analysis"},
                "response": {"content": "Error help", "confidence": "high", "agent_type": "error_analysis"},
            }
        ]
        fallback = {"content": "No match found.", "confidence": "low", "agent_type": "unknown"}
        agent = self._make_agent("router", rules, fallback=fallback)
        response = await agent.process("anything")
        assert response.content == "No match found."
        assert response.confidence == ConfidenceLevel.LOW

    @pytest.mark.asyncio
    async def test_static_backend_metadata_flag(self):
        """Every response should have static_backend: True in metadata."""
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {"content": "Hello", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test")
        assert response.metadata.static_backend is True

    @pytest.mark.asyncio
    async def test_fallback_also_has_metadata_flag(self):
        agent = self._make_agent("router", [])
        response = await agent.process("test")
        assert response.metadata.static_backend is True

    @pytest.mark.asyncio
    async def test_defaults_applied(self):
        """confidence from defaults block used when rule omits it."""
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {"content": "No confidence set", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules, defaults={"confidence": "medium"})
        response = await agent.process("test")
        assert response.confidence == ConfidenceLevel.MEDIUM

    @pytest.mark.asyncio
    async def test_response_is_agent_response(self):
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {"content": "Hello", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test")
        assert isinstance(response, AgentResponse)

    @pytest.mark.asyncio
    async def test_first_matching_rule_wins(self):
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {"content": "First", "confidence": "high", "agent_type": "router"},
            },
            {
                "match": {"agent_type": "router"},
                "response": {"content": "Second", "confidence": "medium", "agent_type": "router"},
            },
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test")
        assert response.content == "First"

    def test_static_agent_is_base_galaxy_agent(self):
        agent = self._make_agent("router", [])
        assert isinstance(agent, BaseGalaxyAgent)

    def test_create_agent_raises(self):
        agent = self._make_agent("router", [])
        with pytest.raises(NotImplementedError):
            agent._create_agent()

    def test_get_system_prompt_empty(self):
        agent = self._make_agent("router", [])
        assert agent.get_system_prompt() == ""

    @pytest.mark.asyncio
    async def test_context_rule_fails_when_no_context(self):
        """Rule requiring context should NOT match when context is None."""
        rules = [
            {
                "match": {"agent_type": "router", "context": {"page_content": "methods"}},
                "response": {"content": "Context match", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test", context=None)
        assert response.content == "fallback"

    @pytest.mark.asyncio
    async def test_context_rule_matches_when_context_present(self):
        rules = [
            {
                "match": {"agent_type": "router", "context": {"page_content": "(?i)methods"}},
                "response": {"content": "Context match", "confidence": "high", "agent_type": "router"},
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test", context={"page_content": "## Methods\nSome content"})
        assert response.content == "Context match"

    @pytest.mark.asyncio
    async def test_suggestions_preserved(self):
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {
                    "content": "Hello",
                    "confidence": "high",
                    "agent_type": "router",
                    "suggestions": [
                        {
                            "action_type": "save_tool",
                            "description": "Save tool",
                            "parameters": {"tool_id": "test", "tool_yaml": "test: true"},
                            "confidence": "high",
                            "priority": 1,
                        }
                    ],
                },
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test")
        assert len(response.suggestions) == 1
        assert response.suggestions[0].action_type.value == "save_tool"
        assert response.suggestions[0].parameters["tool_id"] == "test"

    @pytest.mark.asyncio
    async def test_reasoning_preserved(self):
        rules = [
            {
                "match": {"agent_type": "router"},
                "response": {
                    "content": "Hello",
                    "confidence": "high",
                    "agent_type": "router",
                    "reasoning": "Because reasons",
                },
            }
        ]
        agent = self._make_agent("router", rules)
        response = await agent.process("test")
        assert response.reasoning == "Because reasons"


# --- StaticAgentRegistry tests ---


class TestStaticAgentRegistry:
    def test_list_agents(self, static_registry):
        agents = static_registry.list_agents()
        assert "router" in agents
        assert "error_analysis" in agents

    def test_get_agent_returns_static_agent(self, static_registry):
        # deps not used by StaticAgent, pass None
        agent = static_registry.get_agent("router", None)
        assert isinstance(agent, StaticAgent)
        assert isinstance(agent, BaseGalaxyAgent)

    def test_is_registered_known_type(self, static_registry):
        assert static_registry.is_registered("router") is True
        assert static_registry.is_registered("error_analysis") is True

    def test_is_registered_unknown_with_fallback(self, static_registry):
        # Unknown type but fallback exists → registered
        assert static_registry.is_registered("nonexistent") is True

    def test_is_registered_unknown_no_fallback(self, yaml_config_path):
        # Modify config to remove fallback
        with open(yaml_config_path) as f:
            config = yaml.safe_load(f)
        config.pop("fallback", None)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
            yaml.dump(config, f)
            no_fallback_path = f.name
        try:
            registry = StaticAgentRegistry(no_fallback_path)
            assert registry.is_registered("nonexistent") is False
        finally:
            os.unlink(no_fallback_path)

    def test_get_agent_info(self, static_registry):
        info = static_registry.get_agent_info("router")
        assert info["agent_type"] == "router"
        assert info["class_name"] == "StaticAgent"
        assert info["metadata"]["static_backend"] is True

    def test_list_agent_info(self, static_registry):
        infos = static_registry.list_agent_info()
        assert len(infos) >= 2
        types = [i["agent_type"] for i in infos]
        assert "router" in types
        assert "error_analysis" in types

    @pytest.mark.asyncio
    async def test_end_to_end_query(self, static_registry):
        """Registry → get_agent → process → response."""
        agent = static_registry.get_agent("router", None)
        response = await agent.process("Hello!")
        assert "Hello" in response.content or "help" in response.content.lower()
        assert response.confidence == ConfidenceLevel.HIGH

    @pytest.mark.asyncio
    async def test_end_to_end_fallback(self, static_registry):
        agent = static_registry.get_agent("unknown_type", None)
        response = await agent.process("xyzzy")
        assert "no matching rule" in response.content.lower()

    def test_static_registry_is_agent_registry(self, static_registry):
        from galaxy.agents.registry import AgentRegistry

        assert isinstance(static_registry, AgentRegistry)
