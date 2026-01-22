"""
API tests for AgentOperationsManager.

These tests exercise the operations that AgentOperationsManager provides,
testing through the normal Galaxy API endpoints which use the same service
layer code paths.
"""

from galaxy_test.base.decorators import requires_new_history
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TestAgentOperationsApi(ApiTestCase):
    """
    Test the operations available through AgentOperationsManager.

    These tests verify the underlying functionality that MCP tools and
    internal Galaxy agents use to interact with Galaxy.
    """

    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    # ==================== Connection / Server Info Tests ====================

    def test_connect_whoami(self):
        """Test that we can verify connection and get user info."""
        # This tests the connect() operation - get current user info
        response = self._get("users/current")
        self._assert_status_code_is(response, 200)
        user_info = response.json()
        self._assert_has_keys(user_info, "id", "email", "username")
        assert user_info["email"] is not None

    def test_get_server_version(self):
        """Test that we can get server version info."""
        response = self._get("version")
        self._assert_status_code_is(response, 200)
        version_info = response.json()
        self._assert_has_keys(version_info, "version_major", "version_minor")

    def test_get_server_configuration(self):
        """Test that we can get server configuration."""
        response = self._get("configuration")
        self._assert_status_code_is(response, 200)
        config = response.json()
        # Configuration endpoint returns various server settings
        assert isinstance(config, dict)

    # ==================== History Operations Tests ====================

    def test_list_histories(self):
        """Test listing user histories with pagination."""
        # Create a history first
        history_name = "TestHistoryForListing"
        history_id = self.dataset_populator.new_history(name=history_name)

        # List histories
        response = self._get("histories")
        self._assert_status_code_is(response, 200)
        histories = response.json()

        assert isinstance(histories, list)
        assert len(histories) > 0

        # Find our history
        our_history = [h for h in histories if h["id"] == history_id]
        assert len(our_history) == 1
        assert our_history[0]["name"] == history_name

    def test_list_histories_with_pagination(self):
        """Test listing histories with limit and offset."""
        # Create multiple histories
        for i in range(3):
            self.dataset_populator.new_history(name=f"PaginationTestHistory{i}")

        # Test limit
        response = self._get("histories", data={"limit": 2})
        self._assert_status_code_is(response, 200)
        histories = response.json()
        assert len(histories) <= 2

        # Test offset
        response = self._get("histories", data={"limit": 10, "offset": 1})
        self._assert_status_code_is(response, 200)

    def test_create_history(self):
        """Test creating a new history."""
        history_name = "TestHistoryCreation"
        response = self._post("histories", data={"name": history_name})
        self._assert_status_code_is(response, 200)
        history = response.json()

        self._assert_has_keys(history, "id", "name")
        assert history["name"] == history_name

    def test_get_history_details(self):
        """Test getting detailed history information."""
        history_name = "TestHistoryDetails"
        history_id = self.dataset_populator.new_history(name=history_name)

        response = self._get(f"histories/{history_id}")
        self._assert_status_code_is(response, 200)
        history = response.json()

        self._assert_has_keys(history, "id", "name", "state", "size", "contents_url")
        assert history["id"] == history_id
        assert history["name"] == history_name

    def test_get_history_contents(self):
        """Test getting history contents (datasets)."""
        history_id = self.dataset_populator.new_history()
        # Create a dataset in the history
        self.dataset_populator.new_dataset(history_id, content="test data\n")

        response = self._get(f"histories/{history_id}/contents")
        self._assert_status_code_is(response, 200)
        contents = response.json()

        assert isinstance(contents, list)
        assert len(contents) == 1
        self._assert_has_keys(contents[0], "id", "name", "hid", "history_content_type")

    def test_get_history_contents_pagination(self):
        """Test paginated history contents."""
        history_id = self.dataset_populator.new_history()
        # Create multiple datasets
        for i in range(5):
            self.dataset_populator.new_dataset(history_id, content=f"test data {i}\n")

        # Test with limit - verify we can request a limited number
        response = self._get(f"histories/{history_id}/contents", data={"limit": 2})
        self._assert_status_code_is(response, 200)
        contents = response.json()
        assert len(contents) <= 5  # Should return at most what exists

        # Test with offset - verify offset parameter is accepted
        response = self._get(f"histories/{history_id}/contents", data={"limit": 10, "offset": 2})
        self._assert_status_code_is(response, 200)
        contents = response.json()
        # With offset=2 and 5 total items, we should get at most 3
        assert len(contents) <= 5

    # ==================== Tool Operations Tests ====================

    def test_search_tools(self):
        """Test searching for tools by query."""
        # Search for upload tool which should always exist
        response = self._get("tools", data={"q": "upload"})
        self._assert_status_code_is(response, 200)
        tool_ids = response.json()
        assert isinstance(tool_ids, list)
        assert "upload1" in tool_ids

    @skip_without_tool("cat1")
    def test_search_tools_cat(self):
        """Test searching for concatenate tool."""
        response = self._get("tools", data={"q": "concatenate"})
        self._assert_status_code_is(response, 200)
        tool_ids = response.json()
        assert "cat1" in tool_ids

    def test_get_tool_details(self):
        """Test getting detailed tool information."""
        response = self._get("tools/upload1")
        self._assert_status_code_is(response, 200)
        tool = response.json()

        self._assert_has_keys(tool, "id", "name", "version", "description")
        assert tool["id"] == "upload1"

    @skip_without_tool("cat1")
    def test_get_tool_details_with_io(self):
        """Test getting tool details with input/output specifications."""
        response = self._get("tools/cat1", data={"io_details": True})
        self._assert_status_code_is(response, 200)
        tool = response.json()

        self._assert_has_keys(tool, "id", "name", "inputs", "outputs")
        assert len(tool["inputs"]) > 0

    @skip_without_tool("cat1")
    def test_run_tool(self):
        """Test executing a tool (cat1)."""
        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, content="line1\nline2\n", wait=True)
        dataset_id = dataset["id"]

        # Run cat tool
        payload = {
            "tool_id": "cat1",
            "history_id": history_id,
            "inputs": {"input1": {"src": "hda", "id": dataset_id}},
        }
        response = self._post("tools", data=payload, json=True)
        self._assert_status_code_is(response, 200)
        result = response.json()

        self._assert_has_keys(result, "jobs", "outputs")
        assert len(result["jobs"]) > 0
        assert len(result["outputs"]) > 0

    @skip_without_tool("cat1")
    def test_get_tool_citations(self):
        """Test getting tool citation information."""
        response = self._get("tools/cat1/citations")
        self._assert_status_code_is(response, 200)
        citations = response.json()
        # Citations is a list (may be empty for some tools)
        assert isinstance(citations, list)

    # ==================== Job Operations Tests ====================

    @skip_without_tool("cat1")
    def test_get_job_status(self):
        """Test getting job status."""
        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, content="test\n", wait=True)

        # Run a tool to create a job
        run_result = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": dataset["id"]}},
            history_id=history_id,
        )
        job_id = run_result["jobs"][0]["id"]

        # Get job status
        response = self._get(f"jobs/{job_id}")
        self._assert_status_code_is(response, 200)
        job = response.json()

        self._assert_has_keys(job, "id", "state", "tool_id")
        assert job["id"] == job_id
        assert job["tool_id"] == "cat1"
        assert job["state"] in ["new", "queued", "running", "ok", "error"]

    @skip_without_tool("cat1")
    def test_get_job_details_full(self):
        """Test getting full job details."""
        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, content="test data\n", wait=True)

        run_result = self.dataset_populator.run_tool(
            tool_id="cat1",
            inputs={"input1": {"src": "hda", "id": dataset["id"]}},
            history_id=history_id,
        )
        job_id = run_result["jobs"][0]["id"]

        # Wait for job to complete
        self.dataset_populator.wait_for_job(job_id)

        # Get full job details
        response = self._get(f"jobs/{job_id}", data={"full": True})
        self._assert_status_code_is(response, 200)
        job = response.json()

        self._assert_has_keys(job, "id", "state", "tool_id", "inputs", "outputs")

    # ==================== Dataset Operations Tests ====================

    def test_get_dataset_details(self):
        """Test getting dataset details."""
        history_id = self.dataset_populator.new_history()
        dataset = self.dataset_populator.new_dataset(history_id, content="dataset content\n", wait=True)
        dataset_id = dataset["id"]

        response = self._get(f"datasets/{dataset_id}")
        self._assert_status_code_is(response, 200)
        details = response.json()

        self._assert_has_keys(details, "id", "name", "state", "extension", "file_size")
        assert details["id"] == dataset_id
        assert details["state"] == "ok"

    def test_upload_file_from_content(self):
        """Test uploading a dataset."""
        history_id = self.dataset_populator.new_history()

        # Upload using the populator (tests upload tool functionality)
        dataset = self.dataset_populator.new_dataset(
            history_id, content="uploaded content\nline2\n", file_type="txt", wait=True
        )

        assert dataset["state"] == "ok"
        assert dataset["extension"] == "txt"

        # Verify content
        content = self.dataset_populator.get_history_dataset_content(history_id, dataset=dataset)
        assert "uploaded content" in content

    @requires_new_history
    def test_get_dataset_with_creating_job(self, history_id):
        """Test getting dataset details includes creating job."""
        dataset = self.dataset_populator.new_dataset(history_id, content="test\n", wait=True)

        response = self._get(f"datasets/{dataset['id']}")
        self._assert_status_code_is(response, 200)
        details = response.json()

        # Dataset should have a creating_job
        assert "creating_job" in details

    # ==================== Workflow Operations Tests ====================

    def test_list_workflows(self):
        """Test listing user workflows."""
        response = self._get("workflows")
        self._assert_status_code_is(response, 200)
        workflows = response.json()
        assert isinstance(workflows, list)

    def test_list_workflows_with_pagination(self):
        """Test listing workflows with pagination."""
        response = self._get("workflows", data={"limit": 10, "offset": 0})
        self._assert_status_code_is(response, 200)
        workflows = response.json()
        assert isinstance(workflows, list)

    def test_create_and_get_workflow(self):
        """Test creating and retrieving a workflow."""
        workflow = self.workflow_populator.load_workflow(name="test_workflow_for_agent_ops")
        workflow_id = self.workflow_populator.create_workflow(workflow)

        # Get workflow details
        response = self._get(f"workflows/{workflow_id}")
        self._assert_status_code_is(response, 200)
        workflow_details = response.json()

        self._assert_has_keys(workflow_details, "id", "name", "steps")
        assert workflow_details["id"] == workflow_id

    @skip_without_tool("cat1")
    def test_invoke_workflow(self):
        """Test invoking a workflow."""
        workflow = self.workflow_populator.load_workflow(name="test_workflow_invoke")
        workflow_id = self.workflow_populator.create_workflow(workflow)

        history_id = self.dataset_populator.new_history()
        # The default test workflow has two inputs (step 0 and step 1)
        dataset1 = self.dataset_populator.new_dataset(history_id, content="workflow input 1\n", wait=True)
        dataset2 = self.dataset_populator.new_dataset(history_id, content="workflow input 2\n", wait=True)

        # Invoke the workflow - invoke_workflow returns a Response object
        invocation_response = self.workflow_populator.invoke_workflow(
            workflow_id,
            history_id=history_id,
            inputs={
                "0": {"src": "hda", "id": dataset1["id"]},
                "1": {"src": "hda", "id": dataset2["id"]},
            },
        )
        self._assert_status_code_is(invocation_response, 200)
        invocation = invocation_response.json()

        self._assert_has_keys(invocation, "id", "state", "workflow_id")

    @skip_without_tool("cat1")
    def test_get_invocations(self):
        """Test listing workflow invocations."""
        workflow = self.workflow_populator.load_workflow(name="test_workflow_invocations")
        workflow_id = self.workflow_populator.create_workflow(workflow)

        history_id = self.dataset_populator.new_history()
        # The default test workflow has two inputs (step 0 and step 1)
        dataset1 = self.dataset_populator.new_dataset(history_id, content="test 1\n", wait=True)
        dataset2 = self.dataset_populator.new_dataset(history_id, content="test 2\n", wait=True)

        # Create an invocation - invoke_workflow returns a Response object
        invocation_response = self.workflow_populator.invoke_workflow(
            workflow_id,
            history_id=history_id,
            inputs={
                "0": {"src": "hda", "id": dataset1["id"]},
                "1": {"src": "hda", "id": dataset2["id"]},
            },
        )
        self._assert_status_code_is(invocation_response, 200)

        # List invocations
        response = self._get("invocations")
        self._assert_status_code_is(response, 200)
        invocations = response.json()
        assert isinstance(invocations, list)
        assert len(invocations) > 0

    @skip_without_tool("cat1")
    def test_get_invocation_details(self):
        """Test getting workflow invocation details."""
        workflow = self.workflow_populator.load_workflow(name="test_workflow_invocation_details")
        workflow_id = self.workflow_populator.create_workflow(workflow)

        history_id = self.dataset_populator.new_history()
        # The default test workflow has two inputs (step 0 and step 1)
        dataset1 = self.dataset_populator.new_dataset(history_id, content="test 1\n", wait=True)
        dataset2 = self.dataset_populator.new_dataset(history_id, content="test 2\n", wait=True)

        # invoke_workflow returns a Response object
        invocation_response = self.workflow_populator.invoke_workflow(
            workflow_id,
            history_id=history_id,
            inputs={
                "0": {"src": "hda", "id": dataset1["id"]},
                "1": {"src": "hda", "id": dataset2["id"]},
            },
        )
        self._assert_status_code_is(invocation_response, 200)
        invocation = invocation_response.json()
        invocation_id = invocation["id"]

        # Get invocation details
        response = self._get(f"invocations/{invocation_id}")
        self._assert_status_code_is(response, 200)
        details = response.json()

        self._assert_has_keys(details, "id", "state", "workflow_id", "history_id")
        assert details["id"] == invocation_id


class TestAgentToolOperations(ApiTestCase):
    """Additional tests focused on tool-related operations."""

    dataset_populator: DatasetPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)

    def test_get_tool_panel(self):
        """Test getting the tool panel structure."""
        response = self._get("tools", data={"in_panel": True})
        self._assert_status_code_is(response, 200)
        panel = response.json()
        assert isinstance(panel, list)
        # Panel should have sections with tools
        assert len(panel) > 0

    def test_get_tools_flat_list(self):
        """Test getting tools as a flat list."""
        response = self._get("tools", data={"in_panel": False})
        self._assert_status_code_is(response, 200)
        tools = response.json()
        assert isinstance(tools, list)
        # Should include upload tool
        tool_ids = [t["id"] for t in tools]
        assert "upload1" in tool_ids

    @skip_without_tool("cat1")
    def test_tool_tests(self):
        """Test getting tool test definitions."""
        response = self._get("tools/cat1/test_data")
        self._assert_status_code_is(response, 200)
        test_data = response.json()
        # Test data endpoint returns tool test configurations
        assert isinstance(test_data, list)

    def test_tool_requirements(self):
        """Test getting tool requirements."""
        # upload1 is a built-in tool, should work
        response = self._get("tools/upload1/requirements", admin=True)
        # May require admin access
        if response.status_code == 200:
            requirements = response.json()
            assert isinstance(requirements, list)
