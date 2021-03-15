"""
Galaxy web application framework
"""

from . import base


def handle_url_for(*args, **kargs) -> str:
    try:
        return base.routes.url_for(*args, **kargs)
    except AttributeError:
        if len(args) > 0:
            return args[0]
        return "*deprecated attribute not filled in by FastAPI server*"


url_for = handle_url_for
