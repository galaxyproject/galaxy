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
        self.agent_ops._histories_service = mock_service

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
        self.agent_ops._histories_service = mock_service

        result = self.agent_ops.list_histories(limit=10, offset=0)

        assert "histories" in result
        assert result["count"] == 2
        assert result["pagination"]["limit"] == 10
        assert result["pagination"]["offset"] == 0

    def test_list_histories_with_name_filter(self):
        mock_histories = [mock.MagicMock(id="hist1", name="RNA Analysis")]

        mock_service = mock.MagicMock()
        mock_service.index.return_value = mock_histories
        self.agent_ops._histories_service = mock_service

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
        self.agent_ops._dataset_collections_service = mock_service
        self.trans.security.decode_id = mock.MagicMock(return_value=123)

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
        self.agent_ops._dataset_collections_service = mock_service
        self.trans.security.decode_id = mock.MagicMock(return_value=123)

        result = self.agent_ops.get_collection_details("encoded_col_id", max_elements=3)

        assert len(result["collection"]["elements"]) == 3
        assert result["collection"]["elements_truncated"] is True
        assert result["collection"]["total_elements"] == 10

    def test_get_workflow_details_with_version(self):
        mock_workflow = mock.MagicMock()

        mock_service = mock.MagicMock()
        mock_service.show_workflow.return_value = mock_workflow
        self.agent_ops._workflows_service = mock_service
        self.trans.security.decode_id = mock.MagicMock(return_value=42)

        self.agent_ops.get_workflow_details("encoded_wf_id", version=3)

        mock_service.show_workflow.assert_called_once_with(
            trans=self.trans, workflow_id=42, instance=False, legacy=False, version=3
        )

    def test_invoke_workflow_with_history_name(self):
        mock_workflows_service = mock.MagicMock()
        mock_workflows_service.invoke_workflow.return_value = {"id": "inv123"}
        self.agent_ops._workflows_service = mock_workflows_service
        self.trans.security.decode_id = mock.MagicMock(return_value=42)

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
        self.agent_ops._datasets_service = mock_service
        self.trans.security.decode_id = mock.MagicMock(return_value=1)

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
        self.agent_ops._tools_service = mock_service

        result = self.agent_ops.run_tool("hist123", "cat1", {"input1": "data1"})

        assert "jobs" in result
        mock_service._create.assert_called_once()

    def test_get_job_status(self):
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

    def _make_manifest(self, workflows=None):
        """Helper to build a manifest with enriched fields matching real IWC data."""
        if workflows is None:
            workflows = [
                {
                    "trsID": "#workflow/test/example",
                    "readme": "# Test\nA test workflow for testing purposes.",
                    "authors": [{"name": "Test Author"}],
                    "categories": ["Testing"],
                    "definition": {
                        "name": "Test Workflow",
                        "annotation": "A test workflow",
                        "tags": ["test", "example"],
                        "steps": {
                            "0": {"type": "data_input", "label": "Input data", "tool_id": None},
                            "1": {"type": "tool", "tool_id": "cat1", "name": "Concatenate"},
                        },
                    },
                }
            ]
        return [{"workflows": workflows}]

    def test_get_iwc_workflows(self):
        mock_manifest = self._make_manifest()

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.get_iwc_workflows()

            assert "workflows" in result
            assert "count" in result
            assert result["count"] == 1
            wf = result["workflows"][0]
            assert wf["trsID"] == "#workflow/test/example"
            assert wf["name"] == "Test Workflow"
            assert wf["readme_summary"] != ""
            assert wf["step_count"] == 2
            assert wf["authors"] == ["Test Author"]
            assert wf["categories"] == ["Testing"]
            assert "Concatenate" in wf["tools_used"]

    def test_get_iwc_workflows_enrichment_with_creator_fallback(self):
        """Authors fall back to definition.creator when workflow-level authors missing."""
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/test/fallback",
                        "definition": {
                            "name": "Fallback Test",
                            "annotation": "Test",
                            "tags": [],
                            "steps": {},
                            "creator": [{"class": "Person", "name": "Creator Name"}],
                        },
                    }
                ]
            }
        ]

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.get_iwc_workflows()
            assert result["workflows"][0]["authors"] == ["Creator Name"]

    def test_search_iwc_workflows(self):
        mock_manifest = self._make_manifest(
            [
                {
                    "trsID": "#workflow/rna-seq/main",
                    "readme": "RNA-seq pipeline readme",
                    "authors": [{"name": "Bio Author"}],
                    "categories": [],
                    "definition": {
                        "name": "RNA-seq Analysis",
                        "annotation": "Complete RNA-seq pipeline",
                        "tags": ["rna-seq", "transcriptomics"],
                        "steps": {"0": {"type": "data_input", "tool_id": None}},
                    },
                },
                {
                    "trsID": "#workflow/other/main",
                    "readme": "",
                    "authors": [],
                    "categories": [],
                    "definition": {
                        "name": "Other Workflow",
                        "annotation": "Something else",
                        "tags": ["other"],
                        "steps": {},
                    },
                },
            ]
        )

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.search_iwc_workflows("rna")

            assert "workflows" in result
            assert result["query"] == "rna"
            assert result["count"] == 1
            wf = result["workflows"][0]
            assert wf["name"] == "RNA-seq Analysis"
            assert "step_count" in wf
            assert "authors" in wf

    def test_search_iwc_workflows_by_tag(self):
        mock_manifest = [
            {
                "workflows": [
                    {
                        "trsID": "#workflow/variant/main",
                        "readme": "",
                        "authors": [],
                        "categories": [],
                        "definition": {
                            "name": "Variant Calling",
                            "annotation": "SNP detection",
                            "tags": ["genomics", "variant-calling"],
                            "steps": {},
                        },
                    },
                ]
            }
        ]

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.search_iwc_workflows("genomics")

            assert result["count"] == 1
            assert result["workflows"][0]["name"] == "Variant Calling"

    def test_get_iwc_workflow_details(self):
        mock_manifest = self._make_manifest(
            [
                {
                    "trsID": "#workflow/rna/main",
                    "readme": "# RNA Pipeline\nThis workflow does RNA-seq analysis with star and featurecounts.",
                    "authors": [{"name": "Jane Doe"}],
                    "categories": ["Transcriptomics"],
                    "definition": {
                        "name": "RNA-seq Pipeline",
                        "annotation": "Full RNA-seq analysis",
                        "tags": ["rna-seq"],
                        "license": "MIT",
                        "release": "1.0",
                        "steps": {
                            "0": {
                                "type": "data_input",
                                "label": "Input FASTQ",
                                "tool_id": None,
                                "workflow_outputs": [],
                            },
                            "1": {
                                "type": "tool",
                                "tool_id": "toolshed.g2.bx.psu.edu/repos/iuc/star/rna_star",
                                "name": "RNA STAR",
                                "label": "STAR alignment",
                                "workflow_outputs": [{"label": "Aligned BAM"}],
                            },
                        },
                    },
                }
            ]
        )

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            result = self.agent_ops.get_iwc_workflow_details("#workflow/rna/main")

            assert result["trsID"] == "#workflow/rna/main"
            assert result["name"] == "RNA-seq Pipeline"
            assert result["license"] == "MIT"
            assert result["release"] == "1.0"
            assert result["authors"] == ["Jane Doe"]
            assert result["categories"] == ["Transcriptomics"]
            assert result["step_count"] == 2
            assert len(result["inputs"]) == 1
            assert result["inputs"][0]["label"] == "Input FASTQ"
            assert len(result["outputs"]) == 1
            assert result["outputs"][0]["label"] == "Aligned BAM"
            assert any("STAR" in t for t in result["tools_used"])
            assert "RNA Pipeline" in result["readme"]

    def test_get_iwc_workflow_details_not_found(self):
        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=[]):
            with pytest.raises(ValueError, match="not found in IWC manifest"):
                self.agent_ops.get_iwc_workflow_details("#workflow/nonexistent/main")

    def test_import_workflow_from_iwc_not_found(self):
        mock_manifest = []

        with mock.patch.object(self.agent_ops, "_get_iwc_manifest", return_value=mock_manifest):
            with pytest.raises(ValueError, match="not found in IWC manifest"):
                self.agent_ops.import_workflow_from_iwc("#workflow/nonexistent/main")

    def test_import_workflow_from_iwc(self):
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
            with mock.patch("galaxy.managers.agent_operations.WorkflowsManager") as mock_wf_manager:
                mock_wf_manager.return_value.import_workflow_dict.return_value = mock_imported
                self.trans.security.encode_id = mock.MagicMock(return_value="encoded123")

                result = self.agent_ops.import_workflow_from_iwc("#workflow/test/main")

                assert result["trs_id"] == "#workflow/test/main"
                assert "imported_workflow" in result
                assert result["imported_workflow"]["name"] == "Test Workflow"
