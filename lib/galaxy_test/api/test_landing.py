from base64 import b64encode
from typing import (
    Any,
)

from pydantic import HttpUrl

from galaxy.schema.fetch_data import (
    CreateDataLandingPayload,
    DataLandingRequestState,
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
        response = self.dataset_populator.create_tool_landing_raw(request)
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
