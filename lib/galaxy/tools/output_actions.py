"""Turn the output changes requested for a tool run into post job actions."""

from collections.abc import Mapping
from typing import TYPE_CHECKING

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model import PostJobAction
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


def _action(action_type: str, output_name: str, action_arguments: dict[str, str]) -> PostJobAction:
    return PostJobAction(action_type, output_name=output_name, action_arguments=action_arguments)
