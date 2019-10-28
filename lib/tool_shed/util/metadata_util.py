import logging

from galaxy import util
from tool_shed.util import common_util

log = logging.getLogger(__name__)


def get_updated_changeset_revisions_from_tool_shed(app, tool_shed_url, name, owner, changeset_revision):
    """
    Get all appropriate newer changeset revisions for the repository defined by
    the received tool_shed_url / name / owner combination.
    """
    tool_shed_url = common_util.get_tool_shed_url_from_tool_shed_registry(app, tool_shed_url)
    if tool_shed_url is None or name is None or owner is None or changeset_revision is None:
        message = "Unable to get updated changeset revisions from the Tool Shed because one or more of the following "
        message += "required parameters is None: tool_shed_url: %s, name: %s, owner: %s, changeset_revision: %s " % \
            (str(tool_shed_url), str(name), str(owner), str(changeset_revision))
        raise Exception(message)
    params = dict(name=name, owner=owner, changeset_revision=changeset_revision)
    pathspec = ['repository', 'updated_changeset_revisions']
    text = util.url_get(tool_shed_url, password_mgr=app.tool_shed_registry.url_auth(tool_shed_url), pathspec=pathspec, params=params)
    return text
