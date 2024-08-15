"""
Galaxy web application framework
"""

from . import base

DEPRECATED_URL_ATTRIBUTE_MESSAGE = "*deprecated attribute, URL not filled in by server*"


def handle_url_for(*args, **kwargs) -> str:
    """Tries to resolve the URL using the `routes` module.

    This only works in a WSGI app so a deprecation message is returned
    when running an ASGI app.
    """
    try:
        return base.routes.url_for(*args, **kwargs)
    except AttributeError:
        return DEPRECATED_URL_ATTRIBUTE_MESSAGE


url_for = handle_url_for
