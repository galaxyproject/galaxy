import binascii
import copy
import json
import logging
import uuid

from galaxy import eggs
eggs.require("SQLAlchemy")
import sqlalchemy

from galaxy.util.aliaspickler import AliasPickleModule
from sqlalchemy.types import CHAR, LargeBinary, String, TypeDecorator
from sqlalchemy.ext.mutable import Mutable

log = logging.getLogger( __name__ )

# Default JSON encoder and decoder
json_encoder = json.JSONEncoder( sort_keys=True )
json_decoder = json.JSONDecoder( )


def _sniffnfix_pg9_hex(value):
    """
    Sniff for and fix postgres 9 hex decoding issue
    """
    try:
        if value[0] == 'x':
            return binascii.unhexlify(value[1:])
        elif value.startswith( '\\x' ):
            return binascii.unhexlify( value[2:] )
        else:
            return value
    except Exception:
        return value


class MutableDict(Mutable, dict):
    # MutableDict following http://docs.sqlalchemy.org/en/latest/orm/extensions/mutable.html
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)


class JSONType( TypeDecorator ):
    """
    Defines a JSONType for SQLAlchemy.  Takes a primitive as input and
    JSONifies it.  This should replace PickleType throughout Galaxy.
    """
    impl = LargeBinary

    def process_bind_param( self, value, dialect ):
        if value is None:
            return None
        return json_encoder.encode( value )

    def process_result_value( self, value, dialect ):
        if value is not None:
            try:
                return json_decoder.decode( str( _sniffnfix_pg9_hex( value ) ) )
            except Exception, e:
                log.error( 'Failed to decode JSON (%s): %s', value, e )
        return None

    def copy_value( self, value ):
        # return json_decoder.decode( json_encoder.encode( value ) )
        return copy.deepcopy( value )

    def compare_values( self, x, y ):
        # return json_encoder.encode( x ) == json_encoder.encode( y )
        return ( x == y )

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(sqlalchemy.dialects.mysql.MEDIUMBLOB)
        else:
            return self.impl


MutableDict.associate_with(JSONType)


metadata_pickler = AliasPickleModule( {
    ( "cookbook.patterns", "Bunch" ): ( "galaxy.util.bunch", "Bunch" )
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


class UUIDType(TypeDecorator):
    """
    Platform-independent UUID type.

    Based on http://docs.sqlalchemy.org/en/rel_0_8/core/types.html#backend-agnostic-guid-type
    Changed to remove sqlalchemy 0.8 specific code

    CHAR(32), storing as stringified hex values.
    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


class TrimmedString( TypeDecorator ):
    impl = String

    def process_bind_param( self, value, dialect ):
        """Automatically truncate string values"""
        if self.impl.length and value is not None:
            value = value[0:self.impl.length]
        return value
