import warnings

from galaxy.util.commands import (  # noqa: F401
    argv_to_str,
    CommandLineException,
    download_command,
    execute,
    redirect_aware_commmunicate,
    redirecting_io,
    shell,
    shell_process,
    which,
)


warnings.warn("Importing galaxy.tool_util.deps.commands is deprecated, use galaxy.util.commands instead", DeprecationWarning)
