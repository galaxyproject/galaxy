"""
Galaxy web application framework
"""

from routes import request_config

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


def legacy_url_for(mapper, *args, **kwargs) -> str:
    """
    Re-establishes the mapper for legacy WSGI routes.
    """
    rc = request_config()
    rc.mapper = mapper
    return base.routes.url_for(*args, **kwargs)


url_for = handle_url_for
