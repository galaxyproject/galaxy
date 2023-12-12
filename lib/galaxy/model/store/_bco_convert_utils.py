import urllib.parse
from typing import (
    List,
    Set,
)

from galaxy.model import (
    Workflow,
    WorkflowStep,
)
from galaxy.schema.bco import (
    ExecutionDomainUri,
    SoftwarePrerequisite,
)


class SoftwarePrerequisiteTracker:
    _recorded_tools: Set[str] = set()
    _software_prerequisites: List[SoftwarePrerequisite] = []

    def register_step(self, step: WorkflowStep) -> None:
        if step.type != "tool":
            # TODO: walk subworkflow steps someday...
            return
        tool_id = step.tool_id
        if tool_id in self._recorded_tools:
            return

        tool_version = step.tool_version
        assert tool_id
        self._recorded_tools.add(tool_id)
        uri_safe_tool_id = urllib.parse.quote(tool_id)
        if "repos/" in tool_id:
            # tool shed tool - give them a link...
            uri = f"https://{uri_safe_tool_id}"
        else:
            uri = f"gxstocktools://galaxyproject.org/{uri_safe_tool_id}"

        access_time = None  # used to be uuid - but Pydanic validation... rightfully... disallows this
        software_prerequisite = SoftwarePrerequisite(
            name=tool_id,
            version=tool_version,
            uri=ExecutionDomainUri(uri=uri, access_time=access_time),
        )
        self._software_prerequisites.append(software_prerequisite)

    @property
    def software_prerequisites(self) -> List[SoftwarePrerequisite]:
        return self._software_prerequisites


def bco_workflow_version(workflow: Workflow) -> str:
    current_version = 0
    for i, w in enumerate(reversed(workflow.stored_workflow.workflows)):
        if workflow == w:
            current_version = i
    return f"{current_version}.0"
