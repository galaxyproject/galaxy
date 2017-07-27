"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""

import json
import logging

from galaxy.jobs import handler, NoopQueue
from galaxy.model import Job

log = logging.getLogger(__name__)


class JobManager(object):
    """
    Highest level interface to job management.

    TODO: Currently the app accesses "job_queue" and "job_stop_queue" directly.
          This should be decoupled.
    """

    def __init__(self, app):
        self.app = app
        if self.app.is_job_handler():
            log.debug("Starting job handler")
            self.job_handler = handler.JobHandler(app)
            self.job_stop_queue = self.job_handler.job_stop_queue
        elif app.application_stack.setup_jobs_with_msg:
            self.job_handler = NoopHandler()
            self.job_handler.job_queue = MessageJobQueue(app)
            self.job_stop_queue = NoopQueue()
        else:
            self.job_handler = NoopHandler()
            self.job_stop_queue = NoopQueue
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


class MessageJobQueue( object ):
    """
    Implements the JobQueue / JobStopQueue interface but only sends messages to the actual job queue
    """
    def __init__(self, app):
        self.app = app

    def put(self, job_id, tool_id):
        # FIXME: uwsgi farm name hardcoded here
        # TODO: probably need a single class that encodes and decodes messages
        self.app.application_stack.send_msg(json.dumps({'msg_type': 'setup', 'job_id': job_id, 'state': Job.states.NEW}), 'handlers')

    def put_stop(self, *args):
        return

    def shutdown(self):
        return
