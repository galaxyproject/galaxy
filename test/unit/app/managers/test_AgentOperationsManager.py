"""Unit tests for AgentOperationsManager."""

from unittest import mock

import pytest

from galaxy.managers.agent_operations import AgentOperationsManager
from .base import BaseTestCase


class TestAgentOperationsManagerBasic(BaseTestCase):
    """Tests for basic AgentOperationsManager operations that don't require services."""

    def set_up_managers(self):
        super().set_up_managers()
        self.agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

    def test_connect(self):
        """Test the connect operation returns expected user and server info."""
        result = self.agent_ops.connect()

        assert result["connected"] is True
        assert "server" in result
        assert "user" in result
        assert result["user"]["email"] == self.admin_user.email
        assert result["user"]["username"] == self.admin_user.username

    def test_connect_requires_user(self):
        """Test connect fails without authenticated user."""
        self.trans.set_user(None)
        agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

        with pytest.raises(ValueError, match="User must be authenticated"):
            agent_ops.connect()

    def test_get_user(self):
        """Test get_user returns current user details."""
        result = self.agent_ops.get_user()

        assert result["email"] == self.admin_user.email
        assert result["username"] == self.admin_user.username
        assert result["is_admin"] is True
        assert result["active"] is True
        assert result["deleted"] is False

    def test_get_server_info(self):
        """Test get_server_info returns server configuration."""
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
        """Test creating a new history with mocked service."""
        mock_history = mock.MagicMock()
        mock_history.name = "Test History"
        mock_history.id = "abc123"

        mock_service = mock.MagicMock()
        mock_service.create.return_value = mock_history
        self.agent_ops._histories_service = mock_service

        result = self.agent_ops.create_history("Test History")

        mock_service.create.assert_called_once()
        assert result.name == "Test History"

    def test_list_histories(self):
        """Test listing user histories with mocked service."""
        mock_histories = [
            mock.MagicMock(id="hist1", name="History 1"),
            mock.MagicMock(id="hist2", name="History 2"),
        ]

        mock_service = mock.MagicMock()
        mock_service.index.return_value = mock_histories
        self.agent_ops._histories_service = mock_service

        result = self.agent_ops.list_histories(limit=10, offset=0)

        assert "histories" in result
        assert result["count"] == 2
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0

    def test_search_tools(self):
        """Test tool search with mocked service."""
        mock_tool = mock.MagicMock()
        mock_tool.id = "upload1"
        mock_tool.name = "Upload File"
        mock_tool.description = "Upload files to Galaxy"
        mock_tool.version = "1.0"

        mock_service = mock.MagicMock()
        mock_service._search.return_value = ["upload1"]
        mock_service._get_tool.return_value = mock_tool
        self.agent_ops._tools_service = mock_service

        result = self.agent_ops.search_tools("upload")

        assert result["query"] == "upload"
        assert "tools" in result
        assert result["count"] == 1
        assert result["tools"][0]["id"] == "upload1"

    def test_get_tool_details(self):
        """Test getting tool details with mocked service."""
        mock_tool = mock.MagicMock()
        mock_tool.id = "cat1"
        mock_tool.name = "Concatenate datasets"
        mock_tool.version = "1.0"
        mock_tool.description = "Concatenate files"
        mock_tool.help = "Help text"

        mock_service = mock.MagicMock()
        mock_service._get_tool.return_value = mock_tool
        self.agent_ops._tools_service = mock_service

        result = self.agent_ops.get_tool_details("cat1")

        assert result["id"] == "cat1"
        assert result["name"] == "Concatenate datasets"
        assert result["version"] == "1.0"

    def test_get_tool_details_not_found(self):
        """Test get_tool_details raises for non-existent tool."""
        mock_service = mock.MagicMock()
        mock_service._get_tool.return_value = None
        self.agent_ops._tools_service = mock_service

        with pytest.raises(ValueError, match="not found"):
            self.agent_ops.get_tool_details("nonexistent_tool")

    def test_run_tool(self):
        """Test running a tool with mocked service."""
        mock_result = {"jobs": [{"id": "job123"}], "outputs": [{"id": "dataset123"}]}

        mock_service = mock.MagicMock()
        mock_service._create.return_value = mock_result
        self.agent_ops._tools_service = mock_service

        result = self.agent_ops.run_tool("hist123", "cat1", {"input1": "data1"})

        assert "jobs" in result
        mock_service._create.assert_called_once()

    def test_get_job_status(self):
        """Test getting job status with mocked service."""
        mock_job = mock.MagicMock()
        mock_job.id = 123
        mock_job.state = "ok"

        mock_service = mock.MagicMock()
        mock_service.show.return_value = mock_job
        self.agent_ops._jobs_service = mock_service

        # Need to mock the decode_id as well
        self.trans.security.decode_id = mock.MagicMock(return_value=123)

        result = self.agent_ops.get_job_status("encoded_job_id")

        assert "job" in result
        assert result["job_id"] == "encoded_job_id"


class TestAgentOperationsManagerIWC(BaseTestCase):
    """Tests for IWC-related operations (require mocking HTTP)."""

    def set_up_managers(self):
        super().set_up_managers()
        self.agent_ops = AgentOperationsManager(app=self.app, trans=self.trans)

    def test_get_iwc_workflows(self):
        """Test fetching IWC workflow catalog."""
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/test/example",
                        "definition": {
                            "name": "Test Workflow",
                            "annotation": "A test workflow",
                            "tags": ["test", "example"],
                        },
                    }
                ]
            }
        ]

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.get_iwc_workflows()

            assert "workflows" in result
            assert "count" in result
            assert result["count"] == 1
            assert result["workflows"][0]["trsID"] == "#workflow/test/example"
            assert result["workflows"][0]["name"] == "Test Workflow"

    def test_search_iwc_workflows(self):
        """Test searching IWC workflows."""
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/rna-seq/main",
                        "definition": {
                            "name": "RNA-seq Analysis",
                            "annotation": "Complete RNA-seq pipeline",
                            "tags": ["rna-seq", "transcriptomics"],
                        },
                    },
                    {
                        "trsID": "#workflow/other/main",
                        "definition": {
                            "name": "Other Workflow",
                            "annotation": "Something else",
                            "tags": ["other"],
                        },
                    },
                ]
            }
        ]

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.search_iwc_workflows("rna")

            assert "workflows" in result
            assert result["query"] == "rna"
            # Should only find RNA-seq workflow
            assert result["count"] == 1
            assert result["workflows"][0]["name"] == "RNA-seq Analysis"

    def test_search_iwc_workflows_by_tag(self):
        """Test searching IWC workflows by tag."""
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/variant/main",
                        "definition": {
                            "name": "Variant Calling",
                            "annotation": "SNP detection",
                            "tags": ["genomics", "variant-calling"],
                        },
                    },
                ]
            }
        ]

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.search_iwc_workflows("genomics")

            assert result["count"] == 1
            assert result["workflows"][0]["name"] == "Variant Calling"

    def test_import_workflow_from_iwc_not_found(self):
        """Test importing non-existent IWC workflow raises error."""
        mock_manifest = []

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            with pytest.raises(ValueError, match="not found in IWC manifest"):
                self.agent_ops.import_workflow_from_iwc("#workflow/nonexistent/main")

    def test_import_workflow_from_iwc(self):
        """Test importing workflow from IWC."""
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/test/main",
                        "definition": {
                            "name": "Test Workflow",
                            "annotation": "Test",
                            "tags": [],
                            "steps": {},
                        },
                    }
                ]
            }
        ]

        mock_imported = mock.MagicMock()
        mock_imported.id = 123
        mock_imported.name = "Test Workflow"

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            with mock.patch("galaxy.managers.workflows.WorkflowsManager") as mock_wf_manager:
                mock_wf_manager.return_value.import_workflow_dict.return_value = mock_imported
                self.trans.security.encode_id = mock.MagicMock(return_value="encoded123")

                result = self.agent_ops.import_workflow_from_iwc("#workflow/test/main")

                assert result["trs_id"] == "#workflow/test/main"
                assert "imported_workflow" in result
                assert result["imported_workflow"]["name"] == "Test Workflow"
