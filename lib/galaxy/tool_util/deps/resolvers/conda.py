"""
This is still an experimental module and there will almost certainly be backward
incompatible changes coming.
"""

import logging
import os
import re
from typing import (
    List,
    Optional,
)

import galaxy.tool_util.deps.installable
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from . import (
    Dependency,
    DependencyException,
    DependencyResolver,
    ListableDependencyResolver,
    MappableDependencyResolver,
    MultipleDependencyResolver,
    NullDependency,
    SpecificationPatternDependencyResolver,
)
from ..conda_util import (
    build_isolated_environment,
    cleanup_failed_install,
    cleanup_failed_install_of_environment,
    CondaContext,
    CondaTarget,
    hash_conda_packages,
    install_conda,
    install_conda_target,
    install_conda_targets,
    installed_conda_targets,
    is_conda_target_installed,
    USE_PATH_EXEC_DEFAULT,
)

DEFAULT_BASE_PATH_DIRECTORY = "_conda"
DEFAULT_CONDARC_OVERRIDE = "_condarc"
# Conda channel order from highest to lowest, following the one used in
# https://github.com/bioconda/bioconda-recipes/blob/master/config.yml
DEFAULT_ENSURE_CHANNELS = "conda-forge,bioconda"
CONDA_SOURCE_CMD = """[ "$(basename "$CONDA_DEFAULT_ENV")" = "$(basename '{environment_path}')" ] || {{
MAX_TRIES=3
COUNT=0
while [ $COUNT -lt $MAX_TRIES ]; do
    . '{activate_path}' '{environment_path}' > conda_activate.log 2>&1
    if [ $? -eq 0 ];then
        break
    else
        let COUNT=COUNT+1
        if [ $COUNT -eq $MAX_TRIES ];then
            echo "Failed to activate conda environment! Error was:"
            cat conda_activate.log
            exit 1
        fi
        sleep 10s
    fi
done
}} """


log = logging.getLogger(__name__)


class CondaDependencyResolver(
    DependencyResolver,
    MultipleDependencyResolver,
    ListableDependencyResolver,
    SpecificationPatternDependencyResolver,
    MappableDependencyResolver,
):
    dict_collection_visible_keys = DependencyResolver.dict_collection_visible_keys + [
        "prefix",
        "versionless",
        "ensure_channels",
        "auto_install",
        "auto_init",
        "use_local",
    ]
    resolver_type = "conda"
    config_options = {
        "prefix": None,
        "exec": None,
        "debug": None,
        "ensure_channels": DEFAULT_ENSURE_CHANNELS,
        "auto_install": False,
        "auto_init": True,
        "copy_dependencies": False,
        "use_local": False,
    }
    _specification_pattern = re.compile(r"https\:\/\/anaconda.org\/\w+\/\w+")

    def __init__(self, dependency_manager, **kwds):
        read_only = _string_as_bool(kwds.get("read_only", "false"))
        self.read_only = read_only
        self._setup_mapping(dependency_manager, **kwds)
        self.versionless = _string_as_bool(kwds.get("versionless", "false"))
        self.dependency_manager = dependency_manager

        def get_option(name):
            return dependency_manager.get_resolver_option(self, name, explicit_resolver_options=kwds)

        # Conda context options (these define the environment)
        conda_prefix = get_option("prefix")
        if conda_prefix is None:
            conda_prefix = os.path.join(dependency_manager.default_base_path, DEFAULT_BASE_PATH_DIRECTORY)
        conda_prefix = os.path.abspath(conda_prefix)

        self.conda_prefix_parent = os.path.dirname(conda_prefix)

        condarc_override = get_option("condarc_override")
        if condarc_override is None:
            condarc_override = os.path.join(dependency_manager.default_base_path, DEFAULT_CONDARC_OVERRIDE)

        copy_dependencies = _string_as_bool(get_option("copy_dependencies"))
        use_local = _string_as_bool(get_option("use_local"))
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
            copy_dependencies=copy_dependencies,
            use_local=use_local,
        )
        self.use_local = use_local
        self.ensure_channels = ensure_channels

        # Conda operations options (these define how resolution will occur)
        auto_install = _string_as_bool(get_option("auto_install"))
        self.auto_init = _string_as_bool(get_option("auto_init"))
        self.conda_context = conda_context
        self.disabled = not galaxy.tool_util.deps.installable.ensure_installed(
            conda_context, install_conda, self.auto_init
        )
        if self.auto_init and not self.disabled:
            self.conda_context.ensure_conda_build_installed_if_needed()
        self.auto_install = auto_install
        self.copy_dependencies = copy_dependencies

    def clean(self, **kwds):
        return self.conda_context.exec_clean()

    def uninstall(self, requirements):
        """Uninstall requirements installed by install_all or multiple install statements."""
        all_resolved = [r for r in self.resolve_all(requirements) if r.dependency_type]
        if not all_resolved:
            all_resolved = [self.resolve(requirement) for requirement in requirements]
            all_resolved = [r for r in all_resolved if r.dependency_type]
        if not all_resolved:
            return None
        environments = {os.path.basename(dependency.environment_path) for dependency in all_resolved}
        return self.uninstall_environments(environments)

    def uninstall_environments(self, environments):
        environments = [
            env if not env.startswith(self.conda_context.envs_path) else os.path.basename(env) for env in environments
        ]
        return_codes = [self.conda_context.exec_remove([env]) for env in environments]
        final_return_code = 0
        for env, return_code in zip(environments, return_codes):
            if return_code == 0:
                log.debug(f"Conda environment '{env}' successfully removed.")
            else:
                log.debug(f"Conda environment '{env}' could not be removed.")
                final_return_code = return_code
        return final_return_code

    def install_all(self, conda_targets: List[CondaTarget], env: str) -> bool:
        if self.read_only:
            return False

        return_code = install_conda_targets(conda_targets, conda_context=self.conda_context, env_name=env)
        if return_code != 0:
            is_installed = False
        else:
            # Recheck if installed
            is_installed = self.conda_context.has_env(env)

        if not is_installed:
            log.debug(f"Removing failed conda install of {str(conda_targets)}")
            cleanup_failed_install_of_environment(env, conda_context=self.conda_context)

        return is_installed

    def resolve_all(self, requirements: ToolRequirements, **kwds) -> List[Dependency]:
        """
        Some combinations of tool requirements need to be resolved all at once, so that Conda can select a compatible
        combination of dependencies. This method returns a list of MergedCondaDependency instances (one for each requirement)
        if all requirements have been successfully resolved, or an empty list if any of the requirements could not be resolved.

        Parameters specific to this resolver are:

            preserve_python_environment: Boolean, controls whether the python environment should be maintained during job creation for tools
                                         that rely on galaxy being importable.

            install:                     Controls if `requirements` should be installed. If `install` is True and the requirements are not installed
                                         an attempt is made to install the requirements. If `install` is None requirements will only be installed if
                                         `conda_auto_install` has been activated and the requirements are not yet installed. If `install` is
                                         False will not install requirements.
        """
        if len(requirements) == 0:
            return []

        if not os.path.isdir(self.conda_context.conda_prefix):
            return []

        for requirement in requirements:
            if requirement.type != "package":
                return []

        expanded_requirements = ToolRequirements([self._expand_requirement(r) for r in requirements])
        if self.versionless:
            conda_targets = [CondaTarget(r.name, version=None) for r in expanded_requirements]
        else:
            conda_targets = [CondaTarget(r.name, version=r.version) for r in expanded_requirements]

        preserve_python_environment = kwds.get("preserve_python_environment", False)

        for capitalized_package_names in (True, False):
            env = self.merged_environment_name(conda_targets, capitalized_package_names)
            is_installed = self.conda_context.has_env(env)
            if is_installed:
                break

        install = kwds.get("install", None)
        if install is None:
            # Default behavior, install dependencies if conda_auto_install is active.
            install = not is_installed and self.auto_install
        elif install:
            # Install has been set to True, install if not yet installed.
            install = not is_installed
        if install:
            is_installed = self.install_all(conda_targets, env)

        dependencies: List[Dependency] = []
        if is_installed:
            for requirement in requirements:
                dependency = MergedCondaDependency(
                    self.conda_context,
                    self.conda_context.env_path(env),
                    exact=not self.versionless or requirement.version is None,
                    name=requirement.name,
                    version=requirement.version,
                    preserve_python_environment=preserve_python_environment,
                    dependency_resolver=self,
                )
                dependencies.append(dependency)

        return dependencies

    def merged_environment_name(self, conda_targets: List[CondaTarget], capitalized_package_names: bool = False) -> str:
        if len(conda_targets) > 1:
            # For continuity with mulled containers this is kind of nice.
            return f"mulled-v1-{hash_conda_packages(conda_targets, capitalized_package_names)}"
        else:
            assert len(conda_targets) == 1
            return conda_targets[0].install_environment

    def resolve(self, requirement: ToolRequirement, **kwds) -> Dependency:
        requirement = self._expand_requirement(requirement)
        name, version, type = requirement.name, requirement.version, requirement.type

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
        is_installed = is_conda_target_installed(conda_target, conda_context=self.conda_context)

        preserve_python_environment = kwds.get("preserve_python_environment", False)

        job_directory = kwds.get("job_directory", None)
        install = kwds.get("install", None)
        if install is None:
            install = not is_installed and self.auto_install
        elif install:
            install = not is_installed
        if install:
            is_installed = self.install_dependency(name=name, version=version, type=type)

        if not is_installed:
            return NullDependency(version=version, name=name)

        # Have installed conda_target and job_directory to send it to.
        # If dependency is for metadata generation, store environment in conda-metadata-env
        if kwds.get("metadata", False):
            conda_env = "conda-metadata-env"
        else:
            conda_env = "conda-env"

        if job_directory:
            conda_environment = os.path.join(job_directory, conda_env)
        else:
            conda_environment = self.conda_context.get_conda_target_installed_path(conda_target)

        return CondaDependency(
            self.conda_context,
            conda_environment,
            exact,
            name,
            version,
            preserve_python_environment=preserve_python_environment,
            dependency_resolver=self,
        )

    def _expand_requirement(self, requirement):
        return self._expand_specs(self._expand_mappings(requirement))

    def unused_dependency_paths(self, toolbox_requirements_status):
        """
        Identify all local environments that are not needed to build requirements_status.

        We try to resolve the requirements, and we note every environment_path that has been taken.
        """
        used_paths = set()
        for dependencies in toolbox_requirements_status.values():
            for dependency in dependencies:
                if dependency.get("dependency_type") == "conda":
                    path = os.path.basename(dependency["environment_path"])
                    used_paths.add(path)
        dir_contents = set(
            os.listdir(self.conda_context.envs_path) if os.path.exists(self.conda_context.envs_path) else []
        )
        # never delete Galaxy's conda env
        used_paths.add("_galaxy_")
        unused_paths = dir_contents.difference(used_paths)  # New set with paths in dir_contents but not in used_paths
        unused_paths = [os.path.join(self.conda_context.envs_path, p) for p in unused_paths]
        return unused_paths

    def list_dependencies(self):
        for install_target in installed_conda_targets(self.conda_context):
            name = install_target.package
            version = install_target.version
            yield self._to_requirement(name, version)

    def _install_dependency(self, name, version, type, **kwds):
        "Returns True on (seemingly) successfull installation"
        # should be checked before called
        assert not self.read_only

        if type != "package":
            log.warning(f"Cannot install dependencies of type '{type}'")
            return False

        if self.versionless:
            version = None

        conda_target = CondaTarget(name, version=version)

        is_installed = is_conda_target_installed(conda_target, conda_context=self.conda_context)

        if is_installed:
            return is_installed

        return_code = install_conda_target(conda_target, conda_context=self.conda_context)
        if return_code != 0:
            is_installed = False
        else:
            # Recheck if installed
            is_installed = is_conda_target_installed(conda_target, conda_context=self.conda_context)
        if not is_installed:
            log.debug(f"Removing failed conda install of {name}, version '{version}'")
            cleanup_failed_install(conda_target, conda_context=self.conda_context)

        return is_installed

    @property
    def prefix(self):
        return self.conda_context.conda_prefix


class MergedCondaDependency(Dependency):
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + [
        "environment_path",
        "name",
        "version",
        "dependency_resolver",
    ]
    dependency_type = "conda"

    def __init__(
        self,
        conda_context: CondaContext,
        environment_path: str,
        exact: bool,
        name: str,
        version: Optional[str] = None,
        preserve_python_environment: bool = False,
        dependency_resolver: Optional[DependencyResolver] = None,
    ) -> None:
        self.activate = conda_context.activate
        self.conda_context = conda_context
        self.environment_path = environment_path
        self._exact = exact
        self._name = name
        self._version = version
        self.cache_path = None
        self._preserve_python_environment = preserve_python_environment
        self.dependency_resolver = dependency_resolver

    @property
    def exact(self):
        return self._exact

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    def shell_commands(self):
        if self._preserve_python_environment:
            # On explicit testing the only such requirement I am aware of is samtools - and it seems to work
            # fine with just appending the PATH as done below. Other tools may require additional
            # variables in the future.
            return f"""export PATH=$PATH:'{self.environment_path}/bin' """
        else:
            return CONDA_SOURCE_CMD.format(activate_path=self.activate, environment_path=self.environment_path)


class CondaDependency(Dependency):
    dict_collection_visible_keys = Dependency.dict_collection_visible_keys + [
        "environment_path",
        "name",
        "version",
        "dependency_resolver",
    ]
    dependency_type = "conda"
    cacheable = True

    def __init__(
        self,
        conda_context: CondaContext,
        environment_path: str,
        exact: bool,
        name: str,
        version: Optional[str] = None,
        preserve_python_environment: bool = False,
        dependency_resolver: Optional[DependencyResolver] = None,
    ) -> None:
        self.activate = conda_context.activate
        self.conda_context = conda_context
        self.environment_path = environment_path
        self._exact = exact
        self._name = name
        self._version = version
        self.cache_path = None
        self._preserve_python_environment = preserve_python_environment
        self.dependency_resolver = dependency_resolver

    @property
    def exact(self):
        return self._exact

    @property
    def name(self):
        return self._name

    @property
    def version(self):
        return self._version

    def build_cache(self, cache_path):
        self.set_cache_path(cache_path)
        self.build_environment()

    def set_cache_path(self, cache_path):
        self.cache_path = cache_path
        self.environment_path = cache_path

    def build_environment(self) -> None:
        env_path, exit_code = build_isolated_environment(
            CondaTarget(self.name, version=self.version),
            conda_context=self.conda_context,
            path=self.environment_path,
            copy=self.conda_context.copy_dependencies,
        )
        if exit_code:
            if len(os.path.abspath(self.environment_path)) > 79:
                # TODO: remove this once conda_build version 2 is released and packages have been rebuilt.
                raise DependencyException(
                    "Conda dependency failed to build job environment. "
                    "This is most likely a limitation in conda. "
                    "You can try to shorten the path to the job_working_directory."
                )
            raise DependencyException("Conda dependency seemingly installed but failed to build job environment.")

    def shell_commands(self):
        if not self.cache_path:
            # Build an isolated environment if not using a cached dependency manager
            self.build_environment()
        if self._preserve_python_environment:
            # On explicit testing the only such requirement I am aware of is samtools - and it seems to work
            # fine with just appending the PATH as done below. Other tools may require additional
            # variables in the future.
            return f"""export PATH=$PATH:'{self.environment_path}/bin' """
        else:
            return CONDA_SOURCE_CMD.format(activate_path=self.activate, environment_path=self.environment_path)


def _string_as_bool(value):
    return str(value).lower() == "true"


__all__ = ("CondaDependencyResolver", "DEFAULT_ENSURE_CHANNELS")
