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
        job,
        main,
        pathmapper,
        process,
        workflow,
    )
except ImportError:
    main = None  # type: ignore[assignment]
    workflow = None  # type: ignore[assignment]
    job = None  # type: ignore[assignment]
    process = None  # type: ignore[assignment]
    pathmapper = None  # type: ignore[assignment]

try:
    from cwltool.context import (
        getdefault,
        LoadingContext,
        RuntimeContext,
    )
    from cwltool.job import relink_initialworkdir
    from cwltool.stdfsaccess import StdFsAccess
except ImportError:
    getdefault = None  # type: ignore[assignment]
    LoadingContext = None  # type: ignore[assignment,misc]
    relink_initialworkdir = None  # type: ignore[assignment]
    RuntimeContext = None  # type: ignore[assignment,misc]
    StdFsAccess = None  # type: ignore[assignment,misc]

try:
    from cwltool import load_tool
except ImportError:
    load_tool = None  # type: ignore[assignment]


try:
    from cwltool import command_line_tool
except ImportError:
    command_line_tool = None  # type: ignore[assignment]

try:
    from cwltool.load_tool import (
        default_loader,
        resolve_and_validate_document,
    )
except ImportError:
    default_loader = None  # type: ignore[assignment]
    resolve_and_validate_document = None  # type: ignore[assignment]

try:
    from cwltool.utils import (
        normalizeFilesDirs,
        visit_class,
    )
except ImportError:
    visit_class = None  # type: ignore[assignment]
    normalizeFilesDirs = None  # type: ignore[assignment]

try:
    import schema_salad
    from schema_salad import (
        ref_resolver,
        sourceline,
    )
    from schema_salad.utils import yaml_no_ts
except ImportError:
    schema_salad = None  # type: ignore[assignment]
    ref_resolver = None  # type: ignore[assignment]
    sourceline = None  # type: ignore[assignment]
    yaml_no_ts = None  # type: ignore[assignment]

try:
    from ruamel.yaml.comments import CommentedMap
except ImportError:
    CommentedMap = None  # type: ignore[assignment,misc]

needs_shell_quoting = re.compile(r"""(^$|[\s|&;()<>\'"$@])""").search

# if set to True, file format checking is not performed.
beta_relaxed_fmt_check = True


def ensure_cwltool_available():
    """Assert optional dependencies proxied via this module are available at runtime.

    Throw an ImportError with a description of the problem if they do not exist.
    """
    if main is None or workflow is None:
        message = "This feature requires cwltool and dependencies to be available, they are not."
        if main is None:
            message += " cwltool is not unavailable."
        elif resolve_and_validate_document is None:
            message += " cwltool.load_tool.resolve_and_validate_document is unavailable - cwltool version is too old."
        if requests is None:
            message += " Library 'requests' unavailable."
        if schema_salad is None:
            message += " Library 'schema_salad' unavailable."
        raise ImportError(message)


__all__ = (
    "CommentedMap",
    "default_loader",
    "ensure_cwltool_available",
    "getdefault",
    "load_tool",
    "LoadingContext",
    "main",
    "needs_shell_quoting",
    "normalizeFilesDirs",
    "pathmapper",
    "process",
    "ref_resolver",
    "relink_initialworkdir",
    "resolve_and_validate_document",
    "RuntimeContext",
    "schema_salad",
    "sourceline",
    "StdFsAccess",
    "visit_class",
    "workflow",
    "yaml_no_ts",
)
