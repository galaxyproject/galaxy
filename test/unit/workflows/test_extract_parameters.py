from functools import partial
from json import loads
from types import SimpleNamespace
from typing import (
    Any,
    cast,
)
from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.managers.context import ProvidesHistoryContext
from galaxy.tools.parameters import (
    params_from_strings,
    params_to_strings,
    ToolInputsT,
)
from galaxy.tools.parameters.basic import TextToolParameter
from galaxy.tools.parameters.grouping import (
    Conditional,
    ConditionalWhen,
    Repeat,
)
from galaxy.util import XML
from galaxy.workflow.extract import _connect_parameter_inputs


@pytest.mark.parametrize("group", [None, "repeat", "conditional"])
@pytest.mark.parametrize("source_invocation_id", [1, 2, None])
def test_parameter_connections_require_selected_source_from_same_invocation(group, source_invocation_id):
    parameter = TextToolParameter(None, XML('<param name="text" type="text"/>'))
    inputs: ToolInputsT = {"text": parameter}
    values: dict[str, Any] = {"text": "recorded value"}
    input_name = "text"
    if group == "repeat":
        repeat = Repeat("repeat")
        repeat.title = "Repeat"
        repeat.inputs = inputs
        inputs = {"repeat": repeat}
        values = {"repeat": [{"__index__": 0, **values}]}
        input_name = "repeat_0|text"
    elif group == "conditional":
        conditional = Conditional("conditional")
        conditional.test_param = TextToolParameter(None, XML('<param name="selector" type="text"/>'))
        case = ConditionalWhen()
        case.value = "selected"
        case.inputs = inputs
        conditional.cases = [case]
        inputs = {"conditional": conditional}
        values = {"conditional": {"__current_case__": 0, "selector": "selected", **values}}
        input_name = "conditional|text"
    tool = SimpleNamespace(
        inputs=inputs,
        params_from_strings=partial(params_from_strings, inputs, app=None),
        params_to_strings=partial(params_to_strings, inputs),
    )
    trans = SimpleNamespace(app=SimpleNamespace(toolbox=Mock()), user=None)
    trans.app.toolbox.tool_for_job.return_value = tool
    original_source = model.WorkflowStep()
    original_source.id = 10
    original_consumer = model.WorkflowStep()
    original_consumer.id = 11
    connection = original_consumer.add_connection(input_name, "text_out", original_source)
    connection.output_step_id = original_source.id

    source_job, source_step = _job_step(original_source, source_invocation_id or 1)
    consumer_job, consumer_step = _job_step(original_consumer, 1)
    consumer_step.tool_inputs = params_to_strings(inputs, values, None)
    # The consumer can precede the producer in the selection payload.
    job_steps = [(consumer_job, consumer_step)]
    if source_invocation_id is not None:
        job_steps.append((source_job, source_step))
    _connect_parameter_inputs(cast(ProvidesHistoryContext, trans), job_steps)

    state = {key: loads(value) for key, value in consumer_step.tool_inputs.items()}
    if group == "repeat":
        state = state["repeat"][0]
    elif group == "conditional":
        state = state["conditional"]
        assert state["selector"] == "selected"
        assert state["__current_case__"] == 0
    value = state["text"]
    if source_invocation_id == 1:
        (connection,) = consumer_step.input_connections
        assert connection.input_name == input_name
        assert connection.output_step is source_step
        assert connection.output_name == "text_out"
        assert value == {"__class__": "ConnectedValue"}
    else:
        assert not consumer_step.input_connections
        assert value == "recorded value"


def test_standalone_job_does_not_need_invocation():
    trans = Mock()
    step = model.WorkflowStep()
    step.tool_inputs = {"text": '"recorded value"'}
    _connect_parameter_inputs(trans, [(model.Job(), step)])
    assert not step.input_connections
    assert step.tool_inputs == {"text": '"recorded value"'}
    trans.app.toolbox.tool_for_job.assert_not_called()


def _job_step(original_step, invocation_id):
    job = model.Job()
    invocation_step = model.WorkflowInvocationStep()
    invocation_step.workflow_invocation_id = invocation_id
    invocation_step.workflow_step_id = original_step.id
    invocation_step.workflow_step = original_step
    invocation_step.job = job
    step = model.WorkflowStep()
    step.type = "tool"
    step.tool_inputs = {}
    return job, step
