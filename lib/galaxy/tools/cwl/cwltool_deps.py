""" This module contains logic for dealing with cwltool as an optional
dependency for Galaxy and/or applications which use Galaxy as a library.
"""

try:
    from galaxy import eggs
    eggs.require("requests")
except Exception:
    pass

try:
    import requests
except ImportError:
    requests = None

try:
    from cwltool import (
        ref_resolver,
        draft1tool,
        draft2tool,
    )
except ImportError as e:
    ref_resolver = None
    draft1tool = None
    draft2tool = None

try:
    import jsonschema
except ImportError:
    jsonschema = None

try:
    import avro
except ImportError:
    avro = None


def ensure_cwltool_available():
    if ref_resolver is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if avro is None:
            message += " Library avro unavailable."
        if jsonschema is None:
            message += " Library jsonschema unavailable."
        if requests is None:
            message += " Library requests unavailable."
        raise ImportError(message)


__all__ = [
    'ref_resolver',
    'draft1tool',
    'draft2tool',
    'ensure_cwltool_available',
]
