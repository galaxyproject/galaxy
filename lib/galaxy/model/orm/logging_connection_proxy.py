import time
import inspect
import os

from galaxy.model.orm import *

import logging
log = logging.getLogger( __name__ )
log.addHandler( logging.FileHandler( "sql_query_profiling.log" ) )
log.propagate = False

wd = os.getcwd()
def stripwd( s ):
    if s.startswith( wd ):
        return s[len(wd):]
    return s

def pretty_stack():
    rval = []
    for frame, fname, line, funcname, _, _ in inspect.stack()[2:]:
        rval.append( "%s:%s@%d" % ( stripwd( fname ), funcname, line ) )
    return " > ".join( rval ) 

class LoggingProxy(ConnectionProxy):

    ## def execute(self, conn, execute, clauseelement, *multiparams, **params):
    ##     start = time.clock()
    ##     rval = execute(clauseelement, *multiparams, **params)
    ##     duration = time.clock() - start
    ##     log.debug( "execute -- clauseelement: %r multiparams: %r params: %r duration: %r", 
    ##                str( clauseelement ), multiparams, params, duration )
    ##     return rval

    def cursor_execute(self, execute, cursor, statement, parameters, context, executemany):
        start = time.clock()
        rval = execute(cursor, statement, parameters, context)
        duration = time.clock() - start
        
        log.debug( "statement: %r parameters: %r executemany: %r duration: %r stack: %r",
                   statement, parameters, executemany, duration, pretty_stack() )
        return rval
