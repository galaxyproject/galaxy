from abc import (
    ABCMeta,
    abstractmethod,
)
from uuid import UUID

from celery.result import AsyncResult


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
    def get_state(self, task_uuid: UUID) -> str:
        """Returns the current state of the task as a string."""


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

    def get_state(self, task_uuid: UUID) -> str:
        """Returns the tasks current state as a string."""
        return str(self._get_result(task_uuid).state)

    def _get_result(self, task_uuid: UUID) -> AsyncResult:
        return AsyncResult(str(task_uuid))
