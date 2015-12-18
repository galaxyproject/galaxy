import inspect
import logging
import os
import threading
import time

from sqlalchemy.interfaces import ConnectionProxy

log = logging.getLogger( __name__ )

wd = os.getcwd()


def stripwd( s ):
    if s.startswith( wd ):
        return s[len(wd):]
    return s


def pretty_stack():
    rval = []
    for frame, fname, line, funcname, _, _ in inspect.stack()[2:]:
        rval.append( "%s:%s@%d" % ( stripwd( fname ), funcname, line ) )
    return rval


class LoggingProxy(ConnectionProxy):
    """
    Logs SQL statements using standard logging module
    """

    def begin(self, conn, begin):
        thread_ident = threading.current_thread().ident
        begin(conn)
        log.debug("begin transaction: thread: %r" % thread_ident)

    def commit(self, conn, commit):
        thread_ident = threading.current_thread().ident
        commit(conn)
        log.debug("commit transaction: thread: %r" % thread_ident)

    def rollback(self, conn, rollback):
        thread_ident = threading.current_thread().ident
        rollback(conn)
        log.debug("rollback transaction: thread: %r" % thread_ident)

    def cursor_execute(self, execute, cursor, statement, parameters, context, executemany):
        thread_ident = threading.current_thread().ident
        start = time.clock()
        rval = execute(cursor, statement, parameters, context)
        duration = time.clock() - start
        log.debug( "statement: %r parameters: %r executemany: %r duration: %r stack: %r thread: %r",
                   statement, parameters, executemany, duration, " > ".join( pretty_stack() ), thread_ident )
        return rval


class TraceLoggerProxy(ConnectionProxy):
    """
    Logs SQL statements using a metlog client
    """
    def __init__( self, trace_logger ):
        self.trace_logger = trace_logger

    def cursor_execute(self, execute, cursor, statement, parameters, context, executemany):
        start = time.clock()
        rval = execute(cursor, statement, parameters, context)
        duration = time.clock() - start
        self.trace_logger.log(
            "sqlalchemy_query",
            message="Query executed",
            statement=statement,
            parameters=parameters,
            executemany=executemany,
            duration=duration
        )
        return rval
