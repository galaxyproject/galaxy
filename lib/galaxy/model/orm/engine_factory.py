import logging
log = logging.getLogger( __name__ )

from sqlalchemy import create_engine


def build_engine(url, engine_options, database_query_profiling_proxy=False, trace_logger=None):
    # Should we use the logging proxy?
    if database_query_profiling_proxy:
        import galaxy.model.orm.logging_connection_proxy as logging_connection_proxy
        proxy = logging_connection_proxy.LoggingProxy()
    # If metlog is enabled, do micrologging
    elif trace_logger:
        import galaxy.model.orm.logging_connection_proxy as logging_connection_proxy
        proxy = logging_connection_proxy.TraceLoggerProxy( trace_logger )
    else:
        proxy = None

    # Create the database engine
    engine = create_engine( url, proxy=proxy, **engine_options )
    return engine
