"""
API operations allowing clients to retrieve and modify the HTML sanitization allow list.
"""

import logging
from typing import (
    Any,
    Dict,
)

from galaxy import web
from galaxy.webapps.base.controller import BaseAPIController

log = logging.getLogger(__name__)


class SanitizeAllowController(BaseAPIController):
    @web.require_admin
    @web.expose_api
    def index(self, trans, **kwd):
        """
        GET /api/sanitize_allow
        Return an object showing the current state of the toolbox and allow list.
        """
        return self._generate_allowlist(trans)

    @web.require_admin
    @web.expose_api
    def create(self, trans, tool_id, **kwd):
        """
        PUT /api/sanitize_allow
        Add a new tool_id to the allowlist.
        """
        if tool_id not in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.append(tool_id)
            self._save_allowlist(trans)
        return self._generate_allowlist(trans)

    @web.require_admin
    @web.expose_api
    def delete(self, trans, tool_id, **kwd):
        """
        DELETE /api/sanitize_allow
        Remove tool_id from allowlist.
        """
        if tool_id in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.remove(tool_id)
            self._save_allowlist(trans)
        return self._generate_allowlist(trans)

    def _save_allowlist(self, trans):
        trans.app.config.sanitize_allowlist = sorted(trans.app.config.sanitize_allowlist)
        with open(trans.app.config.sanitize_allowlist_file, "w") as f:
            f.write("\n".join(trans.app.config.sanitize_allowlist))
        trans.app.queue_worker.send_control_task("reload_sanitize_allowlist", noop_self=True)

    def _generate_allowlist(self, trans):
        sanitize_dict: Dict[str, Any] = dict(
            blocked_toolshed=[], allowed_toolshed=[], blocked_local=[], allowed_local=[]
        )
        ids = None
        for tool_id in trans.app.config.sanitize_allowlist:
            installed_name = ""
            installed_ids = {"full": "", "allowed": tool_id, "owner": "", "repository": "", "tool": ""}
            for toolbox_id in trans.app.toolbox.tools_by_id:
                if toolbox_id.startswith(tool_id):
                    tool = trans.app.toolbox.tools_by_id[toolbox_id]
                    installed_name = tool.name
                    full_id = tool.id
                    installed_ids = {
                        "full": full_id,
                        "allowed": tool_id,
                        "owner": "/".join(full_id.split("/")[:3]),
                        "repository": "/".join(full_id.split("/")[:4]),
                        "tool": "/".join(full_id.split("/")[:5]),
                    }
                    break
            tool_dict = dict(
                tool_name=installed_name,
                tool_id=tool_id.split("/"),
                ids=installed_ids,
                allowed=True,
                toolshed="/" in tool_id,
            )
            if "/" in tool_id:
                sanitize_dict["allowed_toolshed"].append(tool_dict)
            else:
                sanitize_dict["allowed_local"].append(tool_dict)
        for tool_id in sorted(trans.app.toolbox.tools_by_id):
            if not tool_id.startswith(tuple(trans.app.config.sanitize_allowlist)):
                tool = trans.app.toolbox.tools_by_id[tool_id]
                ids = {
                    "full": tool_id,
                    "owner": "/".join(tool_id.split("/")[:3]),
                    "repository": "/".join(tool_id.split("/")[:4]),
                    "tool": "/".join(tool_id.split("/")[:5]),
                }
                tool_dict = dict(
                    tool_name=tool.name, tool_id=tool_id.split("/"), ids=ids, allowed=False, toolshed="/" in tool_id
                )
                if "/" in tool_id:
                    sanitize_dict["blocked_toolshed"].append(tool_dict)
                else:
                    sanitize_dict["blocked_local"].append(tool_dict)
        return sanitize_dict
