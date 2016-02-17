"""
Safe conversion to unicode
"""
from six import text_type


def to_unicode(a_string):
    if a_string is None:
        return None
    return text_type(a_string)
