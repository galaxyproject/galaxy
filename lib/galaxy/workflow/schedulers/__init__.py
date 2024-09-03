""" Module containing Galaxy workflow scheduling plugins. Galaxy's interface
for workflow scheduling is highly experimental and the interface required for
scheduling plugins will almost certainly change.
"""

from abc import (
    ABCMeta,
    abstractmethod,
)


class WorkflowSchedulingPlugin(metaclass=ABCMeta):
    """A plugin defining how Galaxy should schedule plugins. By default
    plugins are passive and should monitor Galaxy's work queue for
    WorkflowRequests. Inherit from ActiveWorkflowSchedulingPlugin instead if
    the scheduling plugin should be forced (i.e. if scheduling happen all at
    once or the request will be stored and monitored outside of Galaxy.)
    """

    @property
    @abstractmethod
    def plugin_type(self):
        """Short string providing labelling this plugin"""

    @abstractmethod
    def startup(self, app):
        """Called when Galaxy starts up if the plugin is enabled."""

    @abstractmethod
    def shutdown(self):
        """Called when Galaxy is shutting down, workflow scheduling should
        end.
        """


class ActiveWorkflowSchedulingPlugin(WorkflowSchedulingPlugin, metaclass=ABCMeta):
    @abstractmethod
    def schedule(self, workflow_invocation):
        """Optionally return one or more commands to instrument job. These
        commands will be executed on the compute server prior to the job
        running.
        """
