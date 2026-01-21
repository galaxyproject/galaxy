"""
Base class for workflow completion hooks.

This module provides the abstract base class for workflow completion hooks.
Separate from __init__.py to avoid circular import issues.
"""

from abc import (
    ABC,
    abstractmethod,
)
from typing import TYPE_CHECKING

from galaxy.structured_app import MinimalManagerApp

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocationCompletion


class WorkflowCompletionHook(ABC):
    """
    Base class for workflow completion hooks.

    Hooks are executed asynchronously via Celery tasks when a workflow
    invocation completes (all jobs reach terminal states).

    To implement a hook:
    1. Extend this class
    2. Set a unique `plugin_type` attribute
    3. Implement the `execute()` method
    4. Optionally override `is_applicable()` to add conditions

    Hooks should be idempotent - they may be called multiple times
    for the same completion (e.g., after a Celery task retry).
    """

    # Plugin type identifier for automatic discovery - must be set by subclasses
    plugin_type: str

    def __init__(self, app: MinimalManagerApp):
        """
        Initialize the hook.

        Args:
            app: The Galaxy application instance.
        """
        self.app = app

    @abstractmethod
    def execute(self, completion: "WorkflowInvocationCompletion") -> None:
        """
        Execute the hook for a completed workflow invocation.

        This runs inside a Celery task, so it can perform long-running
        operations without blocking the main application.

        Should be idempotent - may be called multiple times for the
        same completion.

        Args:
            completion: The completion record with invocation details.
        """
        pass

    def is_applicable(self, completion: "WorkflowInvocationCompletion") -> bool:
        """
        Check if this hook should run for the given completion.

        Override to add conditions (e.g., only run on success,
        only run if certain parameters are present).

        Args:
            completion: The completion record to check.

        Returns:
            True if the hook should execute, False otherwise.
        """
        return True
