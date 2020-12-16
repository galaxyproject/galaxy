import binascii
import copy
import json
import logging
import uuid
from collections import deque
from itertools import chain
from sys import getsizeof

import numpy
import sqlalchemy
from sqlalchemy.ext.mutable import (
    Mutable,
    MutableDict,
    MutableList,
)
from sqlalchemy.types import (
    CHAR,
    LargeBinary,
    String,
    TypeDecorator
)

from galaxy.util import (
    smart_str,
    unicodify
)
from galaxy.util.aliaspickler import AliasPickleModule

log = logging.getLogger(__name__)


class SafeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.int_):
            return int(obj)
        elif isinstance(obj, numpy.float_):
            return float(obj)
        elif isinstance(obj, bytes):
            return unicodify(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


json_encoder = SafeJsonEncoder(sort_keys=True)
json_decoder = json.JSONDecoder()

# Galaxy app will set this if configured to avoid circular dependency
MAX_METADATA_VALUE_SIZE = None


def _sniffnfix_pg9_hex(value):
    """
    Sniff for and fix postgres 9 hex decoding issue
    """
    try:
        if value[0] == 'x':
            return binascii.unhexlify(value[1:])
        elif smart_str(value).startswith(b'\\x'):
            return binascii.unhexlify(value[2:])
        else:
            return value
    except Exception:
        return value


class GalaxyLargeBinary(LargeBinary):

    # This hack is necessary because the LargeBinary result processor
    # does not specify an encoding in the `bytes` call ,
    # likely because `result` should be binary.
    # This doesn't seem to be the case in galaxy.
    def result_processor(self, dialect, coltype):
        def process(value):
            if value is not None:
                if isinstance(value, str):
                    value = bytes(value, encoding='utf-8')
                else:
                    value = bytes(value)
            return value
        return process


class JSONType(sqlalchemy.types.TypeDecorator):
    """
    Represents an immutable structure as a json-encoded string.

    If default is, for example, a dict, then a NULL value in the
    database will be exposed as an empty dict.
    """

    # TODO: Figure out why this is a large binary, and provide a migratino to
    # something like sqlalchemy.String, or even better, when applicable, native
    # sqlalchemy.dialects.postgresql.JSON
    impl = GalaxyLargeBinary

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json_encoder.encode(value).encode()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json_decoder.decode(unicodify(_sniffnfix_pg9_hex(value)))
        return value

    def load_dialect_impl(self, dialect):
        if dialect.name == "mysql":
            return dialect.type_descriptor(sqlalchemy.dialects.mysql.MEDIUMBLOB)
        else:
            return self.impl

    def copy_value(self, value):
        return copy.deepcopy(value)

    def compare_values(self, x, y):
        return (x == y)


class MutationObj(Mutable):
    """Converts plain python lists or dicts into appropriate sqlalchemy types."""
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, dict) and not isinstance(value, MutableDict):
            return MutableDict.coerce(key, value)
        if isinstance(value, list) and not isinstance(value, MutableList):
            return MutableList.coerce(key, value)
        return value


MutationObj.associate_with(JSONType)

metadata_pickler = AliasPickleModule({
    ("cookbook.patterns", "Bunch"): ("galaxy.util.bunch", "Bunch")
})


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

    all_handlers = {tuple: iter,
                    list: iter,
                    deque: iter,
                    dict: dict_handler,
                    set: iter,
                    frozenset: iter}
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


class MetadataType(JSONType):
    """
    Backward compatible metadata type. Can read pickles or JSON, but always
    writes in JSON.
    """

    def process_bind_param(self, value, dialect):
        if value is not None:
            if MAX_METADATA_VALUE_SIZE is not None:
                for k, v in list(value.items()):
                    sz = total_size(v)
                    if sz > MAX_METADATA_VALUE_SIZE:
                        del value[k]
                        log.warning(f'Refusing to bind metadata key {k} due to size ({sz})')
            value = json_encoder.encode(value).encode()
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        ret = None
        try:
            ret = metadata_pickler.loads(unicodify(value))
            if ret:
                ret = dict(ret.__dict__)
        except Exception:
            try:
                ret = json_decoder.decode(unicodify(_sniffnfix_pg9_hex(value)))
            except Exception:
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
                value = uuid.UUID(value)
            return value.hex

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


class TrimmedString(TypeDecorator):
    impl = String

    def process_bind_param(self, value, dialect):
        """Automatically truncate string values"""
        if self.impl.length and value is not None:
            value = unicodify(value)[0:self.impl.length]
        return value
