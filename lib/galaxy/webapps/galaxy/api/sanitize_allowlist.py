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
        return {'status': 'done', 'message': 'Tool allow list loaded.', 'data': self._generate_allowlist(trans)}

    @web.require_admin
    @web.legacy_expose_api
    def create(self, trans, tool_id, **kwd):
        """
        PUT /api/sanitize_allowlist
        Add a new tool specification to the allow list.
        """
        if tool_id not in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.append(tool_id)
            self._save_allowlist(trans)
        return {'status': 'done', 'message': '%s added to allowlist.' % tool_id, 'data': self._generate_allowlist(trans)}

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
        return {'status': 'done', 'message': '%s removed from allowlist.' % tool_id, 'data': self._generate_allowlist(trans)}

    def _save_allowlist(self, trans):
        new_allowlist = sorted([tid for tid in trans.app.config.sanitize_allowlist])
        trans.app.config.sanitize_allowlist = new_allowlist
        with open(trans.app.config.sanitize_allowlist_file, 'wt') as f:
            f.write("\n".join(new_allowlist))

    def _generate_allowlist(self, trans):
        allow_list = []
        sanitize_list = []
        ids = None
        for tool_id in trans.app.config.sanitize_allowlist:
            for toolbox_id in trans.app.toolbox.tools_by_id:
                tool = trans.app.toolbox.tools_by_id[toolbox_id]
                if toolbox_id.startswith(tool_id):
                    tool_name = tool.name
                    full_id = tool.id
                    ids = {'full': full_id,
                           'allowed': tool_id,
                           'owner': '/'.join(full_id.split('/')[:3]),
                           'repository': '/'.join(full_id.split('/')[:4]),
                           'tool': '/'.join(full_id.split('/')[:5])}
                    break
            tool_dict = dict(tool_name=tool.name, tool_id=tool_id.split('/'), ids=ids, allowed=True, toolshed='/' in tool_id)
            allow_list.append(tool_dict)
        for tool_id in sorted(trans.app.toolbox.tools_by_id):
            tool = trans.app.toolbox.tools_by_id[tool_id]
            if not tool_id.startswith(tuple(trans.app.config.sanitize_allowlist)):
                ids = {'full': tool_id, 
                       'owner': '/'.join(tool_id.split('/')[:3]),
                       'repository': '/'.join(tool_id.split('/')[:4]),
                       'tool': '/'.join(tool_id.split('/')[:5])}
                tool_status = dict(tool_name=tool.name, tool_id=tool_id.split('/'), ids=ids, allowed=False, toolshed='/' in tool_id)
                sanitize_list.append(tool_status)
        return {'sanitize': sanitize_list, 'allow': allow_list}
    
