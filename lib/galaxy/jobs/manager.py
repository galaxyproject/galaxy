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
        self.job_handler = NoopHandler()
        self.job_stop_queue = NoopQueue()
        if app.application_stack.setup_jobs_with_msg:
            # defer setup to postfork
            log.debug('######### registering manager init function')
            self.app.application_stack.register_postfork_function(self.init)
        else:
            self.init()

    def init(self):
        log.debug("Initializing job manager interface")
        if self.app.is_job_handler():
            log.debug("Starting job handler")
            self.job_handler = handler.JobHandler(self.app)
            self.job_stop_queue = self.job_handler.job_stop_queue
        elif self.app.application_stack.setup_jobs_with_msg:
            # not a handler, but notification is via the application stack
            self.job_handler = MessageJobHandler( self.app )
            self.job_stop_queue = NoopQueue()
        self.job_queue = self.job_handler.job_queue
        self.job_lock = False

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


class MessageJobHandler( object ):
    """
    Implements the JobHandler interface but just to send setup messages on startup

    TODO: It should be documented that starting two Galaxy uWSGI master processes simultaneously would result in a race condition that *could* cause two handlers to pick up the same job.

    The recommended config for now will be webless/main handlers if running more than one uWSGI (master) process
    """
    def __init__(self, app):
        self.app = app
        self.job_queue = MessageJobQueue(app)
        self.job_stop_queue = NoopQueue()

    def start(self):
        # This runs in the web (main) process pre-fork
        jobs_at_startup = self.app.model.context.query(Job).enable_eagerloads(False) \
            .filter((Job.state == Job.states.NEW) & (Job.handler == null())).all()
        if jobs_at_startup:
            log.info('No handler assigned at startup for the following jobs, will dispatch via message: %s', ', '.join([str(j.id) for j in jobs_at_startup]))
        for job in jobs_at_startup:
            self.job_queue.put(job.id, job.tool_id)

    def shutdown(self, *args):
        pass


class MessageJobQueue(object):
    """
    Implements the JobQueue / JobStopQueue interface but only sends messages to the actual job queue
    """
    def __init__(self, app):
        self.app = app

    def put(self, job_id, tool_id):
        msg = JobHandlerMessage(task='setup', job_id=job_id)
        self.app.application_stack.send_message(self.app.config.job_handler_pool_name, msg)

    def put_stop(self, *args):
        pass

    def shutdown(self):
        pass
