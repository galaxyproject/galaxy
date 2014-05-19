"""
Top-level Galaxy job manager, moves jobs to handler(s)
"""

import logging

from galaxy.jobs import handler, NoopQueue

log = logging.getLogger( __name__ )


class JobManager( object ):
    """
    Highest level interface to job management.

    TODO: Currently the app accesses "job_queue" and "job_stop_queue" directly.
          This should be decoupled.
    """
    def __init__( self, app ):
        self.app = app
        if (self.app.config.track_jobs_in_database and self.app.job_config.is_handler(self.app.config.server_name)) or not self.app.config.track_jobs_in_database:
            log.debug("Starting job handler")
            self.job_handler = handler.JobHandler( app )
            self.job_queue = self.job_handler.job_queue
            self.job_stop_queue = self.job_handler.job_stop_queue
        else:
            self.job_handler = NoopHandler()
            self.job_queue = self.job_stop_queue = NoopQueue()
        self.job_handler.start()

    def shutdown( self ):
        self.job_handler.shutdown()


class NoopHandler( object ):
    def __init__( self, *args, **kwargs ):
        self.job_queue = NoopQueue()
        self.job_stop_queue = NoopQueue()

    def start( self ):
        pass

    def shutdown( self, *args ):
        pass
