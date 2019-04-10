import datetime
import functools
import operator

from galaxy import util


# Utility methods for specifing maps.
def to_str_or_none(value):
    if value is None:
        return None
    else:
        return str(value)


def to_bool_or_none(value):
    return util.string_as_bool_or_none(value)


def to_bool(value):
    return util.asbool(value)


def to_float_or_none(value):
    if value is None:
        return None
    else:
        return float(value)


def to_datetime_interval_or_none(value):
    if value is None:
        return None
    else:
        h, m, s = [int(v) for v in value.split(':')]
        return datetime.timedelta(seconds=s, minutes=m, hours=h)


# Utility methods for specifing valid...
def is_in(*args):
    return functools.partial(operator.contains, args)
