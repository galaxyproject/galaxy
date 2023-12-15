"""
API Controller providing experimental access to Celery Task State.
"""
import logging
from uuid import UUID

from galaxy.managers.tasks import (
    AsyncTasksManager,
    TaskState,
)
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["tasks"])


class FastAPITasks:
    @router.get(
        "/api/tasks/{task_id}/state",
        summary="Determine state of task ID",
        response_description="String indicating task state.",
    )
    def state(task_id: UUID, manager: AsyncTasksManager = depends(AsyncTasksManager)) -> TaskState:  # type: ignore[type-abstract]
        return manager.get_state(task_id)
