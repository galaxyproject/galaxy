"""Logic for dealing with cwltool as an optional dependency.

Use this as the import interface for cwltool and just call
:func:`ensure_cwltool_available` before using any of the imported
functionality at runtime.
"""
import re

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
        pathmapper,
    )
except (ImportError, SyntaxError):
    # Drop SyntaxError once cwltool supports Python 3
    main = None
    workflow = None
    job = None
    process = None
    pathmapper = None

try:
    from cwltool.context import LoadingContext  # Introduced in cwltool 1.0.20180615183820
except (ImportError, SyntaxError):
    LoadingContext = None

try:
    from cwltool import load_tool
except (ImportError, SyntaxError):
    load_tool = None

try:
    import shellescape
except ImportError:
    shellescape = None

try:
    import schema_salad
except (ImportError, SyntaxError):
    # Drop SyntaxError once schema_salad supports Python 3
    schema_salad = None

try:
    from schema_salad import ref_resolver
except (ImportError, SyntaxError):
    ref_resolver = None


needs_shell_quoting = re.compile(r"""(^$|[\s|&;()<>\'"$@])""").search


def ensure_cwltool_available():
    """Assert optional dependencies proxied via this module are available at runtime.

    Throw an ImportError with a description of the problem if they do not exist.
    """
    if main is None or workflow is None or shellescape is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if main is None:
            message += " cwltool is not unavailable."
        elif load_tool is None:
            message += " cwltool.load_tool is unavailable - cwltool version is too old."
        if requests is None:
            message += " Library 'requests' unavailable."
        if shellescape is None:
            message += " Library 'shellescape' unavailable."
        if schema_salad is None:
            message += " Library 'schema_salad' unavailable."
        raise ImportError(message)


__all__ = (
    'main',
    'ref_resolver',
    'load_tool',
    'LoadingContext',
    'workflow',
    'process',
    'pathmapper',
    'ensure_cwltool_available',
    'schema_salad',
    'shellescape',
    'needs_shell_quoting',
)
