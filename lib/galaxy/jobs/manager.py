"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""
import logging
from functools import partial

from sqlalchemy.sql.expression import null

from galaxy.exceptions import HandlerAssignmentError, ToolExecutionError
from galaxy.jobs import handler, NoopQueue
from galaxy.model import Job
from galaxy.web.stack.message import JobHandlerMessage

log = logging.getLogger(__name__)


class JobManager(object):
    """
    Highest level interface to job management.
    """
    def __init__(self, app):
        self.app = app
        self.job_lock = False
        if self.app.is_job_handler:
            log.debug("Initializing job handler")
            self.job_handler = handler.JobHandler(app)
        else:
            self.job_handler = NoopHandler()
            self.__check_jobs_at_startup()

    def __check_jobs_at_startup(self):
        if self.app.job_config.use_messaging:
            jobs_at_startup = self.app.model.context.query(Job).enable_eagerloads(False) \
                .filter((Job.state == Job.states.NEW) & (Job.handler == null())).all()
            if jobs_at_startup:
                log.info(
                    'No handler assigned at startup for the following jobs, will dispatch via message: %s',
                    ', '.join([str(j.id) for j in jobs_at_startup]))
            for job in jobs_at_startup:
                tool = self.app.toolbox.get_tool(job.tool_id, job.tool_version, exact=True)
                self.enqueue(job, tool)

    def start(self):
        self.job_handler.start()

    def _queue_callback(self, job, tool_id):
        self.job_handler.job_queue.put(job.id, tool_id)

    def _message_callback(self, job):
        return JobHandlerMessage(task='setup', job_id=job.id)

    def enqueue(self, job, tool=None):
        """Queue a job for execution.

        Due to the nature of some handler assignment methods which are wholly DB-based, the enqueue method will flush
        the job. Callers who create the job typically should not flush the job before handing it off to ``enqueue()``.
        If a job handler cannot be assigned, :exception:`ToolExecutionError` is raised.

        :param job:     Job to enqueue.
        :type job:      Instance of :class:`galaxy.model.Job`.
        :param tool:    Tool that the job will execute.
        :type tool:     Instance of :class:`galaxy.tools.Tool`.

        :raises ToolExecutionError: if a handler was unable to be assigned.
        returns: str or None -- Handler ID, tag, or pool assigned to the job.
        """
        tool_id = None
        configured_handler = None
        if tool:
            tool_id = tool.id
            configured_handler = tool.get_configured_job_handler(job.params)
            if configured_handler is not None:
                p = " (with job params: %s)" % str(job.params) if job.params else ""
                log.debug("(%s) Configured job handler for tool '%s'%s is: %s", job.log_str(), tool_id, p, configured_handler)
        queue_callback = partial(self._queue_callback, job, tool_id)
        message_callback = partial(self._message_callback, job)
        try:
            return self.app.job_config.assign_handler(
                job, configured=configured_handler, queue_callback=queue_callback, message_callback=message_callback)
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


class NoopManager(object):
    """
    Implements the JobManager interface but does nothing
    """
    def __init__(self, *args, **kwargs):
        self.job_handler = NoopHandler()

    def enqueue(self, *args, **kwargs):
        pass

    def stop(self, *args, **kwargs):
        pass


class NoopHandler(object):
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
