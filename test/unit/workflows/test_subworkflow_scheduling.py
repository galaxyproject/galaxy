from types import SimpleNamespace

import pytest

from galaxy import model
from galaxy.model.dataset_collections import matching
from galaxy.schema.invocation import CancelReason
from galaxy.workflow import modules


class ChildInvoker:
    def __init__(self, initial_state, next_state, workflow, output):
        self.workflow_invocation = model.WorkflowInvocation(state=initial_state)
        self.workflow = workflow
        self.next_state = next_state
        self.invoke_count = 0
        self.output_read_count = 0
        self.output = output
        self.progress = SimpleNamespace(
            output_mapping_axes={},
            get_replacement_workflow_output=self.read_output,
        )

    def invoke(self):
        self.invoke_count += 1
        self.workflow_invocation.state = self.next_state

    def read_output(self, workflow_output):
        self.output_read_count += 1
        return self.output


class CollectionManager:
    def __init__(self):
        self.match_count = 0

    def match_collections(self, collections):
        self.match_count += 1
        return matching.MatchingCollections.for_collections(collections, self.collection_type_descriptions)

    collection_type_descriptions = modules.COLLECTION_TYPE_DESCRIPTION_FACTORY


def scheduling_case(initial_state, next_state):
    child_workflow = model.Workflow()
    output_step = model.WorkflowStep()
    output_step.type = "tool"
    output_step.id = 2
    output_step.workflow = child_workflow
    model.WorkflowOutput(output_step, "output", "result")
    output = model.HistoryDatasetAssociation(create_dataset=True, flush=False)
    child = ChildInvoker(initial_state, next_state, child_workflow, output)
    collection_manager = CollectionManager()
    trans = SimpleNamespace(app=SimpleNamespace(dataset_collection_manager=collection_manager))
    module = object.__new__(modules.SubWorkflowModule)
    module.trans = trans
    module.subworkflow = child_workflow
    caller_step = model.WorkflowStep()
    caller_step.type = "subworkflow"
    invocation_step = model.WorkflowInvocationStep(workflow_step=caller_step)
    propagated_delays = []
    recorded_outputs = {}
    progress = SimpleNamespace(
        when_values=None,
        subworkflow_collection_info=None,
        _subworkflow_invocation=lambda step: child.workflow_invocation,
        subworkflow_invoker=lambda *args, **kwds: child,
        record_subworkflow_delays=propagated_delays.append,
        set_step_outputs=lambda step, outputs, **kwds: recorded_outputs.update(outputs),
    )
    return module, progress, invocation_step, child, collection_manager, propagated_delays, recorded_outputs


@pytest.mark.parametrize("state", ["failed", "cancelling", "cancelled"])
@pytest.mark.parametrize("already_terminal", [False, True])
def test_terminal_child_stops_subworkflow_execution(state, already_terminal):
    module, progress, step, child, manager, _delays, outputs = scheduling_case(
        state if already_terminal else "ready", state
    )
    expected_error = modules.exceptions.MessageException if state == "failed" else modules.CancelWorkflowEvaluation

    with pytest.raises(expected_error) as exc:
        module.execute(module.trans, progress, step)

    if state == "failed":
        assert str(exc.value) == "Subworkflow invocation failed"
    else:
        assert exc.value.why.reason == CancelReason.user_request
    assert child.invoke_count == (0 if already_terminal else 1)
    assert manager.match_count == (0 if already_terminal else 1)
    assert child.output_read_count == 0
    assert outputs == {}


@pytest.mark.parametrize("state", ["new", "ready"])
def test_unfinished_child_delays_caller_before_exporting_outputs(state):
    module, progress, step, child, _manager, delays, outputs = scheduling_case("ready", state)

    with pytest.raises(modules.DelayedWorkflowEvaluation) as exc:
        module.execute(module.trans, progress, step)

    assert exc.value.inherited
    assert delays == [child.progress]
    assert child.output_read_count == 0
    assert outputs == {}


@pytest.mark.parametrize("state", ["scheduled", "completed"])
def test_finished_child_exports_outputs(state):
    module, progress, step, child, _manager, delays, outputs = scheduling_case("ready", state)

    module.execute(module.trans, progress, step)

    assert child.invoke_count == 1
    assert child.output_read_count == 1
    assert delays == [child.progress]
    assert outputs == {"result": child.output}
