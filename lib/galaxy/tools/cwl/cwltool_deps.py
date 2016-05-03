""" This module contains logic for dealing with cwltool as an optional
dependency for Galaxy and/or applications which use Galaxy as a library.
"""

try:
    import requests
except ImportError:
    requests = None

try:
    from cwltool import (
        main,
        workflow,
        job,
        process,
    )
except ImportError:
    main = None
    workflow = None
    job = None
    process = None

try:
    import shellescape
except ImportError:
    shellescape = None

try:
    import schema_salad
except ImportError:
    schema_salad = None

import re

needs_shell_quoting = re.compile(r"""(^$|[\s|&;()<>\'"$@])""").search


def ensure_cwltool_available():
    if main is None or workflow is None or shellescape is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if requests is None:
            message += " Library 'requests' unavailable."
        if shellescape is None:
            message += " Library 'shellescape' unavailable."
        if schema_salad is None:
            message += " Library 'schema_salad' unavailable."
        raise ImportError(message)


__all__ = [
    'main',
    'workflow',
    'process',
    'ensure_cwltool_available',
    'schema_salad',
    'shellescape',
    'needs_shell_quoting',
]
