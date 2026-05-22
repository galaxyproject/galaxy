"""Test Galaxy AI agents API.

Requires a configured LLM — skipped unless GALAXY_TEST_ENABLE_LIVE_LLM=1.
For deterministic tests without LLM, see test_static_agent_backend.py.

## Running:
    export GALAXY_TEST_AI_API_KEY="your-api-key"
    export GALAXY_TEST_AI_MODEL="llama-4-scout"
    export GALAXY_TEST_AI_API_BASE_URL="http://localhost:4000/v1/"
    export GALAXY_TEST_ENABLE_LIVE_LLM=1
    pytest test/integration/test_agents.py -v
"""

import asyncio
import logging
import os

import pytest
from fastmcp import (
    Client,
    FastMCP,
)
from fastmcp.exceptions import ToolError

from galaxy.agents.operations import AgentOperationsManager
from galaxy.managers.context import ProvidesUserContext
from galaxy.util.unittest_utils import pytestmark_live_llm
from galaxy.webapps.galaxy.api.mcp import get_mcp_app
from galaxy_test.base.populators import (
    DatasetPopulator,
    TOOL_WITH_SHELL_COMMAND,
    WorkflowPopulator,
)
from galaxy_test.driver.integration_util import IntegrationTestCase

log = logging.getLogger(__name__)


class AgentIntegrationTestCase(IntegrationTestCase):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        # AI/LLM configuration for agent tests
        if ai_api_key := os.environ.get("GALAXY_TEST_AI_API_KEY"):
            config["ai_api_key"] = ai_api_key
        if ai_api_base_url := os.environ.get("GALAXY_TEST_AI_API_BASE_URL"):
            config["ai_api_base_url"] = ai_api_base_url
        if ai_model := os.environ.get("GALAXY_TEST_AI_MODEL"):
            config["ai_model"] = ai_model


class TestAgentsApi(AgentIntegrationTestCase):
    """Test the Galaxy AI agents API endpoints.

    These tests verify API structure and static backend responses.
    For tests of actual agent logic with mocked LLMs, see test/unit/app/test_agents.py.
    """

    def test_list_agents(self):
        response = self._get("ai/agents")
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "agents" in data
        agents = data["agents"]
        assert len(agents) > 0
        agent_types = [a["agent_type"] for a in agents]
        assert "router" in agent_types
        assert "custom_tool" in agent_types
        assert "error_analysis" in agent_types


# ============================================================================
# LIVE LLM TEST SUITE - Requires configured LLM
# ============================================================================


@pytestmark_live_llm
class TestAgentsApiLiveLLM(AgentIntegrationTestCase):
    """Test Galaxy AI agents API with real LLM.

    These tests require a configured LLM and will be skipped unless
    GALAXY_TEST_ENABLE_LIVE_LLM=1 is set.
    """

    def test_query_agent_auto_routing_live(self):
        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a BWA-MEM tool for paired-end reads",
                "agent_type": "auto",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        assert "agent_type" in data["response"]
        # Router should route this to custom_tool
        assert data.get("routing_info", {}).get("selected_agent") == "custom_tool"

    def test_query_custom_tool_agent_live(self):
        response = self._post(
            "ai/agents/query",
            data={
                "query": "Create a simple tool that counts lines in a file",
                "agent_type": "custom_tool",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        agent_response = data["response"]
        assert "content" in agent_response
        assert "metadata" in agent_response
        assert "tool_id" in agent_response["metadata"]
        assert "tool_yaml" in agent_response["metadata"]
        # Check that it created something sensible
        tool_yaml = agent_response["metadata"]["tool_yaml"]
        assert "command" in tool_yaml or "shell_command" in tool_yaml

    def test_error_analysis_endpoint_live(self):
        response = self._post(
            "ai/agents/error-analysis",
            data={
                "query": "My BWA job failed with exit code 137 and stderr shows 'Killed'",
                "error_details": {"tool_id": "bwa_mem", "exit_code": 137},
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "content" in data
        assert "confidence" in data
        # Should mention memory or OOM since exit code 137 is SIGKILL
        content = data["content"].lower()
        assert any(word in content for word in ["memory", "kill", "resource", "oom"])

    def test_custom_tool_endpoint_live(self):
        response = self._post(
            "ai/agents/custom-tool",
            data={
                "query": "Create a tool that counts sequences in a FASTA file",
            },
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "content" in data
        assert "metadata" in data
        # Should generate tool YAML
        metadata = data["metadata"]
        assert "tool_yaml" in metadata or "tool_id" in metadata

    def test_chat_endpoint_live(self):
        response = self._post(
            "chat?query=What%20tools%20are%20available%20for%20RNA-seq%3F&agent_type=auto",
            data={},
            json=True,
        )
        self._assert_status_code_is_ok(response)
        data = response.json()
        assert "response" in data
        # Should return some content about RNA-seq
        assert len(data["response"]) > 0

    def test_chat_history_endpoint(self):
        response = self._get("chat/history?limit=5")
        self._assert_status_code_is_ok(response)
        data = response.json()
        # Should return a list (may be empty)
        assert isinstance(data, list)


# ============================================================================
# AgentOperationsManager ID Encoding Tests
# ============================================================================


class TestAgentOperationsManagerEncoding(AgentIntegrationTestCase):
    """Test AgentOperationsManager ID encoding.

    These tests verify that the _encode_ids_in_response helper correctly
    encodes Galaxy database IDs so agents can use them in subsequent API calls.
    """

    def _make_ops(self):
        class MinimalTrans(ProvidesUserContext):
            def __init__(self, app):
                self._app = app

            @property
            def app(self):
                return self._app

            @property
            def user(self):
                return None

            @property
            def url_builder(self):
                return None

            @property
            def security(self):
                return self._app.security

            @property
            def user_is_admin(self):
                return False

        trans = MinimalTrans(self._app)
        return AgentOperationsManager(app=self._app, trans=trans)

    def test_encode_ids_helper_encodes_nested_ids(self):
        ops = self._make_ops()

        test_data = {
            "id": 123,
            "name": "test",
            "nested": {"id": 456, "history_id": 789},
            "list_items": [{"id": 111, "dataset_id": 222}, {"id": 333}],
        }

        result = ops._encode_ids_in_response(test_data)

        assert isinstance(result["id"], str)
        assert len(result["id"]) >= 16
        assert result["name"] == "test"
        assert isinstance(result["nested"]["id"], str)
        assert isinstance(result["nested"]["history_id"], str)
        assert isinstance(result["list_items"][0]["id"], str)
        assert isinstance(result["list_items"][0]["dataset_id"], str)
        assert isinstance(result["list_items"][1]["id"], str)

    def test_encode_ids_preserves_non_id_fields(self):
        ops = self._make_ops()

        test_data = {
            "id": 1,
            "name": "My History",
            "annotation": "Test annotation",
            "count": 42,
            "empty_list": [],
            "tags": ["tag1", "tag2"],
        }

        result = ops._encode_ids_in_response(test_data)

        assert isinstance(result["id"], str)
        assert result["name"] == "My History"
        assert result["annotation"] == "Test annotation"
        assert result["count"] == 42
        assert result["empty_list"] == []
        assert result["tags"] == ["tag1", "tag2"]

    def test_encode_ids_handles_already_encoded_ids(self):
        ops = self._make_ops()

        test_data = {
            "id": "abc123def456",
            "history_id": "already_encoded_id",
        }

        result = ops._encode_ids_in_response(test_data)

        assert result["id"] == "abc123def456"
        assert result["history_id"] == "already_encoded_id"


# ============================================================================
# MCP Server Smoke Tests
# ============================================================================


class TestMCPServerSmoke(IntegrationTestCase):
    """Smoke tests for the MCP server.

    Verifies the server initializes, advertises tools, handles auth,
    and can execute basic tool calls. Not exhaustive API testing --
    the MCP tools are thin wrappers around AgentOperationsManager.
    """

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        config["enable_mcp_server"] = True
        config["enable_beta_tool_formats"] = True

    def _get_mcp_server(self):
        http_app = get_mcp_app(self._app)
        return http_app.state.mcp_server

    def _get_api_key(self):
        _, api_key = self._setup_user_get_key("mcp_test_user@test.com")
        return api_key

    def _setup_udt_user(self, email: str):
        """Create a user, grant USER_TOOL_EXECUTE, return (user, api_key)."""
        user, api_key = self._setup_user_get_key(email)
        populator = DatasetPopulator(self.galaxy_interactor)
        populator.create_role([user["id"]], role_type="user_tool_execute")
        return user, api_key

    def _run_async(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_mcp_server_initializes(self):
        """MCP server creates a FastMCP instance when enabled."""
        mcp_server = self._get_mcp_server()
        assert isinstance(mcp_server, FastMCP)

    def test_mcp_tools_registered(self):
        """MCP server advertises all expected tools."""
        mcp_server = self._get_mcp_server()

        async def _list():
            async with Client(mcp_server) as client:
                return await client.list_tools()

        tools = self._run_async(_list())
        tool_names = {t.name for t in tools}

        expected = {
            "connect",
            "search_tools",
            "list_histories",
            "run_tool",
            "get_tool_details",
            "get_history_contents",
            "get_dataset_details",
            "upload_file_from_url",
            "invoke_workflow",
            "get_job_status",
            "list_user_tools",
            "create_user_tool",
            "delete_user_tool",
            "run_user_tool",
            "search_iwc_workflows",
            "get_iwc_workflow_details",
            "import_workflow_from_iwc",
        }
        assert expected.issubset(tool_names), f"Missing tools: {expected - tool_names}"

    def test_mcp_connect_with_valid_key(self):
        """connect() succeeds with a valid API key and returns user + server info."""
        mcp_server = self._get_mcp_server()
        api_key = self._get_api_key()

        async def _connect():
            async with Client(mcp_server) as client:
                return await client.call_tool("connect", {"api_key": api_key})

        result = self._run_async(_connect())
        assert not result.is_error
        data = result.data
        assert "user" in data
        assert "server" in data

    def test_mcp_connect_with_invalid_key(self):
        """connect() rejects an invalid API key."""
        mcp_server = self._get_mcp_server()

        async def _connect():
            async with Client(mcp_server) as client:
                return await client.call_tool("connect", {"api_key": "bogus-key-12345"})

        with pytest.raises(ToolError, match="(?i)(invalid|api key)"):
            self._run_async(_connect())

    def test_mcp_list_histories(self):
        """list_histories() returns a valid response."""
        mcp_server = self._get_mcp_server()
        api_key = self._get_api_key()

        async def _list():
            async with Client(mcp_server) as client:
                return await client.call_tool("list_histories", {"api_key": api_key})

        result = self._run_async(_list())
        assert not result.is_error
        data = result.data
        assert "histories" in data

    def test_mcp_search_tools(self):
        """search_tools() executes and returns a well-formed response."""
        mcp_server = self._get_mcp_server()
        api_key = self._get_api_key()

        async def _search():
            async with Client(mcp_server) as client:
                return await client.call_tool("search_tools", {"api_key": api_key, "query": "sort"})

        result = self._run_async(_search())
        assert not result.is_error
        data = result.data
        assert "tools" in data
        assert "query" in data
        assert "count" in data
        assert isinstance(data["tools"], list)

    def test_mcp_list_user_tools_empty(self):
        """list_user_tools() returns an empty list for a user with the role and no UDTs."""
        mcp_server = self._get_mcp_server()
        _, api_key = self._setup_udt_user("udt_list_user@test.com")

        async def _list():
            async with Client(mcp_server) as client:
                return await client.call_tool("list_user_tools", {"api_key": api_key})

        result = self._run_async(_list())
        assert not result.is_error, result
        data = result.data
        assert data["tools"] == []
        assert data["count"] == 0

    def test_mcp_create_user_tool(self):
        """create_user_tool() persists a UDT and returns its uuid."""
        mcp_server = self._get_mcp_server()
        _, api_key = self._setup_udt_user("udt_create_user@test.com")

        async def _create():
            async with Client(mcp_server) as client:
                return await client.call_tool(
                    "create_user_tool",
                    {"api_key": api_key, "representation": TOOL_WITH_SHELL_COMMAND},
                )

        result = self._run_async(_create())
        assert not result.is_error, result
        data = result.data
        assert "uuid" in data
        assert data["representation"]["name"] == TOOL_WITH_SHELL_COMMAND["name"]

    def test_mcp_delete_user_tool(self):
        """delete_user_tool() deactivates a UDT so list_user_tools no longer returns it."""
        mcp_server = self._get_mcp_server()
        _, api_key = self._setup_udt_user("udt_delete_user@test.com")
        populator = DatasetPopulator(self._get_interactor(api_key=api_key))
        history_id = populator.new_history()

        async def _flow():
            async with Client(mcp_server) as client:
                create = await client.call_tool(
                    "create_user_tool",
                    {"api_key": api_key, "representation": TOOL_WITH_SHELL_COMMAND},
                )
                uuid = create.data["uuid"]
                await client.call_tool("delete_user_tool", {"api_key": api_key, "uuid": uuid})
                listed = await client.call_tool("list_user_tools", {"api_key": api_key})
                deleted_run = await client.call_tool(
                    "run_user_tool",
                    {
                        "api_key": api_key,
                        "history_id": history_id,
                        "tool_uuid": uuid,
                        "inputs": {},
                    },
                    raise_on_error=False,
                )
                return uuid, listed, deleted_run

        uuid, listed, deleted_run = self._run_async(_flow())
        uuids_after = {t["uuid"] for t in listed.data["tools"]}
        assert uuid not in uuids_after
        assert deleted_run.is_error
        assert "deactivated" in deleted_run.content[0].text

    def test_mcp_run_user_tool(self):
        """run_user_tool() executes a UDT against an HDA input and produces an output."""
        mcp_server = self._get_mcp_server()
        _, api_key = self._setup_udt_user("udt_run_user@test.com")

        populator = DatasetPopulator(self._get_interactor(api_key=api_key))
        history_id = populator.new_history()
        dataset = populator.new_dataset(history_id=history_id, content="abc")

        async def _flow():
            async with Client(mcp_server) as client:
                create = await client.call_tool(
                    "create_user_tool",
                    {"api_key": api_key, "representation": TOOL_WITH_SHELL_COMMAND},
                )
                uuid = create.data["uuid"]
                return await client.call_tool(
                    "run_user_tool",
                    {
                        "api_key": api_key,
                        "history_id": history_id,
                        "tool_uuid": uuid,
                        "inputs": {"input": {"src": "hda", "id": dataset["id"]}},
                    },
                )

        result = self._run_async(_flow())
        assert not result.is_error, result
        data = result.data
        assert data["jobs"][0]["tool_id"] == TOOL_WITH_SHELL_COMMAND["id"]
        assert data["jobs"][0]["history_id"] == history_id
        assert data["outputs"][0]["output_name"] == "output"
        populator.wait_for_history(history_id, assert_ok=True)
        output = populator.get_history_dataset_content(history_id)
        assert output == "abc\n"

    def test_mcp_import_workflow_from_iwc(self):
        """import_workflow_from_iwc() imports a StoredWorkflow via the shared TRS pipeline."""
        import json
        from unittest.mock import patch

        from fastmcp import Client

        mcp_server = self._get_mcp_server()
        api_key = self._get_api_key()

        # Minimal valid Galaxy workflow definition, served as a Dockstore TRS descriptor.
        definition = {
            "a_galaxy_workflow": "true",
            "format-version": "0.1",
            "name": "IWC smoke test workflow",
            "steps": {
                "0": {
                    "id": 0,
                    "type": "data_input",
                    "label": "input",
                    "inputs": [],
                    "outputs": [],
                    "tool_state": "{}",
                    "input_connections": {},
                    "annotation": "",
                    "position": {"left": 0, "top": 0},
                }
            },
            "tags": [],
            "annotation": "",
        }
        trs_id = "#workflow/github.com/iwc-workflows/smoke/main"

        async def _import():
            async with Client(mcp_server) as client:
                return await client.call_tool(
                    "import_workflow_from_iwc",
                    {"api_key": api_key, "trs_id": trs_id},
                )

        # The TRS proxy fetches the workflow descriptor over HTTP; mock that so we
        # don't actually hit Dockstore from CI.
        with patch("galaxy.workflow.trs_proxy.requests.get") as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.return_value = {"content": json.dumps(definition)}
            result = self._run_async(_import())

        assert not result.is_error, result
        data = result.data
        assert "id" in data
        assert data["trsID"] == trs_id
