"""
Classes for wrapping Objects and Sanitizing string output.
"""

import copyreg
import inspect
import logging
from collections import UserDict
from collections.abc import Callable
from numbers import Number
from types import (
    BuiltinFunctionType,
    BuiltinMethodType,
    CodeType,
    FrameType,
    FunctionType,
    GeneratorType,
    GetSetDescriptorType,
    MemberDescriptorType,
    MethodType,
    ModuleType,
    TracebackType,
)

from sqlalchemy.orm import InstanceState

from galaxy.util import (
    MAPPED_CHARACTERS as _mapped_characters,
    sanitize_lists_to_string as _sanitize_lists_to_string,
    VALID_CHARACTERS as _valid_characters,
)

# Handle difference between valid/mapped chars defined in galaxy.utils and this module:
VALID_CHARACTERS = _valid_characters.copy() | set('@')  # Add '@' to valid chars
MAPPED_CHARACTERS = {key: value for key, value in _mapped_characters.items() if key != '@'}  # Remove mapping for '@'

NoneType = type(None)
NotImplementedType = type(NotImplemented)
EllipsisType = type(Ellipsis)
RangeType = range
SliceType = slice

log = logging.getLogger(__name__)

# Define different behaviors for different types, see also: https://docs.python.org/3/library/types.html

# Known Callable types
__CALLABLE_TYPES__ = (FunctionType, MethodType, GeneratorType, CodeType, BuiltinFunctionType, BuiltinMethodType, )

# Always wrap these types without attempting to subclass
__WRAP_NO_SUBCLASS__ = (ModuleType, RangeType, SliceType, TracebackType, FrameType,
                        GetSetDescriptorType, MemberDescriptorType) + __CALLABLE_TYPES__

# Don't wrap or sanitize.
__DONT_SANITIZE_TYPES__ = (Number, bool, NoneType, NotImplementedType, EllipsisType, bytearray, )

# Wrap contents, but not the container
__WRAP_SEQUENCES__ = (tuple, list, )
__WRAP_SETS__ = (set, frozenset, )
__WRAP_MAPPINGS__ = (dict, UserDict, )


def sanitize_lists_to_string(value):
    return _sanitize_lists_to_string(
        value, valid_characters=VALID_CHARACTERS, character_map=MAPPED_CHARACTERS)


def wrap_with_safe_string(value, no_wrap_classes=None):
    """
    Recursively wrap values that should be wrapped.
    """

    def __do_wrap(value):
        if isinstance(value, no_wrap_classes):
            return value
        safe_class = CallableSafeStringWrapper if isinstance(value, Callable) else SafeStringWrapper
        if isinstance(value, __WRAP_NO_SUBCLASS__):
            return safe_class(value, safe_string_wrapper_function=__do_wrap)
        for this_type in __WRAP_SEQUENCES__ + __WRAP_SETS__:
            if isinstance(value, this_type):
                return this_type(list(map(__do_wrap, value)))
        for this_type in __WRAP_MAPPINGS__:
            if isinstance(value, this_type):
                return this_type((__do_wrap(key), __do_wrap(value)) for key, value in value.items())

        # Create a dynamic class that joins SafeStringWrapper with the object being wrapped.
        # This allows e.g. isinstance to continue to work.
        class_to_wrap, wrapped_class_name = get_class_and_name_for_wrapping(value, safe_class)
        do_wrap_func_name = f"__do_wrap_{wrapped_class_name}"
        do_wrap_func = __do_wrap
        global_dict = globals()
        if wrapped_class_name in global_dict:
            # Check to see if we have created a wrapper for this class yet, if so, reuse
            wrapped_class = global_dict.get(wrapped_class_name)
            do_wrap_func = global_dict.get(do_wrap_func_name, __do_wrap)
        else:
            try:
                wrapped_class = type(wrapped_class_name, (safe_class, class_to_wrap, ), {})
            except TypeError as e:
                # Fail-safe for when a class cannot be dynamically subclassed.
                log.warning(f"Unable to create dynamic subclass {wrapped_class_name} for {type(value)}, {value}: {e}")
                wrapped_class = type(wrapped_class_name, (safe_class, ), {})
            if wrapped_class not in (SafeStringWrapper, CallableSafeStringWrapper):
                # Save this wrapper for reuse and pickling/copying
                global_dict[wrapped_class_name] = wrapped_class
                do_wrap_func.__name__ = do_wrap_func_name
                global_dict[do_wrap_func_name] = do_wrap_func

                def pickle_safe_object(safe_object):
                    return (wrapped_class, (safe_object.unsanitized, do_wrap_func, ))
                # Set pickle and copy properties
                copyreg.pickle(wrapped_class, pickle_safe_object, do_wrap_func)
        return wrapped_class(value, safe_string_wrapper_function=do_wrap_func)

    no_wrap_classes = get_no_wrap_classes(no_wrap_classes)
    no_wrap_classes = tuple(set(sorted(no_wrap_classes, key=str)))
    return __do_wrap(value)


def get_no_wrap_classes(no_wrap_classes=None):
    """ Determine classes not to wrap."""
    _default = list(__DONT_SANITIZE_TYPES__) + [SafeStringWrapper]
    if no_wrap_classes:
        if not isinstance(no_wrap_classes, (tuple, list)):
            no_wrap_classes = [no_wrap_classes]
        return list(no_wrap_classes) + _default
    return _default


def get_class_and_name_for_wrapping(value, safe_class):
    """Return class to be wrapped + a name for the wrapped class."""
    try:
        class_name = value.__name__
        class_ = value
    except Exception:
        class_name = value.__class__.__name__
        class_ = value.__class__
    value_mod = inspect.getmodule(value)
    if value_mod:
        class_name = f"{value_mod.__name__}.{class_name}"
    class_name = f"{safe_class.__name__}({class_name})"
    return (class_, class_name)


def unwrap(value):
    while isinstance(value, SafeStringWrapper):
        value = value.unsanitized
    return value


# N.B. refer to e.g. https://docs.python.org/reference/datamodel.html for information on Python's Data Model.


class SafeStringWrapper:
    """
    Class that wraps and sanitizes any provided value's attributes
    that will attempt to be cast into a string.

    Attempts to mimic behavior of original class, including operands.

    To ensure proper handling of e.g. subclass checks, the *wrap_with_safe_string()*
    method should be used.

    This wrapping occurs in a recursive/parasitic fashion, as all called attributes of
    the originally wrapped object will also be wrapped and sanitized, unless the attribute
    is of a type found in __DONT_SANITIZE_TYPES__ + __DONT_WRAP_TYPES__, where e.g. ~(strings
    will still be sanitized, but not wrapped), and e.g. integers will have neither.
    """
    __NO_WRAP_NAMES__ = ['__safe_string_wrapper_function__', '__class__', 'unsanitized']

    def __new__(cls, *arg, **kwd):
        # We need to define a __new__ since, we are subclassing from e.g. immutable str, which internally sets data
        # that will be used when other + this (this + other is handled by __add__)
        try:
            sanitized_value = sanitize_lists_to_string(arg[0])
            return super().__new__(cls, sanitized_value)
        except TypeError:
            # Class to be wrapped takes no parameters.
            # This is pefectly normal for mutable types.
            return super().__new__(cls)

    def __init__(self, value, safe_string_wrapper_function=wrap_with_safe_string):
        self.unsanitized = value
        self.__safe_string_wrapper_function__ = safe_string_wrapper_function

    def __str__(self):
        return sanitize_lists_to_string(self.unsanitized)

    def __repr__(self):
        return f"{sanitize_lists_to_string(self.__class__.__name__)} object at {id(self):x} on: {sanitize_lists_to_string(repr(self.unsanitized))}"

    def __lt__(self, other):
        return self.unsanitized.__lt__(unwrap(other))

    def __le__(self, other):
        return self.unsanitized.__le__(unwrap(other))

    def __eq__(self, other):
        return self.unsanitized.__eq__(unwrap(other))

    def __ne__(self, other):
        return self.unsanitized.__ne__(unwrap(other))

    def __gt__(self, other):
        return self.unsanitized.__gt__(unwrap(other))

    def __ge__(self, other):
        return self.unsanitized.__ge__(unwrap(other))

    def __hash__(self):
        return hash(self.unsanitized)

    def __bool__(self):
        return bool(self.unsanitized)

    def __getattr__(self, name):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            # FIXME: is this ever reached?
            return object.__getattribute__(self, name)
        return self.__safe_string_wrapper_function__(getattr(self.unsanitized, name))

    def __setattr__(self, name, value):
        # A class mapped declaratively is a subclass of DeclarativeMeta. It will check at creation time
        # if self has _sa_instance_state set, and if not, it'll try to set it. This happens BEFORE self.__init__
        # has been called, so self.unsanitized does not exist, which raises an AttributeError.
        # To avoid this, as well as to avoid SQLAlchemy state to be set on SafeStringWrapper,
        # we simply ignore this call.
        if isinstance(value, InstanceState):
            return

        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__setattr__(self, name, value)
        return setattr(self.unsanitized, name, value)

    def __delattr__(self, name):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__delattr__(self, name)
        return delattr(self.unsanitized, name)

    def __getattribute__(self, name):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__getattribute__(self, name)
        return self.__safe_string_wrapper_function__(getattr(object.__getattribute__(self, 'unsanitized'), name))

    # Skip Descriptors

    # Skip __slots__

    # Don't need to define a metaclass, we'll use the helper function to handle with subclassing for e.g. isinstance()

    # Revisit:
    # __instancecheck__
    # __subclasscheck__
    # We are using a helper class to create dynamic subclasses to handle class checks

    # We address __call__ as needed based upon unsanitized, through the use of a CallableSafeStringWrapper class

    def __len__(self):
        return len(unwrap(self.unsanitized))  # can we just do len(self.unsanitized)?

    def __getitem__(self, key):
        return self.__safe_string_wrapper_function__(self.unsanitized[key])

    def __setitem__(self, key, value):
        while isinstance(value, SafeStringWrapper):
            value = value.unsanitized
        self.unsanitized[key] = value

    def __delitem__(self, key):
        del self.unsanitized[key]

    def __iter__(self):
        return iter(map(self.__safe_string_wrapper_function__, iter(self.unsanitized)))

    # Do not implement __reversed__

    def __contains__(self, item):
        # FIXME: Do we need to consider if item is/isn't or does/doesn't contain SafeStringWrapper?
        # When considering e.g. nested lists/dicts/etc, this gets complicated
        while isinstance(item, SafeStringWrapper):
            item = item.unsanitized
        return item in self.unsanitized

    # Binary arithmetic operations

    def __add__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__add__(unwrap(other)))

    def __sub__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__sub__(unwrap(other)))

    def __mul__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__mul__(unwrap(other)))

    def __truediv__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__truediv__(unwrap(other)))

    def __floordiv__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__floordiv__(unwrap(other)))

    def __mod__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__mod__(unwrap(other)))

    def __divmod__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__divmod__(unwrap(other)))

    def __pow__(self, *other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__pow__(*unwrap(other)))

    def __lshift__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__lshift__(unwrap(other)))

    def __rshift__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rshift__(unwrap(other)))

    def __and__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__and__(unwrap(other)))

    def __xor__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__xor__(unwrap(other)))

    def __or__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__or__(unwrap(other)))

    # Binary arithmetic operations with reflected (swapped) operands

    def __radd__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__radd__(unwrap(other)))

    def __rsub__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rsub__(unwrap(other)))

    def __rmul__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rmul__(unwrap(other)))

    def __rtruediv__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rtruediv__(unwrap(other)))

    def __rfloordiv__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rfloordiv__(unwrap(other)))

    def __rmod__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rmod__(unwrap(other)))

    def __rdivmod__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rdivmod__(unwrap(other)))

    def __rpow__(self, *other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rpow__(*unwrap(other)))

    def __rlshift__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rlshift__(unwrap(other)))

    def __rrshift__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rrshift__(unwrap(other)))

    def __rand__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rand__(unwrap(other)))

    def __rxor__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__rxor__(unwrap(other)))

    def __ror__(self, other):
        return self.__safe_string_wrapper_function__(self.unsanitized.__ror__(unwrap(other)))

    # Unary arithmetic operations

    def __neg__(self):
        return self.__safe_string_wrapper_function__(self.unsanitized.__neg__())

    def __pos__(self):
        return self.__safe_string_wrapper_function__(self.unsanitized.__pos__())

    def __abs__(self):
        return self.__safe_string_wrapper_function__(self.unsanitized.__abs__())

    def __invert__(self):
        return self.__safe_string_wrapper_function__(self.unsanitized.__invert__())

    # Misc.

    def __complex__(self):
        return self.__safe_string_wrapper_function__(complex(self.unsanitized))

    def __int__(self):
        return int(self.unsanitized)

    def __float__(self):
        return float(self.unsanitized)

    def __index__(self):
        return self.unsanitized.__index__()

    def __trunc__(self):
        return self.unsanitized.__trunc__()

    def __floor__(self):
        return self.unsanitized.__floor__()

    def __ceil__(self):
        return self.unsanitized.__ceil__()

    def __enter__(self):
        return self.unsanitized.__enter__()

    def __exit__(self, *args):
        return self.unsanitized.__exit__(*args)


class CallableSafeStringWrapper(SafeStringWrapper):

    def __call__(self, *args, **kwds):
        return self.__safe_string_wrapper_function__(self.unsanitized(*args, **kwds))


# Enable pickling/deepcopy
def pickle_SafeStringWrapper(safe_object):
    args = (safe_object.unsanitized, )
    cls = SafeStringWrapper
    if isinstance(safe_object, CallableSafeStringWrapper):
        cls = CallableSafeStringWrapper
    return (cls, args)


copyreg.pickle(SafeStringWrapper, pickle_SafeStringWrapper, wrap_with_safe_string)
copyreg.pickle(CallableSafeStringWrapper, pickle_SafeStringWrapper, wrap_with_safe_string)
