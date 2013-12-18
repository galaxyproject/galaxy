import logging
log = logging.getLogger( __name__ )

from sqlalchemy import create_engine
from galaxy.model.orm import load_egg_for_url


def build_engine(url, engine_options, database_query_profiling_proxy=False, trace_logger=None):
    load_egg_for_url( url )

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
