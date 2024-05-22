import inspect
import logging
import os
import threading
import time
from multiprocessing.util import register_after_fork
from typing import Dict

from sqlalchemy import (
    create_engine,
    event,
    exc,
)
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

log = logging.getLogger(__name__)

QUERY_COUNT_LOCAL = threading.local()
WORKING_DIRECTORY = os.getcwd()


def reset_request_query_counts():
    QUERY_COUNT_LOCAL.times = []


def log_request_query_counts(req_id):
    try:
        times = QUERY_COUNT_LOCAL.times
        if times:
            log.info(
                f"Executed [{len(times)}] SQL requests in for web request [{req_id}] ({sum(times) * 1000.0:0.3f} ms)"
            )
    except AttributeError:
        # Didn't record anything so don't worry.
        pass


def stripwd(s):
    if s.startswith(WORKING_DIRECTORY):
        return s[len(WORKING_DIRECTORY) :]
    return s


def pretty_stack():
    rval = []
    for _, fname, line, funcname, _, _ in inspect.stack()[2:]:
        rval.append("%s:%s@%d" % (stripwd(fname), funcname, line))
    return rval


def build_engine(
    url: str,
    engine_options=None,
    database_query_profiling_proxy=False,
    trace_logger=None,
    slow_query_log_threshold=0,
    thread_local_log=None,
    log_query_counts=False,
):
    if database_query_profiling_proxy or slow_query_log_threshold or thread_local_log or log_query_counts:

        @event.listens_for(Engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault("query_start_time", []).append(time.time())

    if slow_query_log_threshold or thread_local_log or log_query_counts:

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info["query_start_time"].pop(-1)
            fragment = "Slow query: "
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
                        duration=total,
                    )
                else:
                    thread_ident = threading.get_ident()
                    stack = " > ".join(pretty_stack())
                    log.debug(
                        f"statement: {statement} parameters: {parameters} executemany: {executemany} duration: {total} stack: {stack} thread: {thread_ident}"
                    )
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

    engine_options = engine_options or {}
    if url.startswith("sqlite://"):
        set_sqlite_connect_args(engine_options, url)

    if url.startswith("sqlite://") and url not in ("sqlite:///:memory:", "sqlite://"):
        engine = create_engine(url, **engine_options, poolclass=NullPool)
    else:
        engine = create_engine(url, **engine_options)

    # Prevent sharing connection across fork: https://docs.sqlalchemy.org/en/14/core/pooling.html#using-connection-pools-with-multiprocessing-or-os-fork
    register_after_fork(engine, lambda e: e.dispose())

    @event.listens_for(engine, "connect")
    def connect(dbapi_connection, connection_record):
        connection_record.info["pid"] = os.getpid()

    @event.listens_for(engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        pid = os.getpid()
        if connection_record.info["pid"] != pid:
            connection_record.dbapi_connection = connection_proxy.dbapi_connection = None
            raise exc.DisconnectionError(
                f"Connection record belongs to pid {connection_record.info['pid']}, attempting to check out in pid {pid}"
            )

    return engine


def set_sqlite_connect_args(engine_options: Dict, url: str) -> None:
    """
    Add or update `connect_args` in `engine_options` if db is sqlite.
    Set check_same_thread to False for sqlite, handled by request-specific session.
    See https://fastapi.tiangolo.com/tutorial/sql-databases/#note
    """
    connect_args = engine_options.setdefault("connect_args", {})
    connect_args["check_same_thread"] = False
