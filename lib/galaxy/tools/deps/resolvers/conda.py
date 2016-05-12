"""
This is still an experimental module and there will almost certainly be backward
incompatible changes coming.
"""


import os

from galaxy.exceptions import NotImplemented

from ..resolvers import (
    DependencyResolver,
    INDETERMINATE_DEPENDENCY,
    Dependency,
    ListableDependencyResolver,
    InstallableDependencyResolver,
)
from ..conda_util import (
    CondaContext,
    CondaTarget,
    install_conda,
    is_conda_target_installed,
    install_conda_target,
    build_isolated_environment,
    installed_conda_targets,
    USE_PATH_EXEC_DEFAULT,
)

DEFAULT_BASE_PATH_DIRECTORY = "_conda"
DEFAULT_CONDARC_OVERRIDE = "_condarc"
DEFAULT_ENSURE_CHANNELS = "r,bioconda"

import logging
log = logging.getLogger(__name__)


class CondaDependencyResolver(DependencyResolver, ListableDependencyResolver, InstallableDependencyResolver):
    dict_collection_visible_keys = DependencyResolver.dict_collection_visible_keys + ['conda_prefix', 'versionless', 'ensure_channels', 'auto_install']
    resolver_type = "conda"

    def __init__(self, dependency_manager, **kwds):
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))

        def get_option(name):
            return self._get_config_option(name, dependency_manager, config_prefix="conda", **kwds)

        # Conda context options (these define the environment)
        conda_prefix = get_option("prefix")
        if conda_prefix is None:
            conda_prefix = os.path.join(
                dependency_manager.default_base_path, DEFAULT_BASE_PATH_DIRECTORY
            )

        condarc_override = get_option("condarc_override")
        if condarc_override is None:
            condarc_override = os.path.join(
                dependency_manager.default_base_path, DEFAULT_CONDARC_OVERRIDE
            )

        conda_exec = get_option("exec")
        debug = _string_as_bool(get_option("debug"))
        ensure_channels = get_option("ensure_channels")
        use_path_exec = get_option("use_path_exec")
        if use_path_exec is None:
            use_path_exec = USE_PATH_EXEC_DEFAULT
        else:
            use_path_exec = _string_as_bool(use_path_exec)
        if ensure_channels is None:
            ensure_channels = DEFAULT_ENSURE_CHANNELS

        conda_context = CondaContext(
            conda_prefix=conda_prefix,
            conda_exec=conda_exec,
            debug=debug,
            ensure_channels=ensure_channels,
            condarc_override=condarc_override,
            use_path_exec=use_path_exec,
        )
        self.ensure_channels = ensure_channels

        # Conda operations options (these define how resolution will occur)
        auto_init = _string_as_bool(get_option("auto_init"))
        auto_install = _string_as_bool(get_option("auto_install"))
        copy_dependencies = _string_as_bool(get_option("copy_dependencies"))

        if auto_init and not os.path.exists(conda_context.conda_prefix):
            if install_conda(conda_context):
                raise Exception("Conda installation requested and failed.")

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

        exact = not self.versionless or version is None
        if self.versionless:
            version = None

        conda_target = CondaTarget(name, version=version)
        is_installed = is_conda_target_installed(
            conda_target, conda_context=self.conda_context
        )
        if not is_installed and self.auto_install:
            install_conda_target(conda_target, conda_context=self.conda_context)

            # Recheck if installed
            is_installed = is_conda_target_installed(
                conda_target, conda_context=self.conda_context
            )

        if not is_installed:
            return INDETERMINATE_DEPENDENCY

        # Have installed conda_target and job_directory to send it too.
        # If dependency is for metadata generation, store environment in conda-metadata-env
        if kwds.get("metadata", False):
            conda_env = "conda-metadata-env"
        else:
            conda_env = "conda-env"
        conda_environment = os.path.join(job_directory, conda_env)
        env_path, exit_code = build_isolated_environment(
            conda_target,
            path=conda_environment,
            copy=self.copy_dependencies,
            conda_context=self.conda_context,
        )
        if not exit_code:
            return CondaDepenency(
                self.conda_context.activate,
                conda_environment,
                exact,
            )
        else:
            raise Exception("Conda dependency seemingly installed but failed to build job environment.")

    def list_dependencies(self):
        for install_target in installed_conda_targets(self.conda_context):
            name = install_target.package
            version = install_target.version
            yield self._to_requirement(name, version)

    def install_dependency(self, name, version, type, **kwds):
        if type != "package":
            raise NotImplemented("Can only install dependencies of type '%s'" % type)

        if self.versionless:
            version = None
        conda_target = CondaTarget(name, version=version)

        if install_conda_target(conda_target, conda_context=self.conda_context):
            raise Exception("Failed to install conda recipe.")

    @property
    def prefix(self):
        return self.conda_context.conda_prefix


class CondaDepenency(Dependency):
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + ['environment_path']
    dependency_type = 'conda'

    def __init__(self, activate, environment_path, exact):
        self.activate = activate
        self.environment_path = environment_path
        self._exact = exact

    @property
    def exact(self):
        return self._exact

    def shell_commands(self, requirement):
        return """[ "$CONDA_DEFAULT_ENV" = "%s" ] || . %s '%s' 2>&1 """ % (
            self.environment_path,
            self.activate,
            self.environment_path
        )


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = ['CondaDependencyResolver']
