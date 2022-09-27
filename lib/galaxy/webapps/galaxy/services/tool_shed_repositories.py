from typing import Optional

from galaxy.model.scoped_session import install_model_scoped_session
from galaxy.schema.schema import CheckForUpdatesResponse
from galaxy.tool_shed.util.repository_util import check_for_updates
from galaxy.util.tool_shed.tool_shed_registry import Registry


class ToolShedRepositoriesService:
    def __init__(
        self,
        install_model_context: install_model_scoped_session,
        tool_shed_registry: Registry,
    ):
        self._install_model_context = install_model_context
        self._tool_shed_registry = tool_shed_registry

    def check_for_updates(self, repository_id: Optional[int]) -> CheckForUpdatesResponse:
        message, status = check_for_updates(self._tool_shed_registry, self._install_model_context, repository_id)
        return CheckForUpdatesResponse(message=message, status=status)
