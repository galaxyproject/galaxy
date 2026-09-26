"""API tests for Galaxy AI agents.

Tests run against any Galaxy with agents configured (static or real LLM).
Assertions adapt based on llm_registry_type: strong for "static", weak for "default".

## Running (auto-started server with static backend):
    ./run_tests.sh -api lib/galaxy_test/api/test_agents.py

## Running against an external Galaxy with a real LLM:
    ./run_tests.sh -api lib/galaxy_test/api/test_agents.py \
        --external_url http://localhost:8080/ \
        --external_user_key YOUR_API_KEY
"""

from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_agents,
)
from ._framework import ApiTestCase


class TestAgentsApi(ApiTestCase):
    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        config = self._get("configuration").json()
        self._registry_type = config.get("llm_registry_type", "default")

    @property
    def _is_static(self) -> bool:
        return self._registry_type == "static"

    def _query_agent(self, query: str, agent_type: str = "auto") -> dict:
        response = self._post(
            "ai/agents/query",
            data={"query": query, "agent_type": agent_type},
            json=True,
        )
        self._assert_status_code_is_ok(response)
        return response.json()

    @skip_without_agents
    def test_configuration_reports_agents(self):
        """GET /api/configuration reports llm_api_configured."""
        config = self._get("configuration").json()
        assert config.get("llm_api_configured") is True
        if self._is_static:
            assert config.get("llm_registry_type") == "static"

    @skip_without_agents
    def test_list_agents(self):
        """GET /api/ai/agents returns agent list."""
        response = self._get("ai/agents")
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "agents" in data
        agent_types = [a["agent_type"] for a in data["agents"]]
        assert len(agent_types) > 0
        if self._is_static:
            assert "router" in agent_types
            assert "error_analysis" in agent_types

    @skip_without_agents
    def test_list_agents_includes_custom_tool(self):
        """GET /api/ai/agents includes custom_tool agent."""
        response = self._get("ai/agents")
        self._assert_status_code_is_ok(response)
        agent_types = [a["agent_type"] for a in response.json()["agents"]]
        assert "custom_tool" in agent_types

    @skip_without_agents
    def test_chat_greeting(self):
        """Query with greeting returns appropriate response."""
        data = self._query_agent("Hello!")
        content = data["response"]["content"]
        assert len(content) > 0
        if self._is_static:
            assert "Hello" in content

    @skip_without_agents
    def test_chat_domain_query(self):
        """Query about RNA-seq returns domain-specific response."""
        data = self._query_agent("How do I analyze RNA-seq data?")
        content = data["response"]["content"]
        assert len(content) > 0
        if self._is_static:
            assert "HISAT2" in content

    @skip_without_agents
    def test_chat_fallback(self):
        """Generic query gets a response."""
        data = self._query_agent("Tell me about Galaxy")
        content = data["response"]["content"]
        assert len(content) > 0
        if self._is_static:
            assert "Galaxy" in content

    @skip_without_agents
    def test_response_metadata(self):
        """Agent responses include metadata."""
        data = self._query_agent("Hello!")
        metadata = data["response"].get("metadata", {})
        assert isinstance(metadata, dict)
        if self._is_static:
            assert metadata.get("static_backend") is True

    @skip_without_agents
    def test_custom_tool_agent(self):
        """custom_tool agent returns tool metadata."""
        data = self._query_agent("Create a tool that counts lines", agent_type="custom_tool")
        resp = data["response"]
        assert "metadata" in resp
        assert "tool_id" in resp["metadata"]
        if self._is_static:
            assert resp["metadata"]["tool_id"] == "line-counter"
            assert "wc -l" in resp["metadata"]["tool_yaml"]
            suggestions = resp.get("suggestions", [])
            assert len(suggestions) >= 1
            save = [s for s in suggestions if s["action_type"] == "save_tool"]
            assert len(save) == 1
            assert save[0]["parameters"]["tool_id"] == "line-counter"
            assert save[0]["parameters"]["tool_yaml"]

    @skip_without_agents
    def test_error_analysis_agent(self):
        """error_analysis agent returns error-related response."""
        data = self._query_agent("My job failed with exit code 1", agent_type="error_analysis")
        content = data["response"]["content"]
        assert len(content) > 0
        if self._is_static:
            assert "error" in content.lower() or "configuration" in content.lower()
