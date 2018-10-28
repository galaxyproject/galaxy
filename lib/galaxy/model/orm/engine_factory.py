import logging
import time

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

log = logging.getLogger(__name__)


def build_engine(url, engine_options, database_query_profiling_proxy=False, trace_logger=None, slow_query_log_threshold=0, thread_local_log=None):
    # Should we use the logging proxy?
    if database_query_profiling_proxy:
        import galaxy.model.orm.logging_connection_proxy as logging_connection_proxy
        proxy = logging_connection_proxy.LoggingProxy()
    # If metlog is enabled, do micrologging
    elif trace_logger:
        import galaxy.model.orm.logging_connection_proxy as logging_connection_proxy
        proxy = logging_connection_proxy.TraceLoggerProxy(trace_logger)
    else:
        proxy = None
    if slow_query_log_threshold or thread_local_log:
        @event.listens_for(Engine, "before_execute")
        def before_execute(conn, clauseelement, multiparams, params):
            conn.info.setdefault('query_start_time', []).append(time.time())

        @event.listens_for(Engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement,
                                 parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            if total > slow_query_log_threshold:
                log.debug("Slow query: %f(s)\n%s\nParameters: %s" % (total, statement, parameters))
            if thread_local_log is not None:
                try:
                    if thread_local_log.log:
                        log.debug("Request query: %f(s)\n%s\nParameters: %s" % (total, statement, parameters))
                except AttributeError:
                    pass

    # Create the database engine
    engine = create_engine(url, proxy=proxy, **engine_options)
    return engine
