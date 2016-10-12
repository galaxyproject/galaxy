"""
This is still an experimental module and there will almost certainly be backward
incompatible changes coming.
"""

import logging
import os

import galaxy.tools.deps.installable

from ..conda_util import (
    build_isolated_environment,
    cleanup_failed_install,
    CondaContext,
    CondaTarget,
    install_conda,
    install_conda_target,
    installed_conda_targets,
    is_conda_target_installed,
    USE_PATH_EXEC_DEFAULT,
)
from ..resolvers import (
    Dependency,
    DependencyResolver,
    InstallableDependencyResolver,
    ListableDependencyResolver,
    NullDependency,
)


DEFAULT_BASE_PATH_DIRECTORY = "_conda"
DEFAULT_CONDARC_OVERRIDE = "_condarc"
DEFAULT_ENSURE_CHANNELS = "conda-forge,r,bioconda,iuc"

log = logging.getLogger(__name__)


class CondaDependencyResolver(DependencyResolver, ListableDependencyResolver, InstallableDependencyResolver):
    dict_collection_visible_keys = DependencyResolver.dict_collection_visible_keys + ['conda_prefix', 'versionless', 'ensure_channels', 'auto_install']
    resolver_type = "conda"

    def __init__(self, dependency_manager, **kwds):
        self.versionless = _string_as_bool(kwds.get('versionless', 'false'))
        self.dependency_manager = dependency_manager

        def get_option(name):
            return self._get_config_option(name, dependency_manager, config_prefix="conda", **kwds)

        # Conda context options (these define the environment)
        conda_prefix = get_option("prefix")
        if conda_prefix is None:
            conda_prefix = os.path.join(
                dependency_manager.default_base_path, DEFAULT_BASE_PATH_DIRECTORY
            )

        self.conda_prefix_parent = os.path.dirname(conda_prefix)

        # warning is related to conda problem discussed in https://github.com/galaxyproject/galaxy/issues/2537, remove when that is resolved
        conda_prefix_warning_length = 50
        if len(conda_prefix) >= conda_prefix_warning_length:
            log.warning("Conda install prefix '%s' is %d characters long, this can cause problems with package installation, consider setting a shorter prefix (conda_prefix in galaxy.ini)" % (conda_prefix, len(conda_prefix)))

        condarc_override = get_option("condarc_override")
        if condarc_override is None:
            condarc_override = os.path.join(
                dependency_manager.default_base_path, DEFAULT_CONDARC_OVERRIDE
            )

        conda_exec = get_option("exec")
        debug = _string_as_bool(get_option("debug"))
        verbose_install_check = _string_as_bool(get_option("verbose_install_check"))
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
        auto_install = _string_as_bool(get_option("auto_install"))
        copy_dependencies = _string_as_bool(get_option("copy_dependencies"))
        self.auto_init = _string_as_bool(get_option("auto_init"))
        self.conda_context = conda_context
        self.disabled = not galaxy.tools.deps.installable.ensure_installed(conda_context, install_conda, self.auto_init)
        self.auto_install = auto_install
        self.copy_dependencies = copy_dependencies
        self.verbose_install_check = verbose_install_check

    def resolve(self, name, version, type, **kwds):
        # Check for conda just not being there, this way we can enable
        # conda by default and just do nothing in not configured.
        if not os.path.isdir(self.conda_context.conda_prefix):
            return NullDependency(version=version, name=name)

        if type != "package":
            return NullDependency(version=version, name=name)

        exact = not self.versionless or version is None
        if self.versionless:
            version = None

        conda_target = CondaTarget(name, version=version)
        is_installed = is_conda_target_installed(
            conda_target, conda_context=self.conda_context, verbose_install_check=self.verbose_install_check
        )

        job_directory = kwds.get("job_directory", None)
        if job_directory is None:  # Job directory is None when resolve() called by find_dep()
            if is_installed:
                return CondaDependency(
                    False,
                    os.path.join(self.conda_context.envs_path, conda_target.install_environment),
                    exact,
                    name=name,
                    version=version
                )
            else:
                log.warning("Conda dependency resolver not sent job directory.")
                return NullDependency(version=version, name=name)

        if not is_installed and self.auto_install:
            is_installed = self.install_dependency(name=name, version=version, type=type)

        if not is_installed:
            return NullDependency(version=version, name=name)

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
            return CondaDependency(
                self.conda_context.activate,
                conda_environment,
                exact,
                name,
                version
            )
        else:
            if len(conda_environment) > 79:
                # TODO: remove this once conda_build version 2 is released and packages have been rebuilt.
                raise Exception("Conda dependency failed to build job environment. "
                                "This is most likely a limitation in conda. "
                                "You can try to shorten the path to the job_working_directory.")
            raise Exception("Conda dependency seemingly installed but failed to build job environment.")

    def list_dependencies(self):
        for install_target in installed_conda_targets(self.conda_context):
            name = install_target.package
            version = install_target.version
            yield self._to_requirement(name, version)

    def install_dependency(self, name, version, type, **kwds):
        "Returns True on (seemingly) successfull installation"
        if type != "package":
            log.warning("Cannot install dependencies of type '%s'" % type)
            return False

        if self.versionless:
            version = None

        conda_target = CondaTarget(name, version=version)

        is_installed = is_conda_target_installed(
            conda_target, conda_context=self.conda_context, verbose_install_check=self.verbose_install_check
        )

        if is_installed:
            return is_installed

        return_code = install_conda_target(conda_target, conda_context=self.conda_context)
        if return_code != 0:
            is_installed = False
        else:
            # Recheck if installed
            is_installed = is_conda_target_installed(
                conda_target, conda_context=self.conda_context, verbose_install_check=self.verbose_install_check
            )
        if not is_installed:
            log.debug("Removing failed conda install of {}, version '{}'".format(name, version))
            cleanup_failed_install(conda_target, conda_context=self.conda_context)

        return is_installed

    @property
    def prefix(self):
        return self.conda_context.conda_prefix


class CondaDependency(Dependency):
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + ['environment_path', 'name', 'version']
    dependency_type = 'conda'

    def __init__(self, activate, environment_path, exact, name=None, version=None):
        self.activate = activate
        self.environment_path = environment_path
        self._exact = exact
        self._name = name
        self._version = version

    @property
    def exact(self):
        return self._exact

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    def shell_commands(self, requirement):
        return """[ "$CONDA_DEFAULT_ENV" = "%s" ] || . %s '%s' 2>&1 """ % (
            self.environment_path,
            self.activate,
            self.environment_path
        )


def _string_as_bool( value ):
    return str( value ).lower() == "true"


__all__ = ['CondaDependencyResolver']
