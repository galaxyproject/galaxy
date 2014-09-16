class TraceLogger( object ):
	def __init__( self, name ):
		self.name = name
	def log( **kwargs ):
		raise TypeError( "Abstract Method" )
