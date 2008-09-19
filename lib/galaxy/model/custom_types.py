from sqlalchemy.types import *
import simplejson
import pickle
from galaxy.util.bunch import Bunch
from galaxy.util.aliaspickler import AliasPickleModule

class JSONType( TypeDecorator ):
    """ 
    Defines a JSONType for SQLAlchemy.  Takes a primitive as input and
    JSONifies it.  This should replace PickleType throughout Galaxy.
    """
    impl = Binary

    def __init__( self, jsonifyer=None, mutable=True ):
        self.jsonifyer = jsonifyer or simplejson
        self.mutable = mutable
        super( JSONType, self).__init__()

    def process_bind_param( self, value, dialect ):
        if value is None:
            return None
        return self.jsonifyer.dumps( value )

    def process_result_value( self, value, dialect ):
        if value is None:
            return None
        return self.jsonifyer.loads( str( value ) )
    
    def copy_value( self, value ):
        if self.mutable:
            return self.jsonifyer.loads( self.jsonifyer.dumps(value) )
        else:
            return value

    def compare_values( self, x, y ):
        if self.mutable:
            return self.jsonifyer.dumps( x ) == self.jsonifyer.dumps( y )
        else:
            return x is y

    def is_mutable( self ):
        return self.mutable

MetadataPickler = AliasPickleModule( {
    ( "cookbook.patterns", "Bunch" ) : ( "galaxy.util.bunch" , "Bunch" )
} )

class MetadataType( JSONType ):
    """
    Mixture between JSONType and PickleType...can read in either, and
    writes JSON.
    """

    def __init__( self, pickler=MetadataPickler, jsonifyer=None, mutable=True ):
        self.jsonifyer =  jsonifyer or simplejson
        self.pickler = pickler or pickle
        self.mutable = mutable
        super( MetadataType, self).__init__()
    
    def process_result_value( self, value, dialect ):
        if value is None:
            return None
        buf = value
        ret = None
        try:
            ret = self.pickler.loads( str(buf) )
            if ret: ret = dict( ret.__dict__ )
        except:
            try:
                ret = self.jsonifyer.loads( str(buf) )
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
        
