import binascii
import copy
import json
import logging
import uuid
from collections import deque
from itertools import chain
from sys import getsizeof
from typing import Optional

import numpy
import sqlalchemy
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.inspection import inspect
from sqlalchemy.types import (
    CHAR,
    LargeBinary,
    String,
    TypeDecorator,
)

from galaxy.util import (
    smart_str,
    unicodify,
)
from galaxy.util.aliaspickler import AliasPickleModule

log = logging.getLogger(__name__)


class SafeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, numpy.int_):
            return int(obj)
        elif isinstance(obj, numpy.float64):
            return float(obj)
        elif isinstance(obj, bytes):
            return unicodify(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


json_encoder = SafeJsonEncoder(sort_keys=True)
json_decoder = json.JSONDecoder()

# Galaxy app will set this if configured to avoid circular dependency
MAX_METADATA_VALUE_SIZE: Optional[int] = None


def _sniffnfix_pg9_hex(value):
    """
    Sniff for and fix postgres 9 hex decoding issue
    """
    try:
        if value[0] == "x":
            return binascii.unhexlify(value[1:])
        elif smart_str(value).startswith(b"\\x"):
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
                    value = bytes(value, encoding="utf-8")
                else:
                    value = bytes(value)
            return value

        return process


class JSONType(TypeDecorator):
    """
    Represents an immutable structure as a json-encoded string.

    If default is, for example, a dict, then a NULL value in the
    database will be exposed as an empty dict.
    """

    # TODO: Figure out why this is a large binary, and provide a migratino to
    # something like sqlalchemy.String, or even better, when applicable, native
    # sqlalchemy.dialects.postgresql.JSON
    impl = GalaxyLargeBinary
    cache_ok = True

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
        return x == y


class DoubleEncodedJsonType(JSONType):
    cache_ok = True

    def process_result_value(self, value, dialect):
        value = super().process_result_value(value, dialect)
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                return value
        return value


class MutableJSONType(JSONType):
    """Associated with MutationObj"""


class MutationObj(Mutable):
    """
    Mutable JSONType for SQLAlchemy from original gist:
    https://gist.github.com/dbarnett/1730610

    Using minor changes from this fork of the gist:
    https://gist.github.com/miracle2k/52a031cced285ba9b8cd

    And other minor changes to make it work for us.
    """

    def __new__(cls, *args, **kwds):
        self = super().__new__(cls, *args, **kwds)
        self._key = None
        return self

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
                val._parents[state] = key

        def set(target, value, oldvalue, initiator):
            if not isinstance(value, cls):
                value = cls.coerce(key, value)
            if isinstance(value, cls):
                value._parents[target] = key
            if isinstance(oldvalue, cls):
                oldvalue._parents.pop(inspect(target), None)
            return value

        def pickle(state, state_dict):
            val = state.dict.get(key, None)
            if isinstance(val, cls):
                if "ext.mutable.values" not in state_dict:
                    state_dict["ext.mutable.values"] = []
                state_dict["ext.mutable.values"].append(val)

        def unpickle(state, state_dict):
            if "ext.mutable.values" in state_dict:
                for val in state_dict["ext.mutable.values"]:
                    val._parents[state] = key

        sqlalchemy.event.listen(parent_cls, "load", load, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, "refresh", load, raw=True, propagate=True)
        sqlalchemy.event.listen(attribute, "set", set, raw=True, retval=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, "pickle", pickle, raw=True, propagate=True)
        sqlalchemy.event.listen(parent_cls, "unpickle", unpickle, raw=True, propagate=True)


class MutationDict(MutationObj, dict):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain dictionary to MutationDict"""
        self = MutationDict((k, MutationObj.coerce(key, v)) for (k, v) in value.items())
        self._key = key
        return self

    def __setitem__(self, key, value):
        value = MutationObj.coerce(self._key, value)
        super().__setitem__(key, value)
        self.changed()

    def __delitem__(self, key):
        super().__delitem__(key)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)

    def pop(self, *args, **kw):
        value = super().pop(*args, **kw)
        self.changed()
        return value

    def update(self, *args, **kwargs):
        value = super().update(*args, **kwargs)
        self.changed()
        return value


class MutationList(MutationObj, list):
    @classmethod
    def coerce(cls, key, value):
        """Convert plain list to MutationList"""
        self = MutationList(MutationObj.coerce(key, v) for v in value)
        self._key = key
        return self

    def __setitem__(self, idx, value):
        super().__setitem__(idx, MutationObj.coerce(self._key, value))
        self.changed()

    def __setslice__(self, start, stop, values):
        super().__setslice__(start, stop, (MutationObj.coerce(self._key, v) for v in values))
        self.changed()

    def __delitem__(self, idx):
        super().__delitem__(idx)
        self.changed()

    def __delslice__(self, start, stop):
        super().__delslice__(start, stop)
        self.changed()

    def __copy__(self):
        return MutationList(MutationObj.coerce(self._key, self[:]))

    def __deepcopy__(self, memo):
        return MutationList(MutationObj.coerce(self._key, copy.deepcopy(self[:])))

    def append(self, value):
        super().append(MutationObj.coerce(self._key, value))
        self.changed()

    def insert(self, idx, value):
        super().insert(self, idx, MutationObj.coerce(self._key, value))
        self.changed()

    def extend(self, values):
        values = (MutationObj.coerce(self._key, value) for value in values)
        super().extend(values)
        self.changed()

    def pop(self, *args, **kw):
        value = super().pop(*args, **kw)
        self.changed()
        return value

    def remove(self, value):
        super().remove(value)
        self.changed()


MutationObj.associate_with(MutableJSONType)


metadata_pickler = AliasPickleModule({("cookbook.patterns", "Bunch"): ("galaxy.util.bunch", "Bunch")})


def total_size(o, handlers=None, verbose=False):
    """Returns the approximate memory footprint an object and all of its contents.

    Automatically finds the contents of the following builtin containers and
    their subclasses:  tuple, list, deque, dict, set and frozenset.
    To search other containers, add handlers to iterate over their contents:

        handlers = {SomeContainerClass: iter,
                    OtherContainerClass: OtherContainerClass.get_elements}

    Recipe from:  https://code.activestate.com/recipes/577504-compute-memory-footprint-of-an-object-and-its-cont/
    """
    handlers = handlers or {}

    def dict_handler(d):
        return chain.from_iterable(d.items())

    all_handlers = {tuple: iter, list: iter, deque: iter, dict: dict_handler, set: iter, frozenset: iter}
    all_handlers.update(handlers)  # user handlers take precedence
    seen = set()  # track which object id's have already been seen
    default_size = getsizeof(0)  # estimate sizeof object without __sizeof__

    def sizeof(o):
        if id(o) in seen:  # do not double count the same object
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

    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if MAX_METADATA_VALUE_SIZE is not None:
                if hasattr(value, "items"):
                    for k, v in list(value.items()):
                        sz = total_size(v)
                        if sz > MAX_METADATA_VALUE_SIZE:
                            del value[k]
                            log.warning(f"Refusing to bind metadata key {k} due to size ({sz})")
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
    cache_ok = True

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
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Automatically truncate string values"""
        if self.impl.length and value is not None:
            value = unicodify(value)[0 : self.impl.length]
        return value
