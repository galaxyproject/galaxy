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
    )
except ImportError:
    main = None
    workflow = None
    job = None

try:
    import shellescape
except ImportError:
    shellescape = None

import re

needs_shell_quoting = re.compile(r"""(^$|[\s|&;()<>\'"$@])""").search


def ensure_cwltool_available():
    if main is None or workflow is None or shellescape is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if requests is None:
            message += " Library 'requests' unavailable."
        if shellescape is None:
            message += " Library 'shellescape' unavailable."
        raise ImportError(message)


__all__ = [
    'main',
    'workflow',
    'ensure_cwltool_available',
    'shellescape',
    'needs_shell_quoting',
]
