from sqlalchemy.types import *
import pkg_resources
pkg_resources.require("simplejson")
import simplejson
import pickle
from galaxy.util.bunch import Bunch
from galaxy.util.aliaspickler import AliasPickleModule

# Default JSON encoder and decoder
json_encoder = simplejson.JSONEncoder( sort_keys=True )
json_decoder = simplejson.JSONDecoder( )

class JSONType( TypeDecorator ):
    """ 
    Defines a JSONType for SQLAlchemy.  Takes a primitive as input and
    JSONifies it.  This should replace PickleType throughout Galaxy.
    """
    impl = Binary

    def process_bind_param( self, value, dialect ):
        if value is None:
            return None
        return json_encoder.encode( value )

    def process_result_value( self, value, dialect ):
        if value is None:
            return None
        return json_decoder.decode( str( value ) )
    
    def copy_value( self, value ):
        return json_decoder.decode( json_encoder.encode( value ) )

    def compare_values( self, x, y ):
        try:
            return x.values == y.values
        except:
            return x == y
    
    def is_mutable( self ):
        return True

metadata_pickler = AliasPickleModule( {
    ( "cookbook.patterns", "Bunch" ) : ( "galaxy.util.bunch" , "Bunch" )
} )

class MetadataType( JSONType ):
    """
    Backward compatible metadata type. Can read pickles or JSON, but always
    writes in JSON.
    """
    def process_result_value( self, value, dialect ):
        if value is None:
            return None
        ret = None
        try:
            ret = metadata_pickler.loads( str( value ) )
            if ret:
                ret = dict( ret.__dict__ )
        except:
            try:
                ret = json_decoder.decode( str( value ) )
            except:
                ret = None
        return ret
    
class TrimmedString( TypeDecorator ):
    impl = String
    def process_bind_param( self, value, dialect ):
        """Automatically truncate string values"""
        if self.impl.length and value is not None:
            value = value[0:self.impl.length]
        return value
        
