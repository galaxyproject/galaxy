"""Logic for dealing with cwltool as an optional dependency.

Use this as the import interface for cwltool and just call
:func:`ensure_cwltool_available` before using any of the imported
functionality at runtime.
"""
import re
import warnings

warnings.filterwarnings("ignore", message=r"[\n.]DEPRECATION: Python 2", module="cwltool")

import requests

try:
    from cwltool import (
        main,
        workflow,
        job,
        process,
        pathmapper,
    )
except ImportError:
    main = None  # type: ignore
    workflow = None  # type: ignore
    job = None  # type: ignore
    process = None  # type: ignore
    pathmapper = None  # type: ignore

try:
    from cwltool.context import (
        getdefault,
        LoadingContext,
        RuntimeContext,
    )
    from cwltool.job import relink_initialworkdir
    from cwltool.stdfsaccess import StdFsAccess
except ImportError:
    getdefault = None  # type: ignore
    LoadingContext = None  # type: ignore
    relink_initialworkdir = None  # type: ignore
    RuntimeContext = None  # type: ignore
    StdFsAccess = None  # type: ignore

try:
    from cwltool import load_tool
    from cwltool.load_tool import (
        default_loader,
        resolve_and_validate_document,
    )
except ImportError:
    default_loader = None  # type: ignore
    load_tool = None  # type: ignore
    resolve_and_validate_document = None  # type: ignore


def _has_relax_path_checks_flag():
    """Return True if cwltool uses a flag to control path checks.

    Old cwltool uses the module global below to control whether
    it's strict about path checks. New versions use an attribute
    of LoadingContext.

    Once the version of cwltool required is new enough, we can remove
    this function and simplify the conditionals where it's used.
    """

    lc = LoadingContext()
    return hasattr(lc, "relax_path_checks")


try:
    from cwltool import command_line_tool
    if not _has_relax_path_checks_flag():
        command_line_tool.ACCEPTLIST_RE = command_line_tool.ACCEPTLIST_EN_RELAXED_RE
except ImportError:
    command_line_tool = None  # type: ignore

try:
    from cwltool.load_tool import resolve_and_validate_document
except ImportError:
    resolve_and_validate_document = None  # type: ignore

try:
    import shellescape
except ImportError:
    shellescape = None  # type: ignore

try:
    import schema_salad
    from schema_salad import (
        ref_resolver,
        sourceline,
    )
except ImportError:
    schema_salad = None  # type: ignore
    ref_resolver = None  # type: ignore
    sourceline = None  # type: ignore

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
