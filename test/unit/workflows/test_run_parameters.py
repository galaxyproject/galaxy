from galaxy import model
from galaxy.model.unittest_utils.utils import random_email
from galaxy.workflow.run_request import (
    _normalize_inputs,
    _normalize_step_parameters,
)
from .workflow_support import MockTrans

STEP_ID_OFFSET = 4  # Offset a little so ids and order index are different.


def test_normalize_parameters_empty():
    normalized_params = __normalize_parameters_against_fixture({})
    assert normalized_params == {}


def test_normalize_parameters_by_tool():
    normalized_params = __normalize_parameters_against_fixture({"cat1": {"foo": "bar"}})
    # Tool specified parameters are expanded out.
    assert normalized_params[STEP_ID_OFFSET + 3] == {"foo": "bar"}
    assert normalized_params[STEP_ID_OFFSET + 4] == {"foo": "bar"}
    assert len(normalized_params.keys()) == 2


def test_step_parameters():
    normalized_params = __normalize_parameters_against_fixture({str(STEP_ID_OFFSET + 1): {"foo": "bar"}})
    assert normalized_params[STEP_ID_OFFSET + 1] == {"foo": "bar"}
    assert len(normalized_params.keys()) == 1


def test_step_parameters_legacy():
    normalized_params = __normalize_parameters_against_fixture(
        {str(STEP_ID_OFFSET + 1): {"param": "foo", "value": "bar"}}
    )
    assert normalized_params[STEP_ID_OFFSET + 1] == {"foo": "bar"}, normalized_params
    assert len(normalized_params.keys()) == 1


def test_inputs_by_step_id():
    input1 = __new_input()
    input2 = __new_input()
    normalized_inputs = __normalize_inputs_against_fixture(
        {str(STEP_ID_OFFSET + 1): input1, str(STEP_ID_OFFSET + 2): input2}, inputs_by="step_id"
    )
    assert normalized_inputs[STEP_ID_OFFSET + 1]["content"] == input1["content"]
    assert normalized_inputs[STEP_ID_OFFSET + 2]["content"] == input2["content"]


def test_inputs_by_step_index():
    input1 = __new_input()
    input2 = __new_input()
    normalized_inputs = __normalize_inputs_against_fixture({str(0): input1, str(1): input2}, inputs_by="step_index")
    assert normalized_inputs[STEP_ID_OFFSET + 1]["content"] == input1["content"]
    assert normalized_inputs[STEP_ID_OFFSET + 2]["content"] == input2["content"]


def test_inputs_by_name():
    input1 = __new_input()
    input2 = __new_input()
    normalized_inputs = __normalize_inputs_against_fixture({"input1": input1, "input2": input2}, inputs_by="name")
    assert normalized_inputs[STEP_ID_OFFSET + 1]["content"] == input1["content"]
    assert normalized_inputs[STEP_ID_OFFSET + 2]["content"] == input2["content"]


def __normalize_parameters_against_fixture(params):
    trans = MockTrans()
    # Create a throw away workflow so step ids and order_index
    # are different for actual fixture.
    __workflow_fixure(trans)

    workflow = __workflow_fixure(trans)
    normalized_params = _normalize_step_parameters(workflow.steps, params, legacy=True)
    return normalized_params


def __normalize_inputs_against_fixture(inputs, inputs_by):
    trans = MockTrans()
    # Create a throw away workflow so step ids and order_index
    # are different for actual fixture.
    __workflow_fixure(trans)

    workflow = __workflow_fixure(trans)
    normalized_inputs = _normalize_inputs(workflow.steps, inputs, inputs_by)
    return normalized_inputs


def __new_input():
    return dict(content=model.HistoryDatasetAssociation())


def __workflow_fixure(trans):
    user = model.User(email=random_email(), password="pass")
    stored_workflow = model.StoredWorkflow()
    stored_workflow.user = user
    workflow = model.Workflow()
    workflow.stored_workflow = stored_workflow

    def add_step(**kwds):
        workflow_step = model.WorkflowStep()
        for key, value in kwds.items():
            setattr(workflow_step, key, value)
        workflow.steps.append(workflow_step)

    session = trans.app.model.context
    session.add(workflow)

    add_step(type="data_input", order_index=0, tool_inputs={"name": "input1"})
    add_step(type="data_input", order_index=1, tool_inputs={"name": "input2"})
    add_step(
        type="tool",
        tool_id="cat1",
        order_index=2,
    )
    add_step(
        type="tool",
        tool_id="cat1",
        order_index=4,
    )
    session.commit()
    # Expunge and reload to ensure step state is as expected from database.
    workflow_id = workflow.id
    session.expunge_all()

    return session.get(model.Workflow, workflow_id)
