"""Lighter-weight variant of Planemo runnable outputs."""
from galaxy.tool_util.parser import get_tool_source
from .parser import workflow_proxy
from .util import guess_artifact_type


def get_outputs(path):
    tool_or_workflow = guess_artifact_type(path)
    if tool_or_workflow == "tool":
        tool_source = get_tool_source(path)
        output_datasets, _ = tool_source.parse_outputs(None)
        outputs = [ToolOutput(o) for o in output_datasets.values()]
        return outputs
    else:
        workflow = workflow_proxy(path, strict_cwl_validation=False)
        return [CwlWorkflowOutput(label) for label in workflow.output_labels]


class CwlWorkflowOutput:
    def __init__(self, label):
        self._label = label

    def get_id(self):
        return self._label


class ToolOutput:
    def __init__(self, tool_output):
        self._tool_output = tool_output

    def get_id(self):
        return self._tool_output.name
