
import inspect
import pprint
import time

import logging
log = logging.getLogger( __name__ )

def stack_trace_string( max_depth=None, line_format="{index}:{file}:{function}:{line}" ):
    """
    Returns a string representation of the current stack.

    :param depth: positive integer to control how many levels of the stack are
    returned. max_depth=None returns the entire stack (default).
    """
    stack_list = []
    for index, caller in enumerate( inspect.stack() ):
        # don't include this function
        if index == 0: continue
        if max_depth and index > max_depth: break

        caller_data = {
            'index'     : str( index ),
            'file'      : caller[1],
            'function'  : caller[3],
            'line'      : caller[2]
        }
        stack_list.append( line_format.format( **caller_data ) )

    return '\n'.join( stack_list )


class SimpleProfiler( object ):
    """
    Simple profiler that captures the duration between calls to `report`
    and stores the results in a list.
    """
    REPORT_FORMAT = '%20f: %s'

    def __init__( self, log=None ):
        self.log = log
        self.start_time = 0
        self.reports = []

    def start( self, msg=None ):
        msg = msg or 'Start'
        self.start_time = time.time()
        report = self.REPORT_FORMAT %( self.start_time, msg )
        self.reports.append( report )
        if self.log:
            self.log( report )

    def report( self, msg ):
        if not self.start_time:
            self.start()
        duration = time.time() - self.start_time
        report = self.REPORT_FORMAT %( duration, msg )
        self.reports.append( report )
        if self.log:
            self.log( report )

    def get_reports( self ):
        return self.reports

    def __str__( self ):
        return '\n'.join( self.reports )
