"""
API operations allowing clients to retrieve and modify the HTML sanitization allow list.
"""
import logging

from galaxy.datatypes.data import Data
from galaxy.util import asbool
from galaxy import web
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class SanitizeAllowlistController(BaseAPIController):

    @web.require_admin
    @web.legacy_expose_api
    def index(self, trans, **kwd):
        """
        GET /api/sanitize_allowlist
        Return an object showing the current state of the toolbox and allow list.
        """
        allowlist = []
        tool_name = None
        for tool_id in trans.app.config.sanitize_allowlist:
            for toolbox_id in trans.app.toolbox.tools_by_id:
                tool = trans.app.toolbox.tools_by_id[toolbox_id]
                if toolbox_id.startswith(tool_id):
                    tool_name = tool.name
                    break
            tool_dict = dict(tool_name=tool.name, tool_id=tool_id.split('/'), allowed=True, toolshed='/' in tool_id)
            allowlist.append(tool_dict)
        for tool_id in sorted(trans.app.toolbox.tools_by_id):
            tool = trans.app.toolbox.tools_by_id[tool_id]
            if not tool_id.startswith(tuple(trans.app.config.sanitize_allowlist)):
                tool_status = dict(tool_name=tool.name, tool_id=tool_id.split('/'), allowed=False, toolshed='/' in tool_id)
                allowlist.append(tool_status)
        return {'status': 'done', 'message': 'Tool allow list loaded.', 'data': allowlist}

    @web.require_admin
    @web.legacy_expose_api
    def create(self, trans, tool_id, **kwd):
        """
        POST /api/sanitize_allowlist
        Add a new tool specification to the allow list.
        """
        if tool_id not in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.append(tool_id)
            self._save_allowlist(trans)

    @web.require_admin
    @web.legacy_expose_api
    def delete(self, trans, tool_id, **kwd):
        """
        DELETE /api/sanitize_allowlist
        Add a new tool specification to the allow list.
        """
        if tool_id in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.remove(tool_id)
            self._save_allowlist(trans)

    def _save_allowlist(self, trans):
        new_allowlist = sorted([tid for tid in trans.app.config.sanitize_allowlist])
        trans.app.config.sanitize_allowlist = new_allowlist
        with open(trans.app.config.sanitize_allowlist_file, 'wt') as f:
            f.write("\n".join(new_allowlist))
