from galaxy.managers.workflows import (
    WorkflowSerializer,
    WorkflowsManager,
)
from galaxy.webapps.galaxy.services.base import ServiceBase
from galaxy.webapps.galaxy.services.sharable import ShareableService


class WorkflowsService(ServiceBase):
    def __init__(
        self,
        workflows_manager: WorkflowsManager,
        serializer: WorkflowSerializer,
    ):
        self._workflows_manager = workflows_manager
        self._serializer = serializer
        self.shareable_service = ShareableService(workflows_manager, serializer)
