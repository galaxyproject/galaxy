from base64 import b64encode
from typing import (
    Any,
    Dict,
)

from galaxy.schema.schema import (
    CreateToolLandingRequestPayload,
    CreateWorkflowLandingRequestPayload,
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
        )
        response = self.dataset_populator.create_tool_landing(request)
        assert response.tool_id == "create_2"
        assert response.state == "unclaimed"
        response = self.dataset_populator.claim_tool_landing(response.uuid)
        assert response.tool_id == "create_2"
        assert response.state == "claimed"

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

    @skip_without_tool("cat1")
    def test_workflow_landing(self):
        workflow_id = self.workflow_populator.simple_workflow("test_landing")
        workflow_target_type = "stored_workflow"
        request_state = _workflow_request_state()
        request = CreateWorkflowLandingRequestPayload(
            workflow_id=workflow_id,
            workflow_target_type=workflow_target_type,
            request_state=request_state,
        )
        response = self.dataset_populator.create_workflow_landing(request)
        assert response.workflow_id == workflow_id
        assert response.workflow_target_type == workflow_target_type

        response = self.dataset_populator.claim_workflow_landing(response.uuid)
        assert response.workflow_id == workflow_id
        assert response.workflow_target_type == workflow_target_type


def _workflow_request_state() -> Dict[str, Any]:
    deferred = False
    input_b64_1 = b64encode(b"1 2 3").decode("utf-8")
    input_b64_2 = b64encode(b"4 5 6").decode("utf-8")
    inputs = {
        "WorkflowInput1": {"src": "url", "url": f"base64://{input_b64_1}", "ext": "txt", "deferred": deferred},
        "WorkflowInput2": {"src": "url", "url": f"base64://{input_b64_2}", "ext": "txt", "deferred": deferred},
    }
    return inputs
