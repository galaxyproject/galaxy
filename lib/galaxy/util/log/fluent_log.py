"""
Provides a `TraceLogger` implementation that logs to a fluentd collector
"""

import time
import threading

import galaxy.eggs
galaxy.eggs.require( "fluent-logger" )
galaxy.eggs.require( "msgpack_python" )

from fluent.sender import FluentSender


class FluentTraceLogger( object ):
    def __init__( self, name, host='localhost', port=24224 ):
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

    def log( self, label, **kwargs ):
        self.lock.acquire()
        if hasattr( self.thread_local, 'context' ):
            kwargs.update( self.thread_local.context )
        self.lock.release()
        self.sender.emit_with_time( label, int(time.time()), kwargs )