""" The class defines the stock Galaxy workflow scheduling plugin - currently
it simply schedules the whole workflow up front when offered.
"""
import logging

from galaxy.work import context
from galaxy.workflow import run, run_request
from ..schedulers import ActiveWorkflowSchedulingPlugin

log = logging.getLogger(__name__)


class CoreWorkflowSchedulingPlugin(ActiveWorkflowSchedulingPlugin):
    plugin_type = "core"

    def __init__(self, **kwds):
        pass

    def startup(self, app):
        self.app = app

    def shutdown(self):
        pass

    def schedule(self, workflow_invocation):
        workflow = workflow_invocation.workflow
        history = workflow_invocation.history
        request_context = context.WorkRequestContext(
            app=self.app,
            history=history,
            user=history.user
        )  # trans-like object not tied to a web-thread.
        workflow_run_config = run_request.workflow_request_to_run_config(
            request_context,
            workflow_invocation
        )
        run.schedule(
            trans=request_context,
            workflow=workflow,
            workflow_run_config=workflow_run_config,
            workflow_invocation=workflow_invocation,
        )


__all__ = ('CoreWorkflowSchedulingPlugin', )
