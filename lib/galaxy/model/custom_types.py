from sqlalchemy.types import *
import pkg_resources
pkg_resources.require("simplejson")
import simplejson
import pickle
import copy
import binascii
from galaxy.util.bunch import Bunch
from galaxy.util.aliaspickler import AliasPickleModule

# For monkeypatching BIGINT
import sqlalchemy.databases.sqlite
import sqlalchemy.databases.postgres
import sqlalchemy.databases.mysql

import logging
log = logging.getLogger( __name__ )

# Default JSON encoder and decoder
json_encoder = simplejson.JSONEncoder( sort_keys=True )
json_decoder = simplejson.JSONDecoder( )

def _sniffnfix_pg9_hex(value):
    """
    Sniff for and fix postgres 9 hex decoding issue
    """
    try:
        if value[0] == 'x':
            return binascii.unhexlify(value[1:])
        else:
            return value
    except Exception, ex:
        return value

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
        return json_decoder.decode( str( _sniffnfix_pg9_hex(value) ) )

    def copy_value( self, value ):
        # return json_decoder.decode( json_encoder.encode( value ) )
        return copy.deepcopy( value )

    def compare_values( self, x, y ):
        # return json_encoder.encode( x ) == json_encoder.encode( y )
        return ( x == y )

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
                ret = json_decoder.decode( str( _sniffnfix_pg9_hex(value) ) )
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


class BigInteger( Integer ):
    """
    A type for bigger ``int`` integers.

    Typically generates a ``BIGINT`` in DDL, and otherwise acts like
    a normal :class:`Integer` on the Python side.

    """

class BIGINT( BigInteger ):
    """The SQL BIGINT type."""

class SLBigInteger( BigInteger ):
    def get_col_spec( self ):
        return "BIGINT"

sqlalchemy.databases.sqlite.SLBigInteger = SLBigInteger
sqlalchemy.databases.sqlite.colspecs[BigInteger] = SLBigInteger
sqlalchemy.databases.sqlite.ischema_names['BIGINT'] = SLBigInteger
sqlalchemy.databases.postgres.colspecs[BigInteger] = sqlalchemy.databases.postgres.PGBigInteger
sqlalchemy.databases.mysql.colspecs[BigInteger] = sqlalchemy.databases.mysql.MSBigInteger
