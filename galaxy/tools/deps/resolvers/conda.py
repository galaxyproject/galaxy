"""
This is still an experimental module and there will almost certainly be backward
incompatible changes coming.
"""


import os

from ..resolvers import DependencyResolver, INDETERMINATE_DEPENDENCY
from ..conda_util import (
    CondaContext,
    CondaTarget,
    install_conda,
    is_conda_target_installed,
    install_conda_target,
    build_isolated_environment,
)

DEFAULT_ENSURE_CHANNELS = "r,bioconda"

import logging
log = logging.getLogger(__name__)


class CondaDependencyResolver(DependencyResolver):
    resolver_type = "conda"

    def __init__(self, dependency_manager, **kwds):
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))

        def get_option(name):
            return self._get_config_option(name, dependency_manager, prefix="conda", **kwds)

        # Conda context options (these define the environment)
        conda_prefix = get_option("prefix")
        conda_exec = get_option("exec")
        debug = _string_as_bool(get_option("debug"))
        ensure_channels = get_option("ensure_channels")
        if ensure_channels is None:
            ensure_channels = DEFAULT_ENSURE_CHANNELS

        conda_context = CondaContext(
            conda_prefix=conda_prefix,
            conda_exec=conda_exec,
            debug=debug,
            ensure_channels=ensure_channels,
        )

        # Conda operations options (these define how resolution will occur)
        auto_init = _string_as_bool(get_option("auto_init"))
        auto_install = _string_as_bool(get_option("auto_install"))
        copy_dependencies = _string_as_bool(get_option("copy_dependencies"))

        if auto_init and not os.path.exists(conda_context.conda_prefix):
            install_conda(conda_context)

        self.conda_context = conda_context
        self.auto_install = auto_install
        self.copy_dependencies = copy_dependencies

    def resolve(self, name, version, type, **kwds):
        # Check for conda just not being there, this way we can enable
        # conda by default and just do nothing in not configured.
        if not os.path.isdir(self.conda_context.conda_prefix):
            return INDETERMINATE_DEPENDENCY

        if type != "package":
            return INDETERMINATE_DEPENDENCY

        job_directory = kwds.get("job_directory", None)
        if job_directory is None:
            log.warn("Conda dependency resolver not sent job directory.")
            return INDETERMINATE_DEPENDENCY

        if self.versionless:
            version = None

        conda_target = CondaTarget(name, version=version)
        is_installed = is_conda_target_installed(
            conda_target, conda_context=self.conda_context
        )
        if not is_installed and self.auto_install:
            install_conda_target(conda_target)

            # Recheck if installed
            is_installed = is_conda_target_installed(
                conda_target, conda_context=self.conda_context
            )

        if not is_installed:
            return INDETERMINATE_DEPENDENCY

        # Have installed conda_target and job_directory to send it too.
        conda_environment = os.path.join(job_directory, "conda-env")
        env_path, exit_code = build_isolated_environment(
            conda_target,
            path=conda_environment,
            copy=self.copy_dependencies,
            conda_context=self.conda_context,
        )
        if not exit_code:
            return CondaDepenency(
                self.conda_context.activate,
                conda_environment
            )
        else:
            raise Exception("Conda dependency seemingly installed but failed to build job environment.")


class CondaDepenency():

    def __init__(self, activate, environment_path):
        self.activate = activate
        self.environment_path = environment_path

    def shell_commands(self, requirement):
        return """[ "$CONDA_DEFAULT_ENV" = "%s" ] || source %s '%s'""" % (
            self.environment_path,
            self.activate,
            self.environment_path
        )


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = ['CondaDependencyResolver']
