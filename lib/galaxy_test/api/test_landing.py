from base64 import b64encode
from typing import (
    Any,
)

import yaml
from pydantic import HttpUrl

from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    CreateFileLandingPayload,
    DataLandingRequestState,
    FileOrCollectionRequestsAdapter,
)
from galaxy.schema.schema import (
    CreateToolLandingRequestPayload,
    CreateWorkflowLandingRequestPayload,
    WorkflowLandingRequest,
)
from galaxy_test.base.api_asserts import (
    assert_error_code_is,
    assert_status_code_is,
)
from galaxy_test.base.populators import (
    DatasetPopulator,
    skip_without_tool,
    WorkflowPopulator,
)
from ._framework import ApiTestCase


class TestLandingApi(ApiTestCase):
    dataset_populator: DatasetPopulator
    workflow_populator: WorkflowPopulator

    def setUp(self):
        super().setUp()
        self.dataset_populator = DatasetPopulator(self.galaxy_interactor)
        self.workflow_populator = WorkflowPopulator(self.galaxy_interactor)

    @skip_without_tool("cat")
    def test_tool_landing(self):
        request = CreateToolLandingRequestPayload(
            tool_id="create_2",
            tool_version=None,
            request_state={"sleep_time": 0},
            origin=HttpUrl("http://example.localhost/"),
        )
        response = self.dataset_populator.create_tool_landing(request)
        assert response.tool_id == "create_2"
        assert response.state == "unclaimed"
        assert str(response.origin) == "http://example.localhost/"
        response = self.dataset_populator.claim_tool_landing(response.uuid)
        assert response.tool_id == "create_2"
        assert response.state == "claimed"
        assert str(response.origin) == "http://example.localhost/"

    @skip_without_tool("gx_int")
    def test_tool_landing_invalid(self):
        request = CreateToolLandingRequestPayload(
            tool_id="gx_int",
            tool_version=None,
            request_state={"parameter": "foobar"},
        )
        response = self.dataset_populator.create_landing_raw(request, "tool")
        assert_status_code_is(response, 400)
        assert_error_code_is(response, 400008)
        assert "Input should be a valid integer" in response.text

    def test_data_landing(self):
        data_landing_request_state = DataLandingRequestState(
            targets=[
                {
                    "destination": {"type": "hdas"},
                    "items": [
                        {
                            "src": "url",
                            "url": "base64://eyJ0ZXN0IjogInRlc3QifQ==",  # base64 encoded {"test": "test"}
                            "ext": "txt",
                            "deferred": False,
                        }
                    ],
                }
            ],
        )
        payload = CreateDataLandingPayload(request_state=data_landing_request_state, public=True)
        response = self.dataset_populator.create_data_landing(payload)
        assert response.tool_id == "__DATA_FETCH__"

        tool_landing = self.dataset_populator.use_tool_landing(response.uuid)
        request_state = tool_landing.request_state
        assert request_state
        request_json = request_state["request_json"]
        assert request_json
        targets = request_json["targets"]
        assert targets
        assert len(targets) == 1
        target = targets[0]
        assert "elements" in target
        assert target["elements"]
        assert len(target["elements"]) == 1

    def test_file_landing_with_sample_sheet(self):
        """Test that sample sheet metadata is preserved through landing request creation and claiming."""
        file_landing_request_state = FileOrCollectionRequestsAdapter.validate_python(
            [
                {
                    "class": "Collection",
                    "collection_type": "sample_sheet",
                    "name": "test sample sheet",
                    "elements": [
                        {
                            "class": "File",
                            "identifier": "sample1",
                            "location": "base64://c2FtcGxlMQ==",  # base64 encoded "sample1"
                            "filetype": "txt",
                            "deferred": False,
                        },
                        {
                            "class": "File",
                            "identifier": "sample2",
                            "location": "base64://c2FtcGxlMg==",  # base64 encoded "sample2"
                            "filetype": "txt",
                            "deferred": False,
                        },
                    ],
                    "column_definitions": [
                        {"type": "int", "name": "replicate", "optional": False},
                        {"type": "string", "name": "condition", "optional": False},
                    ],
                    "rows": {
                        "sample1": [1, "control"],
                        "sample2": [2, "treatment"],
                    },
                },
            ],
        )
        payload = CreateFileLandingPayload(request_state=file_landing_request_state, public=True)
        response = self.dataset_populator.create_file_landing(payload)
        assert response.tool_id == "__DATA_FETCH__"

        # Verify the landing request has sample sheet metadata
        tool_landing = self.dataset_populator.use_tool_landing(response.uuid)
        request_state = tool_landing.request_state
        assert request_state
        request_json = request_state["request_json"]
        assert request_json
        targets = request_json["targets"]
        assert targets
        assert len(targets) == 1
        target = targets[0]

        # Check that column_definitions and rows were preserved
        assert "column_definitions" in target
        assert target["column_definitions"] is not None
        assert len(target["column_definitions"]) == 2
        assert target["column_definitions"][0]["name"] == "replicate"
        assert target["column_definitions"][0]["type"] == "int"
        assert target["column_definitions"][1]["name"] == "condition"
        assert target["column_definitions"][1]["type"] == "string"

        assert "rows" in target
        assert target["rows"] is not None
        assert "sample1" in target["rows"]
        assert target["rows"]["sample1"] == [1, "control"]
        assert "sample2" in target["rows"]
        assert target["rows"]["sample2"] == [2, "treatment"]

    def test_file_landing_with_sample_sheet_invalid_collection_type(self):
        """Test that sample sheet metadata with non-sample_sheet collection_type is rejected."""
        file_landing_request_state = FileOrCollectionRequestsAdapter.validate_python(
            [
                {
                    "class": "Collection",
                    "collection_type": "list",  # Invalid: should be "sample_sheet" or "sample_sheet:*"
                    "name": "invalid sample sheet",
                    "elements": [
                        {
                            "class": "File",
                            "identifier": "sample1",
                            "location": "base64://c2FtcGxlMQ==",
                            "filetype": "txt",
                            "deferred": False,
                        },
                    ],
                    "column_definitions": [
                        {"type": "int", "name": "replicate", "optional": False},
                    ],
                    "rows": {
                        "sample1": [1],
                    },
                },
            ],
        )
        payload = CreateFileLandingPayload(request_state=file_landing_request_state, public=True)
        response = self.dataset_populator.create_landing_raw(payload, "file")
        assert_status_code_is(response, 400)
        assert_error_code_is(response, 400008)
        assert "Sample sheet metadata" in response.text
        assert "can only be used with collection_type 'sample_sheet'" in response.text

    @skip_without_tool("cat1")
    def test_create_public_workflow_landing_authenticated_user(self):
        request = _get_simple_landing_payload(self.workflow_populator, public=True)
        response = self.dataset_populator.create_workflow_landing(request)
        assert response.workflow_id == request.workflow_id
        assert response.workflow_target_type == request.workflow_target_type

        with self._different_user():
            # Can use without claim
            _can_use_request(self.dataset_populator, response)

        with self._different_user(anon=True):
            # Cannot claim since can't run workflows
            _cannot_use_request(self.dataset_populator, response)

        # Should claim of public landing request be denied ?
        # Yes, so other user cannot own workflow in between use and invocation submission
        # No, since there's no way to delete a landing request. If you accidentally make something
        # with a private reference public you can't delete the landing page request.
        # TODO: allow deleting landing request, deny claiming public requests ?

        with self._different_user():
            _can_claim_request(self.dataset_populator, response)
            _can_use_request(self.dataset_populator, response)

        # Cannot use if other user claimed
        _cannot_claim_request(self.dataset_populator, response)

    @skip_without_tool("cat1")
    def test_create_public_workflow_landing_anonymous_user(self):
        # Anonymous user can create public landing request
        request = _get_simple_landing_payload(self.workflow_populator, public=True)
        with self._different_user(anon=True):
            response = self.dataset_populator.create_workflow_landing(request)

        with self._different_user():
            # Can use without claim
            _can_use_request(self.dataset_populator, response)

        with self._different_user(anon=True):
            # Cannot claim since can't run workflows
            _cannot_use_request(self.dataset_populator, response)

        with self._different_user():
            _can_claim_request(self.dataset_populator, response)
            _can_use_request(self.dataset_populator, response)

        # Cannot use if other user claimed
        _cannot_claim_request(self.dataset_populator, response)

    @skip_without_tool("cat1")
    def test_create_private_workflow_landing_authenticated_user(self):
        request = _get_simple_landing_payload(self.workflow_populator, public=False)
        response = self.dataset_populator.create_workflow_landing(request)
        with self._different_user():
            # Must be claimed first
            _cannot_use_request(self.dataset_populator, response, expect_status_code=409)
            _can_claim_request(self.dataset_populator, response)
            # Can be used after claim by same user
            _can_use_request(self.dataset_populator, response)

        # other user claimed, so we can't use
        _cannot_claim_request(self.dataset_populator, response)
        _cannot_use_request(self.dataset_populator, response)

    def test_invalid_workflow_landing_creation_cors(self):
        request = _get_simple_landing_payload(self.workflow_populator, public=True).model_dump()
        # Make payload invalid.
        request.pop("workflow_id")
        cors_headers = {"Access-Control-Request-Method": "POST", "Origin": "https://foo.example"}
        response = self._options(
            "workflow_landings",
            data=request,
            headers=cors_headers,
            json=True,
        )
        # CORS preflight request should succeed, doesn't matter that the payload is invalid
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "https://foo.example"
        response = self._post(
            "workflow_landings",
            data=request,
            headers=cors_headers,
            json=True,
        )
        assert response.status_code == 400
        assert response.headers["Access-Control-Allow-Origin"] == "https://foo.example"
        assert "Field required" in response.json()["err_msg"]

    @skip_without_tool("cat1")
    def test_create_private_workflow_landing_anonymous_user(self):
        request = _get_simple_landing_payload(self.workflow_populator, public=False)
        with self._different_user(anon=True):
            response = self.dataset_populator.create_workflow_landing(request)
        with self._different_user():
            # Must be claimed first
            _cannot_use_request(self.dataset_populator, response, expect_status_code=409)
            _can_claim_request(self.dataset_populator, response)
            # Can be used after claim by same user
            _can_use_request(self.dataset_populator, response)

        # other user claimed, so we can't use
        _cannot_claim_request(self.dataset_populator, response)
        _cannot_use_request(self.dataset_populator, response)

    @skip_without_tool("cat1")
    def test_workflow_landing_uniform_response(self):
        request = _get_simple_landing_payload(self.workflow_populator, public=True)
        response = self.dataset_populator.create_workflow_landing(request)
        landing_request = self.dataset_populator.use_workflow_landing_raw(response.uuid)
        # Make sure url is turned into location
        assert landing_request["request_state"]["WorkflowInput1"]["location"]

    def test_landing_claim_preserves_source_metadata(self):
        request = CreateWorkflowLandingRequestPayload(
            workflow_id="https://dockstore.org/api/ga4gh/trs/v2/tools/#workflow/github.com/iwc-workflows/chipseq-pe/main/versions/v0.12",
            workflow_target_type="trs_url",
            request_state={},
            public=True,
        )
        response = self.dataset_populator.create_workflow_landing(request)
        landing_request = self.dataset_populator.use_workflow_landing(response.uuid)
        workflow_id = landing_request.workflow_id
        workflow = self.workflow_populator._get(f"/api/workflows/{workflow_id}?instance=true").json()
        assert workflow["source_metadata"]["trs_tool_id"] == "#workflow/github.com/iwc-workflows/chipseq-pe/main"
        assert workflow["source_metadata"]["trs_version_id"] == "v0.12"

    @skip_without_tool("cat1")
    def test_workflow_landing_with_url_base64(self):
        """Test creating a workflow landing request using a URL (base64:// scheme)."""
        # Create a simple workflow definition
        workflow_dict = {
            "class": "GalaxyWorkflow",
            "inputs": {
                "WorkflowInput1": {"type": "data"},
            },
            "steps": {
                "0": {
                    "tool_id": "cat1",
                    "in": {
                        "input1": "WorkflowInput1",
                    },
                },
            },
        }

        # Convert workflow to YAML and encode as base64
        workflow_yaml = yaml.dump(workflow_dict)
        workflow_b64 = b64encode(workflow_yaml.encode("utf-8")).decode("utf-8")
        workflow_url = f"base64://{workflow_b64}"

        # Create workflow landing request with URL
        request_state = _workflow_request_state()
        request = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_url,
            workflow_target_type="url",
            request_state=request_state,
            public=True,
        )
        response = self.dataset_populator.create_workflow_landing(request)
        assert response.workflow_id == workflow_url
        assert response.workflow_target_type == "url"

        # Claim and use the landing request
        landing_request = self.dataset_populator.use_workflow_landing(response.uuid)
        # After claiming, the workflow should be imported and have a proper ID
        assert landing_request.workflow_id != workflow_url
        # The workflow should now have a workflow ID (not "url" anymore, since it's been imported)
        assert landing_request.workflow_target_type == "workflow"

        # Verify the workflow was imported correctly
        workflow = self.workflow_populator._get(f"/api/workflows/{landing_request.workflow_id}?instance=true").json()
        assert workflow["name"]
        # Verify the workflow has the expected structure
        assert len(workflow["steps"]) >= 1

    @skip_without_tool("cat1")
    def test_workflow_landing_to_invocation_association(self):
        """Test that landing_uuid is included in workflow invocation API response when invoked from landing request."""
        # Create a workflow landing request
        request = _get_simple_landing_payload(self.workflow_populator, public=True)
        landing_response = self.dataset_populator.create_workflow_landing(request)

        # Use the landing request
        claimed_response = self.dataset_populator.use_workflow_landing(landing_response.uuid)

        # Check that the workflow was invoked
        invocation_id = self.workflow_populator.invoke_workflow(
            claimed_response.workflow_id,
            inputs=claimed_response.request_state,
            request={"landing_uuid": str(landing_response.uuid)},
            inputs_by="name",
        ).json()["id"]
        invocation_details = self.workflow_populator.get_invocation(invocation_id)

        # Verify that the landing_uuid in the invocation matches the original landing request
        assert "landing_uuid" in invocation_details, "landing_uuid should be included in invocation response"
        assert invocation_details["landing_uuid"] == str(
            landing_response.uuid
        ), "landing_uuid should match the original landing request"

    @skip_without_tool("cat1")
    def test_workflow_landing_with_sample_sheet(self):
        """Test that workflow landing requests can include sample sheet metadata and it's preserved."""
        # Create a workflow (simple_workflow has inputs: WorkflowInput1 and WorkflowInput2)
        workflow_id = self.workflow_populator.simple_workflow("test_workflow_landing_sample_sheet")

        # Create request state with sample sheet collection
        # Note: Using WorkflowInput1 to match the workflow's expected input name
        input_b64_1 = b64encode(b"sample1 data").decode("utf-8")
        input_b64_2 = b64encode(b"sample2 data").decode("utf-8")
        request_state = {
            "WorkflowInput1": {
                "class": "Collection",
                "collection_type": "sample_sheet",
                "name": "test sample sheet",
                "elements": [
                    {
                        "class": "File",
                        "identifier": "sample1",
                        "url": f"base64://{input_b64_1}",
                        "ext": "txt",
                        "deferred": False,
                    },
                    {
                        "class": "File",
                        "identifier": "sample2",
                        "url": f"base64://{input_b64_2}",
                        "ext": "txt",
                        "deferred": False,
                    },
                ],
                "column_definitions": [
                    {"type": "int", "name": "replicate", "optional": False},
                    {"type": "string", "name": "condition", "optional": False},
                ],
                "rows": {
                    "sample1": [1, "control"],
                    "sample2": [2, "treatment"],
                },
            }
        }

        # Create workflow landing request with sample sheet
        landing_request = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type="stored_workflow",
            request_state=request_state,
            public=True,
        )
        landing_response = self.dataset_populator.create_workflow_landing(landing_request)

        # Use the landing request
        claimed_response = self.dataset_populator.use_workflow_landing(landing_response.uuid)

        # Verify sample sheet metadata is preserved in the claimed response
        workflow_input = claimed_response.request_state.get("WorkflowInput1")
        assert workflow_input is not None
        assert "column_definitions" in workflow_input
        assert workflow_input["column_definitions"] is not None
        assert len(workflow_input["column_definitions"]) == 2
        assert workflow_input["column_definitions"][0]["name"] == "replicate"
        assert workflow_input["column_definitions"][1]["name"] == "condition"

        assert "rows" in workflow_input
        assert workflow_input["rows"] is not None
        assert "sample1" in workflow_input["rows"]
        assert workflow_input["rows"]["sample1"] == [1, "control"]
        assert "sample2" in workflow_input["rows"]
        assert workflow_input["rows"]["sample2"] == [2, "treatment"]

    @skip_without_tool("cat1")
    def test_workflow_landing_with_sample_sheet_execution(self):
        """Test that executing a workflow from landing request preserves sample sheet metadata in output."""
        with self.dataset_populator.test_history() as history_id:
            # Create a simple workflow that maps cat1 over a collection input
            workflow_id = self.workflow_populator.upload_yaml_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: sample_sheet
steps:
  cat:
    tool_id: cat1
    in:
      input1: input_collection
"""
            )

            # Create request state with sample sheet collection
            input_b64_1 = b64encode(b"sample1 data").decode("utf-8")
            input_b64_2 = b64encode(b"sample2 data").decode("utf-8")
            row_data = {
                "sample1": [1, "control"],
                "sample2": [2, "treatment"],
            }
            request_state = {
                "input_collection": {
                    "class": "Collection",
                    "collection_type": "sample_sheet",
                    "name": "test sample sheet for execution",
                    "elements": [
                        {
                            "class": "File",
                            "identifier": "sample1",
                            "url": f"base64://{input_b64_1}",
                            "ext": "txt",
                            "deferred": False,
                        },
                        {
                            "class": "File",
                            "identifier": "sample2",
                            "url": f"base64://{input_b64_2}",
                            "ext": "txt",
                            "deferred": False,
                        },
                    ],
                    "column_definitions": [
                        {"type": "int", "name": "replicate", "optional": False},
                        {"type": "string", "name": "condition", "optional": False},
                    ],
                    "rows": row_data,
                }
            }

            # Create workflow landing request with sample sheet
            landing_request = CreateWorkflowLandingRequestPayload(
                workflow_id=workflow_id,
                workflow_target_type="stored_workflow",
                request_state=request_state,
                public=True,
            )
            landing_response = self.dataset_populator.create_workflow_landing(landing_request)

            # Use the landing request
            claimed_response = self.dataset_populator.use_workflow_landing(landing_response.uuid)

            # Invoke the workflow
            invocation_response = self.workflow_populator.invoke_workflow(
                claimed_response.workflow_id,
                inputs=claimed_response.request_state,
                history_id=history_id,
                inputs_by="name",
            )
            invocation_id = invocation_response.json()["id"]

            # Wait for workflow to complete
            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, claimed_response.workflow_id, invocation_id, assert_ok=True
            )

            # Get the output collections from the history
            collections = self.dataset_populator.get_history_contents_of_type(history_id, "dataset_collections")
            assert len(collections) >= 2, f"Expected at least 2 collections (input and output), got {len(collections)}"

            # Find the output collection (should be the last one created)
            output_collection = collections[-1]

            # Get full collection details
            collection_details = self.dataset_populator.get_history_collection_details(
                history_id, content_id=output_collection["id"]
            )

            # Verify sample sheet metadata is preserved
            assert "column_definitions" in collection_details
            assert collection_details["column_definitions"] is not None
            assert len(collection_details["column_definitions"]) == 2
            assert collection_details["column_definitions"][0]["name"] == "replicate"
            assert collection_details["column_definitions"][1]["name"] == "condition"

            # Verify elements have columns metadata
            assert "elements" in collection_details
            elements = collection_details["elements"]
            assert len(elements) == 2

            # Verify each element has correct columns
            for element in elements:
                element_id = element.get("element_identifier")
                expected_columns = row_data.get(element_id)

                assert "columns" in element, f"Element {element_id} missing columns"
                assert (
                    element["columns"] == expected_columns
                ), f"Element {element_id} has incorrect columns: {element['columns']}, expected {expected_columns}"

    @skip_without_tool("cat1")
    def test_workflow_landing_with_sample_sheet_paired_execution(self):
        """Test that executing a workflow from landing request preserves sample sheet metadata for paired collections."""
        with self.dataset_populator.test_history() as history_id:
            column_definitions = [
                {"type": "int", "name": "replicate", "optional": False},
                {"type": "string", "name": "condition", "optional": False},
            ]
            rows = {
                "sample1": [1, "control"],
                "sample2": [2, "treatment"],
            }

            workflow_id = self.workflow_populator.upload_yaml_workflow(
                """
class: GalaxyWorkflow
inputs:
  input_collection:
    type: collection
    collection_type: sample_sheet:paired
steps:
  cat:
    tool_id: cat1
    in:
      input1: input_collection
"""
            )

            # Create paired elements (forward/reverse for each sample)
            forward_b64_1 = b64encode(b"sample1 forward data").decode("utf-8")
            reverse_b64_1 = b64encode(b"sample1 reverse data").decode("utf-8")
            forward_b64_2 = b64encode(b"sample2 forward data").decode("utf-8")
            reverse_b64_2 = b64encode(b"sample2 reverse data").decode("utf-8")

            request_state = {
                "input_collection": {
                    "class": "Collection",
                    "collection_type": "sample_sheet:paired",
                    "name": "test sample sheet paired for execution",
                    "elements": [
                        {
                            "class": "Collection",
                            "identifier": "sample1",
                            "collection_type": "paired",
                            "elements": [
                                {
                                    "class": "File",
                                    "identifier": "forward",
                                    "url": f"base64://{forward_b64_1}",
                                    "ext": "txt",
                                    "deferred": False,
                                },
                                {
                                    "class": "File",
                                    "identifier": "reverse",
                                    "url": f"base64://{reverse_b64_1}",
                                    "ext": "txt",
                                    "deferred": False,
                                },
                            ],
                        },
                        {
                            "class": "Collection",
                            "identifier": "sample2",
                            "collection_type": "paired",
                            "elements": [
                                {
                                    "class": "File",
                                    "identifier": "forward",
                                    "url": f"base64://{forward_b64_2}",
                                    "ext": "txt",
                                    "deferred": False,
                                },
                                {
                                    "class": "File",
                                    "identifier": "reverse",
                                    "url": f"base64://{reverse_b64_2}",
                                    "ext": "txt",
                                    "deferred": False,
                                },
                            ],
                        },
                    ],
                    "column_definitions": column_definitions,
                    "rows": rows,
                }
            }

            landing_request = CreateWorkflowLandingRequestPayload(
                workflow_id=workflow_id,
                workflow_target_type="stored_workflow",
                request_state=request_state,
                public=True,
            )
            landing_response = self.dataset_populator.create_workflow_landing(landing_request)

            claimed_response = self.dataset_populator.use_workflow_landing(landing_response.uuid)
            invocation_response = self.workflow_populator.invoke_workflow(
                claimed_response.workflow_id,
                inputs=claimed_response.request_state,
                history_id=history_id,
                inputs_by="name",
            )
            invocation_id = invocation_response.json()["id"]

            self.workflow_populator.wait_for_invocation_and_jobs(
                history_id, claimed_response.workflow_id, invocation_id, assert_ok=True
            )

            collections = self.dataset_populator.get_history_contents_of_type(history_id, "dataset_collections")
            assert len(collections) >= 2, f"Expected at least 2 collections (input and output), got {len(collections)}"
            output_collection = collections[-1]
            collection_details = self.dataset_populator.get_history_collection_details(
                history_id, content_id=output_collection["id"]
            )

            assert "column_definitions" in collection_details
            assert collection_details["column_definitions"] is not None
            assert len(collection_details["column_definitions"]) == 2
            assert collection_details["column_definitions"][0]["name"] == "replicate"
            assert collection_details["column_definitions"][1]["name"] == "condition"

            assert "elements" in collection_details
            elements = collection_details["elements"]
            assert len(elements) == 2

            for element in elements:
                element_id = element.get("element_identifier")
                expected_columns = rows.get(element_id)  # Reuse shared rows data

                assert "columns" in element, f"Element {element_id} missing columns"
                assert (
                    element["columns"] == expected_columns
                ), f"Element {element_id} has incorrect columns: {element['columns']}, expected {expected_columns}"

                # Additional verification specific to paired collections
                assert element.get("element_type") == "dataset_collection"
                assert "object" in element
                inner_collection = element["object"]
                assert inner_collection["collection_type"] == "paired"

                # Verify inner paired elements exist but don't have columns (only outer elements do)
                assert "elements" in inner_collection
                paired_elements = inner_collection["elements"]
                assert len(paired_elements) == 2
                for paired_element in paired_elements:
                    assert paired_element.get("columns") is None, (
                        f"Inner element {paired_element.get('element_identifier')} "
                        "should not have columns (only outer collection elements have sample sheet metadata)"
                    )


def _workflow_request_state() -> dict[str, Any]:
    deferred = False
    input_b64_1 = b64encode(b"1 2 3").decode("utf-8")
    input_b64_2 = b64encode(b"4 5 6").decode("utf-8")
    inputs = {
        "WorkflowInput1": {"src": "url", "url": f"base64://{input_b64_1}", "ext": "txt", "deferred": deferred},
        "WorkflowInput2": {"src": "url", "url": f"base64://{input_b64_2}", "ext": "txt", "deferred": deferred},
    }
    return inputs


def _get_simple_landing_payload(workflow_populator: WorkflowPopulator, public: bool = False):
    workflow_id = workflow_populator.simple_workflow("test_landing")
    if public:
        workflow_populator.make_public(workflow_id)
    workflow_target_type = "stored_workflow"
    request_state = _workflow_request_state()
    return CreateWorkflowLandingRequestPayload(
        workflow_id=workflow_id,
        workflow_target_type=workflow_target_type,
        request_state=request_state,
        public=public,
    )


def _can_claim_request(dataset_populator: DatasetPopulator, request: WorkflowLandingRequest):
    response = dataset_populator.claim_workflow_landing(request.uuid)
    assert response.workflow_id == request.workflow_id
    assert response.workflow_target_type == request.workflow_target_type


def _cannot_claim_request(dataset_populator: DatasetPopulator, request: WorkflowLandingRequest):
    exception_encountered = False
    try:
        _can_claim_request(dataset_populator, request)
    except Exception as e:
        assert "Request status code (403)" in str(e)
        exception_encountered = True
    assert exception_encountered, "Expected claim to fail"


def _can_use_request(dataset_populator: DatasetPopulator, request: WorkflowLandingRequest):
    response = dataset_populator.use_workflow_landing(request.uuid)
    assert response.workflow_id == request.workflow_id
    assert response.workflow_target_type == request.workflow_target_type


def _cannot_use_request(
    dataset_populator: DatasetPopulator, request: WorkflowLandingRequest, expect_status_code: int = 403
):
    exception_encountered = False
    try:
        _can_use_request(dataset_populator, request)
    except Exception as e:
        assert f"Request status code ({expect_status_code})" in str(e)
        exception_encountered = True
    assert exception_encountered, "Expected landing page usage to fail"
