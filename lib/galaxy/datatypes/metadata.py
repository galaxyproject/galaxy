import sys

# Taken in part from Elixir and how they do it: http://elixir.ematia.de

STATEMENTS = "__galaxy_statements__"

class Statement( object ):
    def __init__( self, target ):
        self.target = target
    def __call__( self, *args, **kwargs ):
        class_locals = sys._getframe(1).f_locals
        statements = class_locals.setdefault(STATEMENTS, [])
        statements.append((self, args, kwargs))
    @classmethod
    def process( cls, element ):
        for statement, args, kwargs in getattr( element, STATEMENTS, [] ):
            statement.target( element, *args, **kwargs )

class MetadataSpecCollection( list ):
    pass

class MetadataWrapper( object ):
    def __init__( self, metadata ):
        self.value = metadata
    def get_value( self ):
        return self.value
    def set_value( self, value ):
        value = self.marshal(value)
        self.validate(value)
        self.value = value
        
    def marshal( self, value ):
        '''
        This method should/can be overridden to convert the incomming
        value to whatever type it is supposed to be.
        '''
        return value

    def validate( self, value ):
        '''
        Throw an exception if the value is invalid.
        '''
        pass

class MetadataElementSpec( object ):
    READONLY = 1
    def __init__( self, datatype, name=None, desc=None, wrapper=MetadataWrapper, attributes=None ):
        self.name = name
        self.desc = desc
        self.wrapper = wrapper
        self.attributes = attributes
        datatype._metadataspec.append( self )
    def hasAttribute( self, attribute ):
        return ((self.permission & attribute) == attribute)
    def wrap( self, metadata ):
        return self.wrapper(metadata)

MetadataElement = Statement(MetadataElementSpec)

