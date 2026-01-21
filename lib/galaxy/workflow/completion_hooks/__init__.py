"""
Workflow completion hooks system.

This module provides the hook registry and base class for workflow
completion hooks. Hooks are executed asynchronously via Celery when
a workflow invocation completes.

To add a new hook:
1. Create a new module in this package
2. Define a class that extends WorkflowCompletionHook
3. Set a unique `plugin_type` class attribute
4. Export the class via `__all__`

Hooks are automatically discovered via the plugin_type attribute.
"""

import logging
from typing import (
    Optional,
    TYPE_CHECKING,
)

import galaxy.workflow.completion_hooks
from galaxy.structured_app import MinimalManagerApp
from galaxy.util import plugin_config
from galaxy.workflow.completion_hooks.base import WorkflowCompletionHook

if TYPE_CHECKING:
    from galaxy.model import WorkflowInvocationCompletion

log = logging.getLogger(__name__)

# Re-export WorkflowCompletionHook for backwards compatibility
__all__ = ["WorkflowCompletionHook", "WorkflowCompletionHookRegistry"]


class WorkflowCompletionHookRegistry:
    """
    Registry of available workflow completion hooks.

    Manages hook registration, instantiation, and execution.
    All registered hooks are enabled by default.
    """

    # All available hook classes, keyed by name
    hooks: dict[str, type[WorkflowCompletionHook]] = {}

    def __init__(self, app: MinimalManagerApp):
        """
        Initialize the registry.

        Args:
            app: The Galaxy application instance.
        """
        self.app = app
        self._instances: dict[str, WorkflowCompletionHook] = {}
        self._load_hooks()

    def _load_hooks(self) -> None:
        """Load and instantiate all available hooks."""
        # Auto-discover hooks via plugin_type attribute
        self.hooks = plugin_config.plugins_dict(galaxy.workflow.completion_hooks, "plugin_type")

        # Instantiate all hooks
        for hook_name, hook_class in self.hooks.items():
            log.info("Enabling workflow completion hook: %s", hook_name)
            self._instances[hook_name] = hook_class(self.app)

    def get_available_hooks(self) -> list[str]:
        """
        Get list of all available hook names.

        Returns:
            List of all registered hook names.
        """
        return list(self.hooks.keys())

    def get_hook(self, name: str) -> Optional[WorkflowCompletionHook]:
        """
        Get a hook instance by name.

        Instantiates the hook on-demand if not already cached.

        Args:
            name: The name of the hook.

        Returns:
            The hook instance if available, None otherwise.
        """
        # Check if already instantiated
        if name in self._instances:
            return self._instances[name]

        # Try to instantiate on-demand
        if name in self.hooks:
            self._instances[name] = self.hooks[name](self.app)
            return self._instances[name]

        return None

    def execute_hook(self, name: str, completion: "WorkflowInvocationCompletion") -> bool:
        """
        Execute a specific hook.

        Args:
            name: The name of the hook to execute.
            completion: The completion record.

        Returns:
            True if executed successfully (or not applicable),
            False if hook not found or execution failed.
        """
        hook = self.get_hook(name)
        if not hook:
            log.warning("Hook '%s' not found or not enabled", name)
            return False

        if not hook.is_applicable(completion):
            log.debug(
                "Hook '%s' not applicable for invocation %d",
                name,
                completion.workflow_invocation_id,
            )
            return True  # Not an error, just not applicable

        try:
            log.info(
                "Executing hook '%s' for invocation %d",
                name,
                completion.workflow_invocation_id,
            )
            hook.execute(completion)
            return True
        except Exception:
            log.exception(
                "Error executing hook '%s' for invocation %d",
                name,
                completion.workflow_invocation_id,
            )
            return False
