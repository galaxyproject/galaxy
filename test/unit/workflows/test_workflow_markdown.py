from galaxy import model
from galaxy.managers.markdown_parse import validate_galaxy_markdown
from galaxy.managers.markdown_util import (populate_invocation_markdown, resolve_invocations)
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


def test_inputs_section_expansion():
    workflow_markdown = """
## Workflow Inputs
```galaxy
invocation_inputs()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "## Workflow Inputs" in galaxy_markdown
    assert "```galaxy\ninvocation_inputs(invocation_id=44)\n" in galaxy_markdown
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


def test_input_reference_mapping():
    workflow_markdown = """
And outputs...

```galaxy
history_dataset_peek(input=input1)
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
    assert "```galaxy\nhistory_dataset_peek(invocation_id=44, input=input1)\n```" in galaxy_markdown


def test_invocation_time():
    workflow_markdown = """
And outputs...

```galaxy
invocation_time()
```
"""
    galaxy_markdown = populate_markdown(workflow_markdown)
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


def test_basic_output_reference_mapping():
    workflow_markdown = """
And outputs...

```galaxy
history_dataset_as_image(output=output_label)
```
"""
    galaxy_markdown = resolve_markdown(populate_markdown(workflow_markdown))
    assert "```galaxy\nhistory_dataset_as_image(invocation_id=44, output=output_label)\n```" in galaxy_markdown


def populate_markdown(workflow_markdown):
    # Convert workflow markdown to internal Galaxy markdown with object id references
    # and with sections expanded.
    trans = MockTrans()
    validate_galaxy_markdown(workflow_markdown)
    galaxy_markdown = populate_invocation_markdown(trans, example_invocation(trans), workflow_markdown)
    return galaxy_markdown


def resolve_markdown(workflow_markdown):
    # Convert workflow markdown to internal Galaxy markdown with object id references
    # and with sections expanded.
    trans = MockTrans()
    validate_galaxy_markdown(workflow_markdown)
    galaxy_markdown = resolve_invocation_markdown(trans, example_invocation(trans), galaxy_markdown)
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
