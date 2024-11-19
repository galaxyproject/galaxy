"""
Galaxy web framework helpers

The functions in this module should be considered part of the API used by
visualizations in their mako files through the `$h` object, see
GalaxyWebTransaction in galaxy/webapps/base/webapp.py
"""

import re
from datetime import (
    datetime,
    timedelta,
    timezone,
)

from babel import default_locale
from babel.dates import format_timedelta
from routes import url_for

from galaxy.util.json import safe_dumps as dumps  # noqa: F401
from .tags import (
    javascript_link,
    stylesheet_link,
)
from ..base import server_starttime


def time_ago(x):
    """
    Convert a datetime to a string.
    """
    # If the date is more than one week ago, then display the actual date instead of in words
    if datetime.now(tz=timezone.utc) - x > timedelta(weeks=1):  # Greater than a week difference
        return x.strftime("%b %d, %Y")
    else:
        # Workaround https://github.com/python-babel/babel/issues/137
        kwargs = {}
        if not default_locale("LC_TIME"):
            kwargs["locale"] = "en_US_POSIX"
        return format_timedelta(x - datetime.now(tz=timezone.utc), threshold=1, add_direction=True, **kwargs)  # type: ignore[arg-type] # https://github.com/python/mypy/issues/9676


def iff(a, b, c):
    """
    Ternary shortcut
    """
    if a:
        return b
    else:
        return c


def truncate(content, length=100, suffix="..."):
    """
    Smart string truncation
    """
    if len(content) <= length:
        return content
    else:
        return content[:length].rsplit(" ", 1)[0] + suffix


# Quick helpers for static content
def css(*args):
    """
    Take a list of stylesheet names (no extension) and return appropriate string
    of link tags.

    Cache-bust with time that server started running on
    """
    urls = (url_for(f"/static/style/{name}.css?v={server_starttime}") for name in args)
    return stylesheet_link(*urls)


def dist_css(*args):
    """
    Transition function 'css' helper -- this is the modern way where all bundled
    artifacts are in the unified 'dist'.
    """
    urls = (url_for(f"/static/dist/{name}.css?v={server_starttime}") for name in args)
    return stylesheet_link(*urls)


def js_helper(prefix, *args):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.

    Cache-bust with time that server started running on
    """
    urls = (url_for(f"/{prefix}{name}.js?v={server_starttime}") for name in args)
    return javascript_link(*urls)


def dist_js(*args):
    """
    Take a prefix and list of javascript names and return appropriate
    string of script tags.
    """
    return js_helper("static/dist/", *args)


def is_true(val):
    """
    Returns true if input is a boolean and true or is a string and looks like a true value.
    """
    return val is True or val in ["True", "true", "T", "t"]


def is_url(val):
    """
    Regular expression to match common URL protocols

    >>> assert is_url(None) == False
    >>> assert is_url("is_url") == False
    >>> assert is_url("http://is_url") == True
    >>> assert is_url("https://is_url") == True
    """
    if val is not None:
        url_pattern = re.compile(r"^(https?:\/\/|ftp:\/\/)")
        return bool(url_pattern.match(val))
    else:
        return False


def to_js_bool(val):
    """
    Prints javascript boolean for passed value.
    TODO: isn't there a standard python JSON parser we should
    be using instead of all these manual conversions?
    """
    return iff(is_true(val), "true", "false")


def js_nullable(val):
    """
    Prints javascript null instead of python None
    TODO: isn't there a standard python JSON parser we should
    be using instead of all these manual conversions?
    """
    return iff(val is None, "null", val)
