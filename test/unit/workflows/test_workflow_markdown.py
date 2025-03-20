from unittest import mock

from galaxy import model
from galaxy.managers.markdown_parse import validate_galaxy_markdown
from galaxy.managers.markdown_util import (
    populate_invocation_markdown,
    resolve_invocation_markdown,
)
from .test_workflow_progress import TEST_WORKFLOW_YAML
from .workflow_support import (
    MockTrans,
    yaml_to_model,
)


def test_workflow_section_expansion():
    workflow_markdown = """
## Workflow
```galaxy
workflow_display()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "## Workflow\n" in galaxy_markdown
    assert "```galaxy\nworkflow_display(invocation_id=44)\n```\n" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "```galaxy\nworkflow_display(workflow_id=342, workflow_checkpoint=0)\n```" in galaxy_markdown


def test_inputs_section_expansion():
    workflow_markdown = """
## Workflow Inputs
```galaxy
invocation_inputs()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "## Workflow Inputs" in galaxy_markdown
    assert "```galaxy\ninvocation_inputs(invocation_id=44)\n```" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "Input Dataset: input1" in galaxy_markdown
    assert '```galaxy\nhistory_dataset_display(input="input1")\n```' in galaxy_markdown
    assert len(galaxy_markdown.split("```")) == 3


def test_outputs_section_expansion():
    workflow_markdown = """
## Workflow Outputs
```galaxy
invocation_outputs()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "## Workflow Outputs" in galaxy_markdown
    assert "```galaxy\ninvocation_outputs(invocation_id=44)" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "Output Dataset: output_label" in galaxy_markdown
    assert '```galaxy\nhistory_dataset_display(output="output_label")\n```' in galaxy_markdown
    assert len(galaxy_markdown.split("```")) == 5


def test_input_reference_mapping():
    workflow_markdown = """
And outputs...

```galaxy
history_dataset_peek(input=input1)
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "```galaxy\nhistory_dataset_peek(invocation_id=44, input=input1)\n```" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "```galaxy\nhistory_dataset_peek(history_dataset_id=567)\n```" in galaxy_markdown


def test_invocation_time():
    workflow_markdown = """
And outputs...

```galaxy
invocation_time()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "```galaxy\ninvocation_time(invocation_id=44)\n```" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "```galaxy\ninvocation_time(invocation_id=44)\n```" in galaxy_markdown


def test_output_reference_mapping():
    workflow_markdown = """
And outputs...

```galaxy
history_dataset_as_image(output=output_label)
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "```galaxy\nhistory_dataset_as_image(invocation_id=44, output=output_label)\n```" in galaxy_markdown
    galaxy_markdown = resolve_markdown(galaxy_markdown)
    assert "```galaxy\nhistory_dataset_as_image(history_dataset_id=563)\n```" in galaxy_markdown


def test_populating_invocation_json():
    workflow_markdown_0 = """
```any
{
    "invocation_id": "",
    "other_key": "other_value"
}
```
"""
    workflow_markdown_1 = """
```any
{
    "nested_structure": {
        "invocation_id": ""
    }
}
```
"""
    workflow_markdown_2 = """
{
    "invocation_id": ""
}
"""
    galaxy_markdown = populate_markdown(workflow_markdown_0)
    assert '\n```any\n{\n    "invocation_id": "44",\n    "other_key": "other_value"\n}\n```\n' in galaxy_markdown
    galaxy_markdown = populate_markdown(workflow_markdown_1)
    assert '\n```any\n{\n    "nested_structure": {\n        "invocation_id": "44"\n    }\n}\n```\n' in galaxy_markdown
    galaxy_markdown = populate_markdown(workflow_markdown_2)
    assert '\n{\n    "invocation_id": ""\n}\n' in galaxy_markdown


def populate_markdown(workflow_markdown):
    # Add invocation ids to internal Galaxy markdown
    trans = MockTrans()
    validate_galaxy_markdown(workflow_markdown)
    galaxy_markdown = populate_invocation_markdown(trans, example_invocation(trans), workflow_markdown)
    return galaxy_markdown


def resolve_markdown(workflow_markdown):
    # Convert internal Galaxy markdown with invocation ids and labels
    # to object id references and expanded sections.
    trans = MockTrans()
    validate_galaxy_markdown(workflow_markdown)
    trans.app.workflow_manager = mock.MagicMock()
    invocation = example_invocation(trans)
    trans.app.workflow_manager.get_invocation.side_effect = [invocation, invocation]
    galaxy_markdown = resolve_invocation_markdown(trans, workflow_markdown)
    return galaxy_markdown


def example_invocation(trans):
    invocation = model.WorkflowInvocation()
    workflow = yaml_to_model(TEST_WORKFLOW_YAML)
    workflow.id = 342
    invocation.id = 44
    invocation.workflow = workflow

    # TODO: fix this to use workflow id and eliminate hack.
    stored_workflow = model.StoredWorkflow()
    stored_workflow.id = 342
    invocation.workflow.stored_workflow = stored_workflow

    hda = model.HistoryDatasetAssociation(create_dataset=True, sa_session=trans.sa_session)
    hda.id = 567
    invocation.add_input(hda, step=workflow.steps[0])
    out_hda = model.HistoryDatasetAssociation(create_dataset=True, sa_session=trans.sa_session)
    out_hda.id = 563
    wf_output = model.WorkflowOutput(workflow.steps[2], label="output_label")
    invocation.add_output(wf_output, workflow.steps[2], out_hda)
    return invocation
