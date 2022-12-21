"""
API Controller providing experimental access to Celery Task State.
"""
import logging
from uuid import UUID

from galaxy.managers.tasks import AsyncTasksManager
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["tasks"])


@router.cbv
class FastAPITasks:
    manager: AsyncTasksManager = depends(AsyncTasksManager)  # type: ignore[type-abstract]

    @router.get(
        "/api/tasks/{task_id}/state",
        summary="Determine state of task ID",
        response_description="String indicating task state.",
    )
    def state(self, task_id: UUID) -> str:
        return self.manager.get_state(task_id)
