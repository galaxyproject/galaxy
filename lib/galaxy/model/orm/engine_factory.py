import inspect
import logging
import os
import threading
import time

from sqlalchemy import create_engine, event
from sqlalchemy.engine import (
    Engine,
)

log = logging.getLogger(__name__)

QUERY_COUNT_LOCAL = threading.local()
WORKING_DIRECTORY = os.getcwd()


def reset_request_query_counts():
    QUERY_COUNT_LOCAL.times = []


def log_request_query_counts(req_id):
    try:
        times = QUERY_COUNT_LOCAL.times
        if times:
            log.info("Executed [{}] SQL requests in for web request [{}] ({:0.3f} ms)".format(len(times), req_id, sum(times) * 1000.))
    except AttributeError:
        # Didn't record anything so don't worry.
        pass


def stripwd(s):
    if s.startswith(WORKING_DIRECTORY):
        return s[len(WORKING_DIRECTORY):]
    return s


def pretty_stack():
    rval = []
    for _, fname, line, funcname, _, _ in inspect.stack()[2:]:
        rval.append("%s:%s@%d" % (stripwd(fname), funcname, line))
    return rval


def build_engine(url, engine_options, database_query_profiling_proxy=False, trace_logger=None, slow_query_log_threshold=0, thread_local_log=None, log_query_counts=False):
    if database_query_profiling_proxy or slow_query_log_threshold or thread_local_log or log_query_counts:

        @event.listens_for(Engine, "before_execute")
        def before_execute(conn, clauseelement, multiparams, params):
            conn.info.setdefault('query_start_time', []).append(time.time())

    if slow_query_log_threshold or thread_local_log or log_query_counts:
        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement,
                                 parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            fragment = 'Slow query: '
            if total > slow_query_log_threshold:
                log.debug(f"{fragment}{total:f}(s)\n{statement}\nParameters: {parameters}")
            if database_query_profiling_proxy:
                if trace_logger:
                    trace_logger.log(
                        "sqlalchemy_query",
                        message="Query executed",
                        statement=statement,
                        parameters=parameters,
                        executemany=executemany,
                        duration=total
                    )
                else:
                    thread_ident = threading.get_ident()
                    stack = " > ".join(pretty_stack())
                    log.debug(f"statement: {statement} parameters: {parameters} executemany: {executemany} duration: {total} stack: {stack} thread: {thread_ident}")
            if log_query_counts:
                try:
                    QUERY_COUNT_LOCAL.times.append(total)
                except AttributeError:
                    # Not a web thread.
                    pass
            if thread_local_log is not None:
                try:
                    if thread_local_log.log:
                        log.debug(f"Request query: {total:f}(s)\n{statement}\nParameters: {parameters}")
                except AttributeError:
                    pass

    # Create the database engine
    engine = create_engine(url, **engine_options)
    return engine
