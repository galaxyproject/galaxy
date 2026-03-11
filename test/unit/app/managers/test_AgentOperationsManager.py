from unittest import mock

import pytest

from galaxy.webapps.galaxy.services.agent_operations import AgentOperationsManager
from .base import BaseTestCase


class TestAgentOperationsManagerBasic(BaseTestCase):
    """Tests for basic AgentOperationsManager operations that don't require services."""

    def set_up_managers(self):
        super().set_up_managers()
        self.agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

    def test_connect(self):
        result = self.agent_ops.connect()

        assert result["connected"] is True
        assert "server" in result
        assert "user" in result
        assert result["user"]["email"] == self.admin_user.email
        assert result["user"]["username"] == self.admin_user.username

    def test_connect_requires_user(self):
        self.trans.set_user(None)
        agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

        with pytest.raises(ValueError, match="User must be authenticated"):
            agent_ops.connect()

    def test_get_user(self):
        result = self.agent_ops.get_user()

        assert result["email"] == self.admin_user.email
        assert result["username"] == self.admin_user.username
        assert result["is_admin"] is True
        assert result["active"] is True
        assert result["deleted"] is False

    def test_get_server_info(self):
        result = self.agent_ops.get_server_info()

        assert "server" in result
        assert "capabilities" in result
        assert "version" in result["server"]


class TestAgentOperationsManagerWithMockedServices(BaseTestCase):
    """Tests that mock the service layer."""

    def set_up_managers(self):
        super().set_up_managers()
        self.agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

    def test_create_history(self):
        mock_history = mock.MagicMock()
        mock_history.name = "Test History"
        mock_history.id = "abc123"

        mock_service = mock.MagicMock()
        mock_service.create.return_value = mock_history

        with mock.patch.object(
            type(self.agent_ops), "histories_service", new_callable=lambda: property(lambda self: mock_service)
        ):
            result = self.agent_ops.create_history("Test History")

        mock_service.create.assert_called_once()
        assert result.name == "Test History"

    def test_list_histories(self):
        mock_histories = [
            mock.MagicMock(id="hist1", name="History 1"),
            mock.MagicMock(id="hist2", name="History 2"),
        ]

        mock_service = mock.MagicMock()
        mock_service.index.return_value = mock_histories

        with mock.patch.object(
            type(self.agent_ops), "histories_service", new_callable=lambda: property(lambda self: mock_service)
        ):
            result = self.agent_ops.list_histories(limit=10, offset=0)

        assert "histories" in result
        assert result["count"] == 2
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0

    def test_list_histories_with_name_filter(self):
        mock_histories = [mock.MagicMock(id="hist1", name="RNA Analysis")]

        mock_service = mock.MagicMock()
        mock_service.index.return_value = mock_histories

        with mock.patch.object(
            type(self.agent_ops), "histories_service", new_callable=lambda: property(lambda self: mock_service)
        ):
            result = self.agent_ops.list_histories(name="RNA")

        assert result["count"] == 1
        call_kwargs = mock_service.index.call_args
        filter_params = call_kwargs.kwargs.get("filter_query_params") or call_kwargs[1].get("filter_query_params")
        assert filter_params.q == ["name-contains"]
        assert filter_params.qv == ["RNA"]

    def test_get_collection_details(self):
        mock_collection = {
            "id": "col123",
            "name": "Paired reads",
            "collection_type": "list:paired",
            "elements": [{"id": "elem1"}, {"id": "elem2"}],
        }

        mock_service = mock.MagicMock()
        mock_service.show.return_value = mock_collection

        with (
            mock.patch.object(
                type(self.agent_ops),
                "dataset_collections_service",
                new_callable=lambda: property(lambda self: mock_service),
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=123),
        ):
            result = self.agent_ops.get_collection_details("encoded_col_id")

        assert "collection" in result
        assert result["collection_id"] == "encoded_col_id"
        assert result["collection"]["name"] == "Paired reads"
        assert len(result["collection"]["elements"]) == 2

    def test_get_collection_details_truncates_elements(self):
        elements = [{"id": f"elem{i}"} for i in range(10)]
        mock_collection = {
            "id": "col123",
            "name": "Big collection",
            "collection_type": "list",
            "elements": elements,
        }

        mock_service = mock.MagicMock()
        mock_service.show.return_value = mock_collection

        with (
            mock.patch.object(
                type(self.agent_ops),
                "dataset_collections_service",
                new_callable=lambda: property(lambda self: mock_service),
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=123),
        ):
            result = self.agent_ops.get_collection_details("encoded_col_id", max_elements=3)

        assert len(result["collection"]["elements"]) == 3
        assert result["collection"]["elements_truncated"] is True
        assert result["collection"]["total_elements"] == 10

    def test_get_workflow_details_with_version(self):
        mock_workflow = mock.MagicMock()

        mock_service = mock.MagicMock()
        mock_service.show_workflow.return_value = mock_workflow

        with (
            mock.patch.object(
                type(self.agent_ops), "workflows_service", new_callable=lambda: property(lambda self: mock_service)
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=42),
        ):
            self.agent_ops.get_workflow_details("encoded_wf_id", version=3)

        mock_service.show_workflow.assert_called_once_with(
            trans=self.trans, workflow_id=42, instance=False, legacy=False, version=3
        )

    def test_invoke_workflow_with_history_name(self):
        mock_workflows_service = mock.MagicMock()
        mock_workflows_service.invoke_workflow.return_value = {"id": "inv123"}

        with (
            mock.patch.object(
                type(self.agent_ops),
                "workflows_service",
                new_callable=lambda: property(lambda self: mock_workflows_service),
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=42),
        ):
            self.agent_ops.invoke_workflow("encoded_wf_id", history_name="My Analysis")

        call_kwargs = mock_workflows_service.invoke_workflow.call_args
        payload = call_kwargs.kwargs.get("payload") or call_kwargs[1].get("payload")
        assert payload.new_history_name == "My Analysis"
        assert payload.history_id is None

    def test_invoke_workflow_requires_history(self):
        with pytest.raises(ValueError, match="Either history_id or history_name"):
            self.agent_ops.invoke_workflow("encoded_wf_id")

    def test_get_history_contents_with_filters(self):
        mock_service = mock.MagicMock()
        mock_service.index.return_value = ([], 0)

        with (
            mock.patch.object(
                type(self.agent_ops), "datasets_service", new_callable=lambda: property(lambda self: mock_service)
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=1),
        ):
            self.agent_ops.get_history_contents("hist_id", deleted=True, visible=False)

        call_kwargs = mock_service.index.call_args
        filter_params = call_kwargs.kwargs.get("filter_query_params") or call_kwargs[1].get("filter_query_params")
        assert "deleted-eq" in filter_params.q
        assert "visible-eq" in filter_params.q
        assert "True" in filter_params.qv
        assert "False" in filter_params.qv

    def test_get_tool_run_examples_with_version(self):
        mock_tool_v1 = mock.MagicMock()
        mock_tool_v1.id = "cat1"
        mock_tool_v1.name = "Concatenate"
        mock_tool_v1.version = "1.0"
        mock_tool_v1.tests = []

        mock_tool_v2 = mock.MagicMock()
        mock_tool_v2.id = "cat1"
        mock_tool_v2.name = "Concatenate"
        mock_tool_v2.version = "2.0"
        mock_tool_v2.tests = []

        self.app.toolbox = mock.MagicMock()
        self.app.toolbox.get_tool.side_effect = lambda tid, tool_version=None: (
            mock_tool_v2 if tool_version == "2.0" else mock_tool_v1
        )

        result = self.agent_ops.get_tool_run_examples("cat1", tool_version="2.0")
        assert result["tool_version"] == "2.0"

    def test_search_tools(self):
        mock_tool = mock.MagicMock()
        mock_tool.id = "upload1"
        mock_tool.name = "Upload File"
        mock_tool.description = "Upload files to Galaxy"
        mock_tool.version = "1.0"

        self.app.toolbox_search = mock.MagicMock()
        self.app.toolbox_search.search.return_value = ["upload1"]
        self.app.toolbox = mock.MagicMock()
        self.app.toolbox.get_tool.return_value = mock_tool

        result = self.agent_ops.search_tools("upload")

        assert result["query"] == "upload"
        assert "tools" in result
        assert result["count"] == 1
        assert result["tools"][0]["id"] == "upload1"

    def test_get_tool_details(self):
        mock_tool = mock.MagicMock()
        mock_tool.id = "cat1"
        mock_tool.name = "Concatenate datasets"
        mock_tool.version = "1.0"
        mock_tool.description = "Concatenate files"
        mock_tool.help = "Help text"

        self.app.toolbox = mock.MagicMock()
        self.app.toolbox.get_tool.return_value = mock_tool

        result = self.agent_ops.get_tool_details("cat1")

        assert result["id"] == "cat1"
        assert result["name"] == "Concatenate datasets"
        assert result["version"] == "1.0"

    def test_get_tool_details_not_found(self):
        self.app.toolbox = mock.MagicMock()
        self.app.toolbox.get_tool.return_value = None

        with pytest.raises(ValueError, match="not found"):
            self.agent_ops.get_tool_details("nonexistent_tool")

    def test_run_tool(self):
        mock_result = {"jobs": [{"id": "job123"}], "outputs": [{"id": "dataset123"}]}

        mock_service = mock.MagicMock()
        mock_service._create.return_value = mock_result

        with mock.patch.object(
            type(self.agent_ops), "tools_service", new_callable=lambda: property(lambda self: mock_service)
        ):
            result = self.agent_ops.run_tool("hist123", "cat1", {"input1": "data1"})

        assert "jobs" in result
        mock_service._create.assert_called_once()

    def test_get_job_status(self):
        mock_job = mock.MagicMock()
        mock_job.id = 123
        mock_job.state = "ok"

        mock_service = mock.MagicMock()
        mock_service.show.return_value = mock_job

        with (
            mock.patch.object(
                type(self.agent_ops), "jobs_service", new_callable=lambda: property(lambda self: mock_service)
            ),
            mock.patch.object(self.trans.security, "decode_id", return_value=123),
        ):
            result = self.agent_ops.get_job_status("encoded_job_id")

        assert "job" in result
        assert result["job_id"] == "encoded_job_id"
