"""
API Controller providing experimental access to Celery Task State.
"""
import logging

from celery.result import AsyncResult

from . import Router

log = logging.getLogger(__name__)

router = Router(tags=["tasks"])


@router.cbv
class FastAPITasks:
    @router.get(
        "/api/tasks/{task_id}/state",
        summary="Determine state of task ID",
        response_description="String indicating task state.",
    )
    def state(self, task_id: str) -> str:
        res = AsyncResult(str(task_id))
        return str(res.state)
