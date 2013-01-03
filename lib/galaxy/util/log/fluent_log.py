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

	def context_push( self, value ):
		self.lock.acquire()
		if not hasattr( self.thread_local, 'context' ):
			self.thread_local.context = []
		self.thread_local.context.append( value )
		self.lock.release()

	def context_pop( self ):
		self.lock.acquire()
		self.thread_local.context.pop()
		self.lock.release()

	def log( self, label, **kwargs ):
		self.lock.acquire()
		if not hasattr( self.thread_local, 'context' ):
			self.thread_local.context = []
		self.lock.release()
		kwargs['log_context'] = self.thread_local.context
		self.sender.emit_with_time( label, int(time.time()), kwargs )