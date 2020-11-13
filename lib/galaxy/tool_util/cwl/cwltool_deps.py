"""Logic for dealing with cwltool as an optional dependency.

Use this as the import interface for cwltool and just call
:func:`ensure_cwltool_available` before using any of the imported
functionality at runtime.
"""
import re
import warnings

warnings.filterwarnings("ignore", message=r"[\n.]DEPRECATION: Python 2", module="cwltool")

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
except ImportError:
    main = None
    workflow = None
    job = None
    process = None
    pathmapper = None

try:
    from cwltool.context import (
        getdefault,
        LoadingContext,
        RuntimeContext,
    )
    from cwltool.job import relink_initialworkdir
    from cwltool.stdfsaccess import StdFsAccess
except ImportError:
    getdefault = None
    LoadingContext = None
    relink_initialworkdir = None
    RuntimeContext = None
    StdFsAccess = None

try:
    from cwltool import load_tool
    from cwltool.load_tool import (
        default_loader,
        resolve_and_validate_document,
    )
except ImportError:
    default_loader = None
    load_tool = None
    resolve_and_validate_document = None

try:
    from cwltool import command_line_tool
    command_line_tool.ACCEPTLIST_RE = command_line_tool.ACCEPTLIST_EN_RELAXED_RE
except ImportError:
    command_line_tool = None

try:
    from cwltool.load_tool import resolve_and_validate_document
except ImportError:
    resolve_and_validate_document = None

try:
    from cwltool import command_line_tool
    command_line_tool.ACCEPTLIST_RE = command_line_tool.ACCEPTLIST_EN_RELAXED_RE
except ImportError:
    command_line_tool = None

try:
    import shellescape
except ImportError:
    shellescape = None

try:
    import schema_salad
    from schema_salad import (
        ref_resolver,
        sourceline,
    )
except ImportError:
    schema_salad = None
    ref_resolver = None
    sourceline = None

needs_shell_quoting = re.compile(r"""(^$|[\s|&;()<>\'"$@])""").search

# if set to True, file format checking is not performed.
beta_relaxed_fmt_check = True


def ensure_cwltool_available():
    """Assert optional dependencies proxied via this module are available at runtime.

    Throw an ImportError with a description of the problem if they do not exist.
    """
    if main is None or workflow is None or shellescape is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if main is None:
            message += " cwltool is not unavailable."
        elif resolve_and_validate_document is None:
            message += " cwltool.load_tool.resolve_and_validate_document is unavailable - cwltool version is too old."
        if requests is None:
            message += " Library 'requests' unavailable."
        if shellescape is None:
            message += " Library 'shellescape' unavailable."
        if schema_salad is None:
            message += " Library 'schema_salad' unavailable."
        raise ImportError(message)


__all__ = (
    'default_loader',
    'ensure_cwltool_available',
    'getdefault',
    'load_tool',
    'LoadingContext',
    'main',
    'needs_shell_quoting',
    'pathmapper',
    'process',
    'ref_resolver',
    'relink_initialworkdir',
    'resolve_and_validate_document',
    'RuntimeContext',
    'schema_salad',
    'shellescape',
    'sourceline',
    'StdFsAccess',
    'workflow',
)
