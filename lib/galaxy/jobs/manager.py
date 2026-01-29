"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""

import logging
from functools import partial

from galaxy.exceptions import (
    HandlerAssignmentError,
    ToolExecutionError,
)
from galaxy.jobs import (
    handler,
    NoopQueue,
)
from galaxy.structured_app import MinimalManagerApp
from galaxy.web_stack.message import JobHandlerMessage

log = logging.getLogger(__name__)


class JobManager:
    """
    Highest level interface to job management.
    """

    job_handler: handler.JobHandlerI

    def __init__(self, app: MinimalManagerApp):
        self.app = app
        self.job_lock = False
        self.job_handler = NoopHandler()

    def _check_jobs_at_startup(self):
        if not self.app.is_job_handler:
            self.__check_jobs_at_startup()

    def start(self):
        if self.app.is_job_handler:
            log.debug("Initializing job handler")
            self.job_handler = handler.JobHandler(self.app)
            self.job_handler.start()

    def _queue_callback(self, job, tool_id):
        self.job_handler.job_queue.put(job.id, tool_id)

    def _message_callback(self, job):
        return JobHandlerMessage(task="setup", job_id=job.id)

    def enqueue(self, job, tool=None, flush=True):
        """Queue a job for execution.

        Due to the nature of some handler assignment methods which are wholly DB-based, the enqueue method will flush
        the job. Callers who create the job typically should not flush the job before handing it off to ``enqueue()``.
        If a job handler cannot be assigned, py:class:`ToolExecutionError` is raised.

        :param job:     Job to enqueue.
        :type job:      Instance of :class:`galaxy.model.Job`.
        :param tool:    Tool that the job will execute.
        :type tool:     Instance of :class:`galaxy.tools.Tool`.

        :raises ToolExecutionError: if a handler was unable to be assigned.
        :returns: str or None -- Handler ID, tag, or pool assigned to the job.
        """
        tool_id = None
        configured_handler = None
        if tool:
            tool_id = tool.id
            configured_handler = tool.get_configured_job_handler(job.params)
            if configured_handler is not None:
                p = f" (with job params: {str(job.params)})" if job.params else ""
                log.debug(
                    "(%s) Configured job handler for tool '%s'%s is: %s", job.log_str(), tool_id, p, configured_handler
                )
        queue_callback = partial(self._queue_callback, job, tool_id)
        message_callback = partial(self._message_callback, job)
        try:
            return self.app.job_config.assign_handler(
                job,
                configured=configured_handler,
                queue_callback=queue_callback,
                message_callback=message_callback,
                flush=flush,
            )
        except HandlerAssignmentError as exc:
            raise ToolExecutionError(exc.args[0], job=exc.obj)

    def stop(self, job, message=None):
        """Stop a job that is currently executing.

        This can be safely called on jobs that have already terminated.

        :param job:     Job to stop.
        :type job:      Instance of :class:`galaxy.model.Job`.
        :param message: Message (if any) to be set on the job and output dataset(s) to explain the reason for stopping.
        :type message:  str
        """
        self.job_handler.job_stop_queue.put(job.id, error_msg=message)

    def shutdown(self):
        self.job_handler.shutdown()


class NoopManager:
    """
    Implements the JobManager interface but does nothing
    """

    def __init__(self, *args, **kwargs):
        self.job_handler = NoopHandler()

    def enqueue(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass


class NoopHandler(handler.JobHandlerI):
    """
    Implements the JobHandler interface but does nothing
    """

    def __init__(self, *args, **kwargs):
        self.job_queue = NoopQueue()
        self.job_stop_queue = NoopQueue()

    def start(self):
        pass

    def shutdown(self, *args):
        pass
