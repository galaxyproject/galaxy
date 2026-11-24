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

    Raises ``RequestParameterInvalidException`` for names that aren't outputs of the tool and for
    tags with a comma.
    """
    if unknown := sorted(set(output_actions) - set(tool.outputs)):
        raise RequestParameterInvalidException(f"Tool '{tool.id}' has no output named {', '.join(unknown)}.")
    for actions in output_actions.values():
        # Tag actions keep their tags as one comma separated string.
        if with_comma := [tag for tag in [*actions.add_tags, *actions.remove_tags] if "," in tag]:
            raise RequestParameterInvalidException(f"Tags can't contain a comma: {', '.join(with_comma)}.")
    post_job_actions = []
    for output_name, actions in output_actions.items():
        if actions.rename:
            post_job_actions.append(_action("RenameDatasetAction", output_name, {"newname": actions.rename}))
        if actions.add_tags:
            post_job_actions.append(_action("TagDatasetAction", output_name, {"tags": ",".join(actions.add_tags)}))
        if actions.remove_tags:
            post_job_actions.append(
                _action("RemoveTagDatasetAction", output_name, {"tags": ",".join(actions.remove_tags)})
            )
        if actions.hide:
            post_job_actions.append(_action("HideDatasetAction", output_name, {}))
    return post_job_actions


OUTPUT_ACTION_TYPES = frozenset(
    ["RenameDatasetAction", "TagDatasetAction", "RemoveTagDatasetAction", "HideDatasetAction"]
)


def _action(action_type: str, output_name: str, action_arguments: dict[str, str]) -> PostJobAction:
    return PostJobAction(action_type, output_name=output_name, action_arguments=action_arguments)


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
        if not pja.output_name:
            continue
        arguments = pja.action_arguments or {}
        if pja.action_type == "RenameDatasetAction":
            fields[pja.output_name]["rename"] = arguments.get("newname")
        elif pja.action_type == "TagDatasetAction":
            fields[pja.output_name]["add_tags"] = _split_tags(arguments.get("tags", ""))
        elif pja.action_type == "RemoveTagDatasetAction":
            fields[pja.output_name]["remove_tags"] = _split_tags(arguments.get("tags", ""))
        elif pja.action_type == "HideDatasetAction":
            fields[pja.output_name]["hide"] = True
    return {output_name: ToolOutputActions(**output_fields) for output_name, output_fields in fields.items()}


def _split_tags(tags: str) -> list[str]:
    return [tag.strip() for tag in tags.split(",") if tag.strip()]
