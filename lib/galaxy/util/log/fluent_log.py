"""
Provides a `TraceLogger` implementation that logs to a fluentd collector
"""

import time
import threading

try:
    import galaxy.eggs
    galaxy.eggs.require( "fluent-logger" )
    galaxy.eggs.require( "msgpack_python" )
except Exception:
    pass

try:
    from fluent.sender import FluentSender
except ImportError:
    FluentSender = None


class FluentTraceLogger( object ):
    def __init__( self, name, host='localhost', port=24224 ):
        if FluentSender is None:
            raise Exception("Attempted to use FluentTraceLogger with not Fluent dependency available.")
        self.lock = threading.Lock()
        self.thread_local = threading.local()
        self.name = name
        self.sender = FluentSender( self.name, host=host, port=port )

    def context_set( self, key, value ):
        self.lock.acquire()
        if not hasattr( self.thread_local, 'context' ):
            self.thread_local.context = {}
        self.thread_local.context[key] = value
        self.lock.release()

    def context_remove( self, key ):
        self.lock.acquire()
        del self.thread_local.context[key]
        self.lock.release()

    def log( self, label, time=None, **kwargs ):
        self.lock.acquire()
        if hasattr( self.thread_local, 'context' ):
            kwargs.update( self.thread_local.context )
        self.lock.release()
        if time is None:
            time = int( time.time() )
        self.sender.emit_with_time( label, time, kwargs )
