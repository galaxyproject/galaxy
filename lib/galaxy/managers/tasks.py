from abc import (
    ABCMeta,
    abstractmethod,
)
from enum import Enum
from uuid import UUID

from celery.result import AsyncResult
from pydantic import BaseModel


class TaskState(str, Enum):
    """Enum representing the possible states of a task."""

    PENDING = "PENDING"
    """The task is waiting for execution."""

    STARTED = "STARTED"
    """The task has been started."""

    RETRY = "RETRY"
    """The task is to be retried, possibly because of failure."""

    FAILURE = "FAILURE"
    """The task raised an exception, or has exceeded the retry limit."""

    SUCCESS = "SUCCESS"
    """The task executed successfully."""


class TaskResult(BaseModel):
    state: TaskState
    result: str


class AsyncTasksManager(metaclass=ABCMeta):
    @abstractmethod
    def is_ready(self, task_uuid: UUID) -> bool:
        """Return `True` if the task has executed.

        If the task is still running, pending, or is waiting for retry then `False` is returned.
        """

    def is_pending(self, task_uuid: UUID) -> bool:
        """Return `True` if the task is not done yet."""
        return not self.is_ready(task_uuid)

    @abstractmethod
    def is_successful(self, task_uuid: UUID) -> bool:
        """Return `True` if the task executed successfully."""

    @abstractmethod
    def has_failed(self, task_uuid: UUID) -> bool:
        """Return `True` if the task failed."""

    @abstractmethod
    def get_state(self, task_uuid: UUID) -> TaskState:
        """Returns the current state of the task as a string."""

    @abstractmethod
    def get_result(self, task_uuid: UUID) -> TaskResult:
        """Returns the final state and result message of the task."""


class CeleryAsyncTasksManager(AsyncTasksManager):
    """Thin wrapper around Celery tasks AsyncResult queries."""

    def is_ready(self, task_uuid: UUID) -> bool:
        """Return `True` if the task has executed.

        If the task is still running, pending, or is waiting for retry then `False` is returned.
        """
        return self._get_result(task_uuid).ready()

    def is_successful(self, task_uuid: UUID) -> bool:
        """Return `True` if the task executed successfully."""
        return self._get_result(task_uuid).successful()

    def has_failed(self, task_uuid: UUID) -> bool:
        """Return `True` if the task failed."""
        return self._get_result(task_uuid).failed()

    def get_state(self, task_uuid: UUID) -> TaskState:
        """Returns the tasks current state as a string."""
        result = self._get_result(task_uuid)
        state = TaskState(result.state)
        return state

    def get_result(self, task_uuid: UUID) -> TaskResult:
        async_result = self._get_result(task_uuid)
        result = TaskResult(state=TaskState(async_result.state), result=str(async_result.result or ""))
        return result

    def _get_result(self, task_uuid: UUID) -> AsyncResult:
        return AsyncResult(str(task_uuid))
