"""Turn the output changes requested for a tool run into post job actions."""

from collections import defaultdict
from collections.abc import Mapping
from typing import (
    Any,
    TYPE_CHECKING,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import (
    Job,
    PostJobAction,
)
from galaxy.schema.tool_outputs import ToolOutputActions

if TYPE_CHECKING:
    from galaxy.tools import Tool


def post_job_actions_for_outputs(tool: "Tool", output_actions: Mapping[str, ToolOutputActions]) -> list[PostJobAction]:
    """Return the post job actions that make the requested changes to the outputs of ``tool``.

    Raises ``RequestParameterInvalidException`` for names that aren't outputs of the tool, for
    tags with a comma and for tools whose action does not run post job actions.
    """
    from galaxy.tools.actions import DefaultToolAction

    if output_actions and not isinstance(tool.tool_action, DefaultToolAction):
        raise RequestParameterInvalidException(f"The outputs of tool '{tool.id}' can't be renamed, tagged or hidden.")
    if unknown := sorted(set(output_actions) - set(tool.outputs)):
        raise RequestParameterInvalidException(f"Tool '{tool.id}' has no output named {', '.join(unknown)}.")
    for actions in output_actions.values():
        if with_comma := [tag for tag in [*actions.add_tags, *actions.remove_tags] if "," in tag]:
            raise RequestParameterInvalidException(f"Tags can't contain a comma: {', '.join(with_comma)}.")
    post_job_actions = []
    for output_name, actions in output_actions.items():
        for field, action_type in ACTION_TYPE_BY_FIELD.items():
            if value := getattr(actions, field):
                post_job_actions.append(
                    PostJobAction(action_type, output_name=output_name, action_arguments=_arguments(field, value))
                )
    return post_job_actions


# The field of ToolOutputActions each post job action type stands for
ACTION_TYPE_BY_FIELD = {
    "rename": "RenameDatasetAction",
    "add_tags": "TagDatasetAction",
    "remove_tags": "RemoveTagDatasetAction",
    "hide": "HideDatasetAction",
}
FIELD_BY_ACTION_TYPE = {action_type: field for field, action_type in ACTION_TYPE_BY_FIELD.items()}


def _arguments(field: str, value: Any) -> dict[str, str]:
    if field == "rename":
        return {"newname": value}
    if field == "hide":
        return {}
    # Tag actions keep their tags as one comma separated string.
    return {"tags": ",".join(value)}


def _value(field: str, arguments: dict[str, Any]) -> Any:
    if field == "rename":
        return arguments.get("newname")
    if field == "hide":
        return True
    return _split_tags(arguments.get("tags", ""))


def is_requested_output_change(pja: PostJobAction) -> bool:
    """Whether ``pja`` is a rename, tag or hide asked for a tool run, not one copied from a workflow step."""
    return pja.action_type in FIELD_BY_ACTION_TYPE and pja.workflow_step is None


def job_belongs_to_workflow(job: Job) -> bool:
    """Whether ``job`` was created by a workflow invocation, including a mapped-over step.

    All post job actions of such a job belong to the workflow, also the runtime ones that have no
    workflow step; a tool run attaches the changes asked for it.
    """
    return job.effective_workflow_invocation_step is not None


def output_actions_of_job(job: Job) -> dict[str, ToolOutputActions]:
    """Return the output changes a tool run asked for, from the post job actions of one of its jobs.

    Jobs of workflow invocations have none; their actions belong to the workflow, not to the run.
    """
    if job_belongs_to_workflow(job):
        return {}
    fields: dict[str, dict[str, Any]] = defaultdict(dict)
    for pjaa in job.post_job_actions:
        pja = pjaa.post_job_action
        if not pja.output_name or not is_requested_output_change(pja):
            continue
        field = FIELD_BY_ACTION_TYPE[pja.action_type]
        fields[pja.output_name][field] = _value(field, pja.action_arguments or {})
    return {output_name: ToolOutputActions(**output_fields) for output_name, output_fields in fields.items()}


def _split_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]
