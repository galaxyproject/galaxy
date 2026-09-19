"""
API Controller providing experimental access to Celery Task State.
"""

import logging
from uuid import UUID

from galaxy.managers.tasks import AsyncTasksManager
from galaxy.schema.tasks import (
    TaskResult,
    TaskState,
)
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
        public=True,
        summary="Determine state of task ID",
        response_description="String indicating task state.",
    )
    def state(self, task_id: UUID) -> TaskState:
        return self.manager.get_state(task_id)

    @router.get(
        "/api/tasks/{task_id}/result",
        public=True,
        summary="Get result message for task ID",
    )
    def get_result(self, task_id: UUID) -> TaskResult:
        """
        If the task is still running, pending, or is waiting for retry then the result is an empty string.
        If the task failed, the result is an error message.
        """
        return self.manager.get_result(task_id)
