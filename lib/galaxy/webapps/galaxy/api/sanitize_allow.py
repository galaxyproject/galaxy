"""
API operations allowing clients to retrieve and modify the HTML sanitization allow list.
"""

import logging
from typing import Any, Dict, List

from fastapi import Query

from galaxy.managers.context import ProvidesUserContext
from galaxy.webapps.galaxy.api import DependsOnTrans
from . import Router

log = logging.getLogger(__name__)

router = Router(tags=["configuration"])

ToolIDQueryParam: str = Query(
    title="tool_id only",
    description="ID string of tool to add or delete",
)


class ToolDict(Dict):
    tool_name: str
    tool_id: List[str]
    ids: List[str]
    allowed: bool
    toolshed: bool


class ToolListResponse(Dict):
    blocked_toolshed: List[ToolDict]
    allowed_toolshed: List[ToolDict]
    blocked_local: List[ToolDict]
    allowed_local: List[ToolDict]


@router.cbv
class FastAPISanitizeAllowController:
    @router.get("/api/sanitize_allow", require_admin=True, response_model=ToolListResponse)
    def index(self, trans: ProvidesUserContext = DependsOnTrans):
        """
        Return an object showing the current state of the toolbox and allow list.
        """
        return self._generate_allowlist(trans)

    @router.put("/api/sanitize_allow", require_admin=True, response_model=ToolListResponse)
    def create(self, tool_id: str = ToolIDQueryParam, trans: ProvidesUserContext = DependsOnTrans):
        """
        Add a new tool_id to the allowlist.
        """
        if tool_id not in trans.app.config.sanitize_allowlist:
            trans.app.config.sanitize_allowlist.append(tool_id)
            self._save_allowlist(trans)
        return self._generate_allowlist(trans)

    @router.delete("/api/sanitize_allow", require_admin=True, response_model=ToolListResponse)
    def delete(self, tool_id: str = ToolIDQueryParam, trans: ProvidesUserContext = DependsOnTrans):
        """
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
