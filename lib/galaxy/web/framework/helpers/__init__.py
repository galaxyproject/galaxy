"""
Galaxy web framework helpers
"""

from ..base import server_starttime
from datetime import datetime, timedelta

from galaxy.util import hash_util
from galaxy.util import unicodify
from galaxy.util.json import safe_dumps as dumps  # Used by mako templates # noqa: F401
from webhelpers import date
from webhelpers.html.tags import stylesheet_link, javascript_link

from routes import url_for


def time_ago( x ):
    """
    Convert a datetime to a string.
    """
    delta = timedelta(weeks=1)

    # If the date is more than one week ago, then display the actual date instead of in words
    if (datetime.utcnow() - x) > delta:  # Greater than a week difference
        return x.strftime("%b %d, %Y")
    else:
        date_array = date.distance_of_time_in_words( x, datetime.utcnow() ).replace(",", "").split(" ")
        return "~%s %s ago" % (date_array[0], date_array[1])


def iff( a, b, c ):
    """
    Ternary shortcut
    """
    if a:
        return b
    else:
        return c


def truncate(content, length=100, suffix='...'):
    """
    Smart string truncation
    """
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(' ', 1)[0] + suffix

# Quick helpers for static content


def css( *args ):
    """
    Take a list of stylesheet names (no extension) and return appropriate string
    of link tags.

    Cache-bust with time that server started running on
    """
    return "\n".join( [ stylesheet_link( url_for( "/static/style/%s.css?v=%s" % (name, server_starttime) ) ) for name in args ] )


def js_helper( prefix, *args ):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.

    Cache-bust with time that server started running on
    """
    return "\n".join( [ javascript_link( url_for( "/%s%s.js?v=%s" % (prefix, name, server_starttime ) ) ) for name in args ] )


def js( *args ):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.
    """
    return js_helper( 'static/scripts/', *args )


def templates( *args ):
    """
    Take a list of template names (no extension) and return appropriate
    string of script tags.
    """
    return js_helper( 'static/scripts/templates/compiled/', *args )

# Hashes


def md5( s ):
    """
    Return hex encoded md5 hash of string s
    """
    m = hash_util.md5()
    m.update( s )
    return m.hexdigest()


# Unicode help
def to_unicode( a_string ):
    """
    Convert a string to unicode in utf-8 format; if string is already unicode,
    does nothing because string's encoding cannot be determined by introspection.
    """
    return unicodify( a_string, 'utf-8' )


def is_true( val ):
    """
    Returns true if input is a boolean and true or is a string and looks like a true value.
    """
    return val is True or val in [ 'True', 'true', 'T', 't' ]
