""" Module for validation of incoming inputs.

TODO: Refactor BaseController references to similar methods to use this module.
"""

from galaxy import exceptions
from galaxy.util.sanitize_html import sanitize_html


def validate_and_sanitize_basestring(key, val):
    if not isinstance(val, str):
        raise exceptions.RequestParameterInvalidException(f"{key} must be a string or unicode: {type(val)}")
    return sanitize_html(val)


def validate_and_sanitize_basestring_list(key, val):
    try:
        assert isinstance(val, list)
        return [sanitize_html(t) for t in val]
    except (AssertionError, TypeError):
        raise exceptions.RequestParameterInvalidException(f"{key} must be a list of strings: {type(val)}")


def validate_boolean(key, val):
    if not isinstance(val, bool):
        raise exceptions.RequestParameterInvalidException(f"{key} must be a boolean: {type(val)}")
    return val


# TODO:
# def validate_integer(self, key, val, min, max):
# def validate_float(self, key, val, min, max):
# def validate_number(self, key, val, min, max):
# def validate_genome_build(self, key, val):
