from celery.result import AsyncResult

from galaxy.schema.schema import AsyncTaskResultSummary


def async_task_summary(async_result: AsyncResult) -> AsyncTaskResultSummary:
    name = None
    try:
        name = async_result.name
    except AttributeError:
        # if backend is disabled, we won't have this
        pass
    queue = None
    try:
        queue = async_result.queue
    except AttributeError:
        # if backend is disabled, we won't have this
        pass

    return AsyncTaskResultSummary(
        id=str(async_result.id),
        ignored=async_result.ignored,
        name=name,
        queue=queue,
    )
