from base64 import b64encode
from typing import (
    Any,
    Dict,
)

from galaxy.schema.schema import (
    CreateWorkflowLandingRequestPayload,
    WorkflowLandingRequest,
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


def _workflow_request_state() -> Dict[str, Any]:
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
