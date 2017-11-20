"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""

import logging

from sqlalchemy.sql.expression import null

from galaxy.jobs import handler, NoopQueue
from galaxy.model import Job
from galaxy.web.stack.message import JobHandlerMessage

log = logging.getLogger(__name__)


class JobManager(object):
    """
    Highest level interface to job management.

    TODO: Currently the app accesses "job_queue" and "job_stop_queue" directly.
          This should be decoupled.
    """

    def __init__(self, app):
        self.app = app
        self.job_lock = False
        if self.app.is_job_handler:
            log.debug("Initializing job handler")
            self.job_handler = handler.JobHandler(app)
            self.job_stop_queue = self.job_handler.job_stop_queue
        elif app.application_stack.has_pool(app.application_stack.pools.JOB_HANDLERS):
            log.debug("Initializing job handler messaging interface")
            self.job_handler = MessageJobHandler(app)
            self.job_stop_queue = NoopQueue()
        else:
            self.job_handler = NoopHandler()
            self.job_stop_queue = NoopQueue()
        self.job_queue = self.job_handler.job_queue

    def start(self):
        self.job_handler.start()

    def shutdown(self):
        self.job_handler.shutdown()


class NoopHandler(object):
    def __init__(self, *args, **kwargs):
        self.job_queue = NoopQueue()
        self.job_stop_queue = NoopQueue()

    def start(self):
        pass

    def shutdown(self, *args):
        pass


class MessageJobHandler(NoopHandler):
    """
    Implements the JobHandler interface but just to send setup messages on startup

    TODO: It should be documented that starting two Galaxy uWSGI master processes simultaneously would result in a race condition that *could* cause two handlers to pick up the same job.

    The recommended config for now will be webless handlers if running more than one uWSGI (master) process
    """
    def __init__(self, app):
        # This runs in the web (main) process pre-fork
        self.app = app
        self.job_queue = MessageJobQueue(app)
        self.job_stop_queue = NoopQueue()
        jobs_at_startup = self.app.model.context.query(Job).enable_eagerloads(False) \
            .filter((Job.state == Job.states.NEW) & (Job.handler == null())).all()
        if jobs_at_startup:
            log.info('No handler assigned at startup for the following jobs, will dispatch via message: %s', ', '.join([str(j.id) for j in jobs_at_startup]))
        for job in jobs_at_startup:
            self.job_queue.put(job.id, job.tool_id)


class MessageJobQueue(NoopQueue):
    """
    Implements the JobQueue / JobStopQueue interface but only sends messages to the actual job queue
    """
    def __init__(self, app):
        self.app = app

    def put(self, job_id, tool_id):
        msg = JobHandlerMessage(task='setup', job_id=job_id)
        self.app.application_stack.send_message(self.app.application_stack.pools.JOB_HANDLERS, msg)
