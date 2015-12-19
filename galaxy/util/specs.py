import functools
import operator

from galaxy import util


# Utility methods for specifing maps.
def to_str_or_none( value ):
    if value is None:
        return None
    else:
        return str( value )


def to_bool_or_none( value ):
    return util.string_as_bool_or_none( value )


def to_bool( value ):
    return util.asbool( value )


def to_float_or_none( value ):
    if value is None:
        return None
    else:
        return float( value )


# Utility methods for specifing valid...
def is_in( *args ):
    return functools.partial( operator.contains, args )
