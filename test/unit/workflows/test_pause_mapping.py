from unittest.mock import Mock

import pytest

from galaxy import model
from galaxy.model.dataset_collections import (
    matching,
    registry,
    type_description,
)
from galaxy.model.dataset_collections.structure import Tree
from galaxy.tools.parameters.workflow_utils import NO_REPLACEMENT
from galaxy.workflow import modules
from galaxy.workflow.run import WorkflowProgress
from .workflow_support import yaml_to_model


@pytest.mark.parametrize("input_binding", [False, True])
@pytest.mark.parametrize("legacy_output", [False, True])
@pytest.mark.parametrize("missing_input", [False, True])
def test_reviewed_pause_preserves_mapping_across_recovery(input_binding, legacy_output, missing_input):
    workflow = yaml_to_model("""
steps:
  - type: data_input
  - type: pause
    inputs:
      input:
        connections:
          - "@output_step": 0
            output_name: output
""")
    source, pause = workflow.steps
    invocation = model.WorkflowInvocation(workflow=workflow)
    invocation_step = model.WorkflowInvocationStep(workflow_step=pause, workflow_invocation=invocation)
    invocation_step.workflow_step_id = pause.id
    invocation_step.action = True
    output = model.HistoryDatasetCollectionAssociation(
        collection=model.DatasetCollection(collection_type="list", populated=True)
    )
    output.collection.populated_state = model.DatasetCollection.populated_states.OK
    types = type_description.CollectionTypeDescriptionFactory(registry.DatasetCollectionTypesRegistry())
    axis = matching.MatchingCollectionAxis(Tree([], types.for_collection_type("list")), "samples")
    reference = matching.MatchingCollectionAxisReference.from_axis(axis)
    if missing_input:
        output = NO_REPLACEMENT
    progress = WorkflowProgress(invocation, {}, Mock(), {})
    progress.outputs[source.id] = {"output": output}
    if input_binding:
        progress.inherited_input_axes[source.id] = (axis,)
    else:
        progress.output_mapping_axes[(source.id, "output")] = (reference,)
    if legacy_output and not missing_input:
        invocation_step.add_output("output", output)

    module = object.__new__(modules.PauseModule)
    module.recover_mapping(invocation_step, progress)

    assert progress.output_mapping_axes[(pause.id, "output")] == ((axis,) if input_binding else (reference,))
    assert progress.outputs[pause.id]["output"] is output
    assert len(set(invocation_step.output_dataset_collections)) == (0 if missing_input else 1)

    recovered = WorkflowProgress(invocation, {}, Mock(), {})
    recovered.outputs[source.id] = {"output": output}
    recovered.output_mapping_axes[(source.id, "output")] = (reference,)
    module.recover_outputs(invocation_step, recovered)
    module.recover_mapping(invocation_step, recovered)

    assert recovered.output_mapping_axes[(pause.id, "output")] == (reference,)
    assert recovered.outputs[pause.id]["output"] is output
    assert len(set(invocation_step.output_dataset_collections)) == (0 if missing_input else 1)
