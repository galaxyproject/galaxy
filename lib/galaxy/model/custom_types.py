import binascii
import copy
import json
import logging
import uuid

from sys import getsizeof
from itertools import chain
from collections import deque

import sqlalchemy

from galaxy import app
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


class JSONType(sqlalchemy.types.TypeDecorator):
    """
    Represents an immutable structure as a json-encoded string.

    If default is, for example, a dict, then a NULL value in the
    database will be exposed as an empty dict.
    """

    # TODO: Figure out why this is a large binary, and provide a migratino to
    # something like sqlalchemy.String, or even better, when applicable, native
    # sqlalchemy.dialects.postgresql.JSON
    impl = LargeBinary

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json_encoder.encode(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json_decoder.decode( str( _sniffnfix_pg9_hex( value ) ) )
        return value

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(sqlalchemy.dialects.mysql.MEDIUMBLOB)
        else:
            return self.impl

    def copy_value( self, value ):
        return copy.deepcopy( value )

    def compare_values( self, x, y ):
        return ( x == y )


class MutationObj(Mutable):
    """
    Mutable JSONType for SQLAlchemy from original gist:
    https://gist.github.com/dbarnett/1730610

    Using minor changes from this fork of the gist:
    https://gist.github.com/miracle2k/52a031cced285ba9b8cd

    And other minor changes to make it work for us.
    """
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, dict) and not isinstance(value, MutationDict):
            return MutationDict.coerce(key, value)
        if isinstance(value, list) and not isinstance(value, MutationList):
            return MutationList.coerce(key, value)
        return value

    @classmethod
    def _listen_on_attribute(cls, attribute, coerce, parent_cls):
        key = attribute.key
        if parent_cls is not attribute.class_:
            return

        # rely on "propagate" here
        parent_cls = attribute.class_

        def load(state, *args):
            val = state.dict.get(key, None)
            if coerce and key not in state.unloaded:
                val = cls.coerce(key, val)
                state.dict[key] = val
            if isinstance(val, cls):
                val._parents[state.obj()] = key

        def set(target, value, oldvalue, initiator):
            if not isinstance(value, cls):
                value = cls.coerce(key, value)
            if isinstance(value, cls):
                value._parents[target.obj()] = key
            if isinstance(oldvalue, cls):
                oldvalue._parents.pop(target.obj(), None)
            return value

        def pickle(state, state_dict):
            val = state.dict.get(key, None)
            if isinstance(val, cls):
                if 'ext.mutable.values' not in state_dict:
                    state_dict['ext.mutable.values'] = []
                state_dict['ext.mutable.values'].append(val)

        def unpickle(state, state_dict):
            if 'ext.mutable.values' in state_dict:
                for val in state_dict['ext.mutable.values']:
                    val._parents[state.obj()] = key

        sqlalchemy.event.listen(parent_cls, 'load', load, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'refresh', load, raw=True, propagate=True)
        sqlalchemy.event.listen(attribute, 'set', set, raw=True, retval=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'pickle', pickle, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, 'unpickle', unpickle, raw=True, propagate=True)


class MutationDict(MutationObj, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to MutationDict"""
        self = MutationDict((k, MutationObj.coerce(key, v)) for (k, v) in value.items())
        self._key = key
        return self

    def __setitem__(self, key, value):
        if hasattr(self, '_key'):
            value = MutationObj.coerce(self._key, value)
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)


class MutationList(MutationObj, list):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain list to MutationList"""
        self = MutationList((MutationObj.coerce(key, v) for v in value))
        self._key = key
        return self

    def __setitem__(self, idx, value):
        list.__setitem__(self, idx, MutationObj.coerce(self._key, value))
        self.changed()

    def __setslice__(self, start, stop, values):
        list.__setslice__(self, start, stop, (MutationObj.coerce(self._key, v) for v in values))
        self.changed()

    def __delitem__(self, idx):
        list.__delitem__(self, idx)
        self.changed()

    def __delslice__(self, start, stop):
        list.__delslice__(self, start, stop)
        self.changed()

    def __copy__(self):
        return MutationList(MutationObj.coerce(self._key, self[:]))

    def __deepcopy__(self, memo):
        return MutationList(MutationObj.coerce(self._key, copy.deepcopy(self[:])))

    def append(self, value):
        list.append(self, MutationObj.coerce(self._key, value))
        self.changed()

    def insert(self, idx, value):
        list.insert(self, idx, MutationObj.coerce(self._key, value))
        self.changed()

    def extend(self, values):
        list.extend(self, (MutationObj.coerce(self._key, v) for v in values))
        self.changed()

    def pop(self, *args, **kw):
        value = list.pop(self, *args, **kw)
        self.changed()
        return value

    def remove(self, value):
        list.remove(self, value)
        self.changed()


MutationObj.associate_with(JSONType)

metadata_pickler = AliasPickleModule( {
    ( "cookbook.patterns", "Bunch" ): ( "galaxy.util.bunch", "Bunch" )
} )


def total_size(o, handlers={}, verbose=False):
    """ Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    Recipe from:  https://code.activestate.com/recipes/577504-compute-memory-footprint-of-an-object-and-its-cont/
    """
    def dict_handler(d):
        return chain.from_iterable(d.items())
    all_handlers = { tuple: iter,
                     list: iter,
                     deque: iter,
                     dict: dict_handler,
                     set: iter,
                     frozenset: iter }
    all_handlers.update(handlers)     # user handlers take precedence
    seen = set()                      # track which object id's have already been seen
    default_size = getsizeof(0)       # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:       # do not double count the same object
            return 0
        seen.add(id(o))
        s = getsizeof(o, default_size)

        for typ, handler in all_handlers.items():
            if isinstance(o, typ):
                s += sum(map(sizeof, handler(o)))
                break
        return s

    return sizeof(o)


class MetadataType( JSONType ):
    """
    Backward compatible metadata type. Can read pickles or JSON, but always
    writes in JSON.
    """

    def process_bind_param(self, value, dialect):
        if value is not None:
            if app.app and app.app.config.max_metadata_value_size:
                for k, v in value.items():
                    sz = total_size(v)
                    if sz > app.app.config.max_metadata_value_size:
                        del value[k]
                        log.warning('Refusing to bind metadata key %s due to size (%s)' % (k, sz))
            value = json_encoder.encode(value)
        return value

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
