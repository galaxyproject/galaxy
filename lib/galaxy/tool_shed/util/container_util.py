import logging
from typing import Union

from galaxy.util.tool_shed.common_util import remove_protocol_from_tool_shed_url

log = logging.getLogger(__name__)

# String separator
STRSEP = "__ESEP__"


def generate_repository_dependencies_key_for_repository(
    toolshed_base_url: str,
    repository_name: str,
    repository_owner: str,
    changeset_revision: str,
    prior_installation_required: Union[bool, str],
    only_if_compiling_contained_td: Union[bool, str],
) -> str:
    """
    Assumes tool shed is current tool shed since repository dependencies across tool sheds
    is not yet supported.
    """
    # The tool_shed portion of the key must be the value that is stored in the tool_shed_repository.tool_shed column
    # of the Galaxy database for an installed repository.  This value does not include the protocol, but does include
    # the port if there is one.
    tool_shed = remove_protocol_from_tool_shed_url(toolshed_base_url)
    return "{}{}{}{}{}{}{}{}{}{}{}".format(
        tool_shed,
        STRSEP,
        repository_name,
        STRSEP,
        repository_owner,
        STRSEP,
        changeset_revision,
        STRSEP,
        str(prior_installation_required),
        STRSEP,
        str(only_if_compiling_contained_td),
    )


def get_components_from_key(key: str) -> tuple:
    """
    Assumes tool shed is current tool shed since repository dependencies across tool sheds is not
    yet supported.
    """
    items = key.split(STRSEP)
    toolshed_base_url = items[0]
    repository_name = items[1]
    repository_owner = items[2]
    changeset_revision = items[3]
    if len(items) == 5:
        prior_installation_required = items[4]
        return toolshed_base_url, repository_name, repository_owner, changeset_revision, prior_installation_required
    elif len(items) == 6:
        prior_installation_required = items[4]
        only_if_compiling_contained_td = items[5]
        return (
            toolshed_base_url,
            repository_name,
            repository_owner,
            changeset_revision,
            prior_installation_required,
            only_if_compiling_contained_td,
        )
    else:
        # For backward compatibility to the 12/20/12 Galaxy release we have to return the following, and callers
        # must handle exceptions.
        return toolshed_base_url, repository_name, repository_owner, changeset_revision
