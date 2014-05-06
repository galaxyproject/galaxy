"""
Once state information has been calculated, handle actually executing tools
from various states and tracking results.

Later will also create implicit dataset collections from these executions.
"""

import logging
log = logging.getLogger( __name__ )


def execute( trans, tool, param_combinations, history, rerun_remap_job_id=None ):
    """
    Execute a tool and return object containing summary (output data, number of
    failures, etc...).
    """
    execution_tracker = ToolExecutionTracker( tool, param_combinations )
    for params in execution_tracker.param_combinations:
        job, result = tool.handle_single_execution( trans, rerun_remap_job_id, params, history )
        if job:
            execution_tracker.record_success( job, result )
        else:
            execution_tracker.record_error( result )
    return execution_tracker


class ToolExecutionTracker( object ):
    """
    """

    def __init__( self, tool, param_combinations ):
        self.tool = tool
        self.param_combinations = param_combinations
        self.successful_jobs = []
        self.failed_jobs = 0
        self.execution_errors = []
        self.output_datasets = []

    def record_success( self, job, outputs ):
        self.successful_jobs.append( job )
        self.output_datasets.extend( outputs )

    def record_error( self, error ):
        self.failed_jobs += 1
        self.execution_errors.append( error )

__all__ = [ execute ]
