"""
Classes for wrapping Objects and Sanitizing string output.
"""

import inspect
import logging
import string
import sys

from numbers import Number
try:
    from types import NoneType
except ImportError:
    NoneType = type(None)
try:
    from types import NotImplementedType
except ImportError:
    NotImplementedType = type(NotImplemented)

try:
    from types import EllipsisType
except ImportError:
    EllipsisType = type(Ellipsis)

try:
    from types import XRangeType
except ImportError:
    XRangeType = type(range(0))

try:
    from types import SliceType
except ImportError:
    SliceType = type([][:])

try:
    from types import BufferType
    from types import DictProxyType
except ImportError:
    # Py3 doesn't have these concepts, just treat them like SliceType that
    # so they are __WRAP_NO_SUBCLASS__.
    BufferType = SliceType
    DictProxyType = SliceType

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
from six.moves import copyreg as copy_reg
from six.moves import UserDict

from galaxy.util import sanitize_lists_to_string as _sanitize_lists_to_string

log = logging.getLogger( __name__ )

# Define different behaviors for different types, see also: https://docs.python.org/2/library/types.html

# Known Callable types
__CALLABLE_TYPES__ = ( FunctionType, MethodType, GeneratorType, CodeType, BuiltinFunctionType, BuiltinMethodType, )

# Always wrap these types without attempting to subclass
__WRAP_NO_SUBCLASS__ = ( ModuleType, XRangeType, SliceType, BufferType, TracebackType, FrameType, DictProxyType,
                         GetSetDescriptorType, MemberDescriptorType ) + __CALLABLE_TYPES__

# Don't wrap or sanitize.
__DONT_SANITIZE_TYPES__ = ( Number, bool, NoneType, NotImplementedType, EllipsisType, bytearray, )

# Don't wrap, but do sanitize.
__DONT_WRAP_TYPES__ = tuple()  # ( basestring, ) so that we can get the unsanitized string, we will now wrap basestring instances

# Wrap contents, but not the container
__WRAP_SEQUENCES__ = ( tuple, list, )
__WRAP_SETS__ = ( set, frozenset, )
__WRAP_MAPPINGS__ = ( dict, UserDict, )


# Define the set of characters that are not sanitized, and define a set of mappings for those that are.
# characters that are valid
VALID_CHARACTERS = set( string.ascii_letters + string.digits + " -=_.()/+*^,:?!@" )

# characters that are allowed but need to be escaped
CHARACTER_MAP = { '>': '__gt__',
                  '<': '__lt__',
                  "'": '__sq__',
                  '"': '__dq__',
                  '[': '__ob__',
                  ']': '__cb__',
                  '{': '__oc__',
                  '}': '__cc__',
                  '\n': '__cn__',
                  '\r': '__cr__',
                  '\t': '__tc__',
                  '#': '__pd__'}

INVALID_CHARACTER = "X"

if sys.version_info > (3, 0):
    # __coerce__ doesn't do anything under Python anyway.
    def coerce(x, y):
        return x


def cmp(x, y):
    # Builtin in Python 2, but not Python 3.
    return (x > y) - (x < y)


def sanitize_lists_to_string( values, valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP, invalid_character=INVALID_CHARACTER  ):
    return _sanitize_lists_to_string( values, valid_characters=valid_characters, character_map=character_map, invalid_character=invalid_character  )


def wrap_with_safe_string( value, no_wrap_classes=None ):
    """
    Recursively wrap values that should be wrapped.
    """

    def __do_wrap( value ):
        if isinstance( value, SafeStringWrapper ):
            # Only ever wrap one-layer
            return value
        if callable( value ):
            safe_class = CallableSafeStringWrapper
        else:
            safe_class = SafeStringWrapper
        if isinstance( value, no_wrap_classes ):
            return value
        if isinstance( value, __DONT_WRAP_TYPES__ ):
            return sanitize_lists_to_string( value, valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP )
        if isinstance( value, __WRAP_NO_SUBCLASS__ ):
            return safe_class( value, safe_string_wrapper_function=__do_wrap )
        for this_type in __WRAP_SEQUENCES__ + __WRAP_SETS__:
            if isinstance( value, this_type ):
                return this_type( map( __do_wrap, value ) )
        for this_type in __WRAP_MAPPINGS__:
            if isinstance( value, this_type ):
                # Wrap both key and value
                return this_type( map( lambda x: ( __do_wrap( x[0] ), __do_wrap( x[1] ) ), value.items() ) )
        # Create a dynamic class that joins SafeStringWrapper with the object being wrapped.
        # This allows e.g. isinstance to continue to work.
        try:
            wrapped_class_name = value.__name__
            wrapped_class = value
        except:
            wrapped_class_name = value.__class__.__name__
            wrapped_class = value.__class__
        value_mod = inspect.getmodule( value )
        if value_mod:
            wrapped_class_name = "%s.%s" % ( value_mod.__name__, wrapped_class_name )
        wrapped_class_name = "SafeStringWrapper(%s:%s)" % ( wrapped_class_name, ",".join( sorted( map( str, no_wrap_classes ) ) ) )
        do_wrap_func_name = "__do_wrap_%s" % ( wrapped_class_name )
        do_wrap_func = __do_wrap
        global_dict = globals()
        if wrapped_class_name in global_dict:
            # Check to see if we have created a wrapper for this class yet, if so, reuse
            wrapped_class = global_dict.get( wrapped_class_name )
            do_wrap_func = global_dict.get( do_wrap_func_name, __do_wrap )
        else:
            try:
                wrapped_class = type( wrapped_class_name, ( safe_class, wrapped_class, ), {} )
            except TypeError as e:
                # Fail-safe for when a class cannot be dynamically subclassed.
                log.warning( "Unable to create dynamic subclass for %s, %s: %s", type( value), value, e )
                wrapped_class = type( wrapped_class_name, ( safe_class, ), {} )
            if wrapped_class not in ( SafeStringWrapper, CallableSafeStringWrapper ):
                # Save this wrapper for reuse and pickling/copying
                global_dict[ wrapped_class_name ] = wrapped_class
                do_wrap_func.__name__ = do_wrap_func_name
                global_dict[ do_wrap_func_name ] = do_wrap_func

                def pickle_safe_object( safe_object ):
                    return ( wrapped_class, ( safe_object.unsanitized, do_wrap_func, ) )
                # Set pickle and copy properties
                copy_reg.pickle( wrapped_class, pickle_safe_object, do_wrap_func )
        return wrapped_class( value, safe_string_wrapper_function=do_wrap_func )
    # Determine classes not to wrap
    if no_wrap_classes:
        if not isinstance( no_wrap_classes, ( tuple, list ) ):
            no_wrap_classes = [ no_wrap_classes ]
        no_wrap_classes = list( no_wrap_classes ) + list( __DONT_SANITIZE_TYPES__ ) + [ SafeStringWrapper ]
    else:
        no_wrap_classes = list( __DONT_SANITIZE_TYPES__ ) + [ SafeStringWrapper ]
    no_wrap_classes = tuple( set( sorted( no_wrap_classes, key=str ) ) )
    return __do_wrap( value )


# N.B. refer to e.g. https://docs.python.org/2/reference/datamodel.html for information on Python's Data Model.


class SafeStringWrapper( object ):
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
    __UNSANITIZED_ATTRIBUTE_NAME__ = 'unsanitized'
    __NO_WRAP_NAMES__ = [ '__safe_string_wrapper_function__', __UNSANITIZED_ATTRIBUTE_NAME__]

    def __new__( cls, *arg, **kwd ):
        # We need to define a __new__ since, we are subclassing from e.g. immutable str, which internally sets data
        # that will be used when other + this (this + other is handled by __add__)
        try:
            return super( SafeStringWrapper, cls ).__new__( cls, sanitize_lists_to_string( arg[0], valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP ) )
        except Exception as e:
            log.warning( "Could not provide an argument to %s.__new__: %s; will try without arguments.", cls, e )
            return super( SafeStringWrapper, cls ).__new__( cls )

    def __init__( self, value, safe_string_wrapper_function=wrap_with_safe_string ):
        self.unsanitized = value
        self.__safe_string_wrapper_function__ = safe_string_wrapper_function

    def __str__( self ):
        return sanitize_lists_to_string( self.unsanitized, valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP )

    def __repr__( self ):
        return "%s object at %x on: %s" % ( sanitize_lists_to_string( self.__class__.__name__, valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP ), id( self ), sanitize_lists_to_string( repr( self.unsanitized ), valid_characters=VALID_CHARACTERS, character_map=CHARACTER_MAP ) )

    def __lt__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized < other

    def __le__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized <= other

    def __eq__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized == other

    def __ne__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized != other

    def __gt__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized > other

    def __ge__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.unsanitized >= other

    def __cmp__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return cmp( self.unsanitized, other )

    # Do not implement __rcmp__, python 2.2 < 2.6

    def __hash__( self ):
        return hash( self.unsanitized )

    def __nonzero__( self ):
        return bool( self.unsanitized )

    # Do not implement __unicode__, we will rely on __str__

    def __getattr__( self, name ):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            # FIXME: is this ever reached?
            return object.__getattr__( self, name )
        return self.__safe_string_wrapper_function__( getattr( self.unsanitized, name ) )

    def __setattr__( self, name, value ):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__setattr__( self, name, value )
        return setattr( self.unsanitized, name, value )

    def __delattr__( self, name ):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__delattr__( self, name )
        return delattr( self.unsanitized, name )

    def __getattribute__( self, name ):
        if name in SafeStringWrapper.__NO_WRAP_NAMES__:
            return object.__getattribute__( self, name )
        return self.__safe_string_wrapper_function__( getattr( object.__getattribute__( self, 'unsanitized' ), name ) )

    # Skip Descriptors

    # Skip __slots__

    # Don't need __metaclass__, we'll use the helper function to handle with subclassing for e.g. isinstance()

    # Revisit:
    # __instancecheck__
    # __subclasscheck__
    # We are using a helper class to create dynamic subclasses to handle class checks

    # We address __call__ as needed based upon unsanitized, through the use of a CallableSafeStringWrapper class

    def __len__( self ):
        original_value = self.unsanitized
        while isinstance( original_value, SafeStringWrapper ):
            original_value = self.unsanitized
        return len( self.unsanitized )

    def __getitem__( self, key ):
        return self.__safe_string_wrapper_function__( self.unsanitized[ key ] )

    def __setitem__( self, key, value ):
        while isinstance( value, SafeStringWrapper ):
            value = value.unsanitized
        self.unsanitized[ key ] = value

    def __delitem__( self, key ):
        del self.unsanitized[ key ]

    def __iter__( self ):
        return iter( map( self.__safe_string_wrapper_function__, iter( self.unsanitized ) ) )

    # Do not implement __reversed__

    def __contains__( self, item ):
        # FIXME: Do we need to consider if item is/isn't or does/doesn't contain SafeStringWrapper?
        # When considering e.g. nested lists/dicts/etc, this gets complicated
        while isinstance( item, SafeStringWrapper ):
            item = item.unsanitized
        return item in self.unsanitized

    # Not sure that we need these slice methods, but will provide anyway
    def __getslice__( self, i, j ):
        return self.__safe_string_wrapper_function__( self.unsanitized[ i:j ] )

    def __setslice__( self, i, j, value ):
        self.unsanitized[ i:j ] = value

    def __delslice__( self, i, j ):
        del self.unsanitized[ i:j ]

    def __add__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized + other )

    def __sub__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized - other )

    def __mul__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized * other )

    def __floordiv__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized // other )

    def __mod__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized % other )

    def __divmod__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( divmod( self.unsanitized, other ) )

    def __pow__( self, *other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( pow( self.unsanitized, *other ) )

    def __lshift__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized << other )

    def __rshift__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized >> other )

    def __and__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized & other )

    def __xor__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized ^ other )

    def __or__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized | other )

    def __div__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized / other )

    def __truediv__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( self.unsanitized / other )

    # The only reflected operand that we will define is __rpow__, due to coercion rules complications as per docs
    def __rpow__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return self.__safe_string_wrapper_function__( pow( other, self.unsanitized ) )

    # Do not implement in-place operands

    def __neg__( self ):
        return self.__safe_string_wrapper_function__( -self.unsanitized )

    def __pos__( self ):
        return self.__safe_string_wrapper_function__( +self.unsanitized )

    def __abs__( self ):
        return self.__safe_string_wrapper_function__( abs( self.unsanitized ) )

    def __invert__( self ):
        return self.__safe_string_wrapper_function__( ~self.unsanitized )

    def __complex__( self ):
        return self.__safe_string_wrapper_function__( complex( self.unsanitized ) )

    def __int__( self ):
        return int( self.unsanitized )

    def __float__( self ):
        return float( self.unsanitized )

    def __oct__( self ):
        return oct( self.unsanitized )

    def __hex__( self ):
        return hex( self.unsanitized )

    def __index__( self ):
        return self.unsanitized.index()

    def __coerce__( self, other ):
        while isinstance( other, SafeStringWrapper ):
            other = other.unsanitized
        return coerce( self.unsanitized, other )

    def __enter__( self ):
        return self.unsanitized.__enter__()

    def __exit__( self, *args ):
        return self.unsanitized.__exit__( *args )


class CallableSafeStringWrapper( SafeStringWrapper ):

    def __call__( self, *args, **kwds ):
        return self.__safe_string_wrapper_function__( self.unsanitized( *args, **kwds ) )


# Enable pickling/deepcopy
def pickle_SafeStringWrapper( safe_object ):
    args = ( safe_object.unsanitized, )
    cls = SafeStringWrapper
    if isinstance( safe_object, CallableSafeStringWrapper ):
        cls = CallableSafeStringWrapper
    return ( cls, args )
copy_reg.pickle( SafeStringWrapper, pickle_SafeStringWrapper, wrap_with_safe_string )
copy_reg.pickle( CallableSafeStringWrapper, pickle_SafeStringWrapper, wrap_with_safe_string )
