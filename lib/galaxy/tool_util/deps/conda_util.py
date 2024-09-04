import functools
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import sys
import tempfile
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
    Union,
)

from packaging.version import Version

from galaxy.tool_util.version import parse_version
from galaxy.util import (
    commands,
    download_to_file,
    listify,
    shlex_join,
    smart_str,
    which,
)
from . import installable

if TYPE_CHECKING:
    from galaxy.tool_util.deps.requirements import ToolRequirement

log = logging.getLogger(__name__)

# Not sure there are security concerns, lets just fail fast if we are going
# break shell commands we are building.
SHELL_UNSAFE_PATTERN = re.compile(r"[\s\"']")

IS_OS_X = sys.platform == "darwin"

VERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@(.*)")
UNVERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@_uv_")
USE_PATH_EXEC_DEFAULT = False
CONDA_PACKAGE_SPECS = ("conda>=23.7.0", "conda-libmamba-solver", "'pyopenssl>=22.1.0'")
CONDA_BUILD_SPECS = ("conda-build>=3.22.0",)
USE_LOCAL_DEFAULT = False


def conda_link() -> str:
    if IS_OS_X:
        if "arm64" in platform.platform():
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
        else:
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
    else:
        if "arm64" in platform.platform():
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-aarch64.sh"
        else:
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
    return url


def find_conda_prefix() -> str:
    """If supplied conda_prefix is not set, default to the default location
    for Miniconda installs.
    """
    home = os.path.expanduser("~")
    destinations = ["miniforge3", "miniconda3", "miniconda2", "anaconda3", "anaconda2"]
    for destination in destinations:
        destination = os.path.join(home, destination)
        if os.path.exists(destination):
            return destination
    return os.path.join(home, "miniforge3")


class CondaContext(installable.InstallableContext):
    installable_description = "Conda"
    _conda_build_available: Optional[bool]
    _conda_version: Optional[Version]
    _libmamba_solver_available: Optional[bool]

    def __init__(
        self,
        conda_prefix: Optional[str] = None,
        conda_exec: Optional[str] = None,
        shell_exec: Optional[Callable[..., int]] = None,
        debug: bool = False,
        ensure_channels: Union[str, List[str]] = "",
        condarc_override: Optional[str] = None,
        use_path_exec: bool = USE_PATH_EXEC_DEFAULT,
        copy_dependencies: bool = False,
        use_local: bool = USE_LOCAL_DEFAULT,
    ) -> None:
        self.condarc_override = condarc_override
        if not conda_exec and use_path_exec:
            conda_exec = which("conda")
        if conda_exec and isinstance(conda_exec, str):
            conda_exec = os.path.normpath(conda_exec)
        self.debug = debug
        self.shell_exec = shell_exec or commands.shell
        self.copy_dependencies = copy_dependencies

        if conda_exec is not None:
            self.conda_exec = conda_exec
            if conda_prefix is None:
                info = self.conda_info()
                conda_prefix = info.get("default_prefix")
        if conda_prefix is None:
            conda_prefix = find_conda_prefix()

        self.conda_prefix = conda_prefix
        if conda_exec is None:
            self.conda_exec = self._bin("conda")
        self.ensure_channels: List[str] = listify(ensure_channels)
        self.use_local = use_local
        self._reset_conda_properties()

    def _reset_conda_properties(self) -> None:
        self._conda_version = None
        self._conda_build_available = None
        self._libmamba_solver_available = None

    @property
    def conda_version(self) -> Version:
        if self._conda_version is None:
            self._guess_conda_properties()
        assert isinstance(self._conda_version, Version)
        return self._conda_version

    @property
    def conda_build_available(self) -> bool:
        if self._conda_build_available is None:
            self._guess_conda_properties()
        assert isinstance(self._conda_build_available, bool)
        return self._conda_build_available

    def _guess_conda_properties(self) -> None:
        info = self.conda_info()
        self._conda_version = Version(info["conda_version"])
        self._conda_build_available = False
        conda_build_version = info.get("conda_build_version")
        if conda_build_version and conda_build_version != "not installed":
            try:
                Version(conda_build_version)
                self._conda_build_available = True
            except Exception:
                pass

    @property
    def _override_channels_args(self) -> List[str]:
        override_channels_args = []
        if self.ensure_channels:
            override_channels_args.append("--override-channels")
            for channel in self.ensure_channels:
                override_channels_args.extend(["--channel", channel])
        return override_channels_args

    @property
    def _solver_args(self) -> List[str]:
        if self._libmamba_solver_available is None:
            self._libmamba_solver_available = self.conda_version >= Version("4.12.0") and self.is_package_installed(
                "conda-libmamba-solver"
            )
        if self._libmamba_solver_available:
            # The "--solver" option was introduced in conda 22.11.0, when the
            # "--experimental-solver" option was deprecated.
            # The "--experimental-solver" option was removed in conda 23.9.0 .
            solver_option = "--solver" if self.conda_version >= Version("22.11.0") else "--experimental-solver"
            return [solver_option, "libmamba"]
        else:
            return []

    def ensure_conda_build_installed_if_needed(self) -> int:
        if self.use_local and not self.conda_build_available:
            # Cannot use --use-local during installation of conda-build.
            return self.exec_install(CONDA_BUILD_SPECS, allow_local=False)
        else:
            return 0

    def conda_info(self) -> Dict[str, Any]:
        cmd = listify(self.conda_exec) + ["info", "--json"]
        info_out = commands.execute(cmd)
        info = json.loads(info_out)
        return info

    def is_conda_installed(self) -> bool:
        """
        Check if conda_exec exists
        """
        if os.path.exists(self.conda_exec):
            return True
        else:
            return False

    def can_install_conda(self) -> bool:
        """
        If conda_exec is set to a path outside of conda_prefix,
        there is no use installing conda into conda_prefix, since it can't be used by galaxy.
        If conda_exec equals conda_prefix/bin/conda, we can install conda if either conda_prefix
        does not exist or is empty.
        """
        conda_exec = os.path.abspath(self.conda_exec)
        conda_prefix_plus_exec = os.path.abspath(os.path.join(self.conda_prefix, "bin/conda"))
        if conda_exec == conda_prefix_plus_exec:
            if not os.path.exists(self.conda_prefix):
                return True
            elif os.listdir(self.conda_prefix) == []:
                os.rmdir(self.conda_prefix)  # Conda's install script fails if path exists (even if empty).
                return True
            else:
                log.warning(
                    "Cannot install Conda because conda_prefix '%s' exists and is not empty.", self.conda_prefix
                )
                return False
        else:
            log.warning(
                "Skipping installation of Conda into conda_prefix '%s', "
                "since conda_exec '%s' is set to a path outside of conda_prefix.",
                self.conda_prefix,
                self.conda_exec,
            )
            return False

    def exec_command(self, operation: str, args: List[str], stdout_path: Optional[str] = None) -> int:
        """
        Execute the requested command.

        Return the process exit code (i.e. 0 in case of success).
        """
        cmd = listify(self.conda_exec) + operation.split()
        if self.debug:
            cmd.append("--debug")
        cmd.extend(args)
        env = {}
        if self.condarc_override:
            env["CONDARC"] = self.condarc_override
        cmd_string = shlex_join(cmd)
        kwds: Dict[str, Any] = {}
        try:
            if stdout_path:
                kwds["stdout"] = open(stdout_path, "w")
                cmd_string += f" > '{stdout_path}'"
            conda_exec_home = env["HOME"] = tempfile.mkdtemp(
                prefix="conda_exec_home_"
            )  # We don't want to pollute ~/.conda, which may not even be writable
            log.debug("Executing command: %s", cmd_string)
            return self.shell_exec(cmd, env=env, **kwds)
        except Exception:
            log.exception("Failed to execute command: %s", cmd_string)
            return 1
        finally:
            if kwds.get("stdout"):
                kwds["stdout"].close()
            if conda_exec_home:
                shutil.rmtree(conda_exec_home, ignore_errors=True)

    def is_package_installed(self, pkg_name: str, version: Optional[str] = None) -> bool:
        list_args = ["-f", "--json", pkg_name]
        with tempfile.NamedTemporaryFile("r") as temp:
            ret = self.exec_command("list", list_args, stdout_path=temp.name)
            if ret != 0:
                log.error("Failed to execute 'conda list'")
                return False
            out = json.load(temp)
        if not out:
            return False
        if not version:
            return True
        return any(match["version"] == version for match in out)

    def exec_create(self, args: Iterable[str], allow_local: bool = True, stdout_path: Optional[str] = None) -> int:
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        for try_strict in [True, False]:
            create_args = ["-y", "--quiet"]
            if try_strict:
                if self.conda_version >= Version("4.7.5"):
                    create_args.append("--strict-channel-priority")
                else:
                    continue
            if allow_local and self.use_local:
                create_args.append("--use-local")
            create_args.extend(self._solver_args)
            create_args.extend(self._override_channels_args)
            create_args.extend(args)
            ret = self.exec_command("create", create_args, stdout_path=stdout_path)
            if ret == 0:
                break
        return ret

    def exec_remove(self, args: List[str]) -> int:
        """
        Remove a conda environment using conda env remove -y --name `args`.

        Return the process exit code (i.e. 0 in case of success).
        """
        remove_args = ["-y", "--name"]
        remove_args.extend(args)
        return self.exec_command("env remove", remove_args)

    def exec_install(self, args: Iterable[str], allow_local: bool = True, stdout_path: Optional[str] = None) -> int:
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        for try_strict in [True, False]:
            install_args = ["-y"]
            if try_strict:
                if self.conda_version >= Version("4.7.5"):
                    install_args.append("--strict-channel-priority")
                else:
                    continue
            if allow_local and self.use_local:
                install_args.append("--use-local")
            install_args.extend(self._solver_args)
            install_args.extend(self._override_channels_args)
            install_args.extend(args)
            ret = self.exec_command("install", install_args, stdout_path=stdout_path)
            if ret == 0:
                break
        if ret == 0:
            self._reset_conda_properties()
        return ret

    def exec_clean(self, args: Optional[List[str]] = None, quiet: bool = False) -> int:
        """
        Clean up after conda installation.

        Return the process exit code (i.e. 0 in case of success).
        """
        clean_args = ["--tarballs", "-y"]
        if args:
            clean_args.extend(args)
        stdout_path = None
        if quiet:
            stdout_path = "/dev/null"
        return self.exec_command("clean", clean_args, stdout_path=stdout_path)

    def exec_search(
        self, args: List[str], json: bool = False, offline: bool = False, platform: Optional[str] = None
    ) -> str:
        """
        Search conda channels for a package

        Return the standard output of the conda process.
        """
        cmd = listify(self.conda_exec)[:]
        cmd.append("search")
        cmd.extend(self._override_channels_args)
        if json:
            cmd.append("--json")
        if offline:
            cmd.append("--offline")
        if platform:
            cmd.extend(["--platform", platform])
        cmd.extend(args)
        return commands.execute(cmd)

    def export_list(self, name: str, path: str) -> int:
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        return self.exec_command("list", ["--name", name, "--export"], stdout_path=path)

    def env_path(self, env_name: str) -> str:
        return os.path.join(self.envs_path, env_name)

    @property
    def envs_path(self) -> str:
        return os.path.join(self.conda_prefix, "envs")

    def has_env(self, env_name: str) -> bool:
        env_path = self.env_path(env_name)
        return os.path.isdir(env_path)

    def get_conda_target_installed_path(self, conda_target: "CondaTarget") -> Optional[str]:
        for env_name in (conda_target.install_environment, conda_target.capitalized_install_environment):
            if self.has_env(env_name):
                return self.env_path(env_name)
        return None

    @property
    def deactivate(self) -> str:
        return self._bin("deactivate")

    @property
    def activate(self) -> str:
        return self._bin("activate")

    def is_installed(self) -> bool:
        return self.is_conda_installed()

    def can_install(self) -> bool:
        return self.can_install_conda()

    @property
    def parent_path(self) -> str:
        return os.path.dirname(os.path.abspath(self.conda_prefix))

    def _bin(self, name: str) -> str:
        return os.path.join(self.conda_prefix, "bin", name)


def installed_conda_targets(conda_context: CondaContext) -> Iterator["CondaTarget"]:
    envs_path = conda_context.envs_path
    dir_contents = os.listdir(envs_path) if os.path.exists(envs_path) else []
    for name in dir_contents:
        versioned_match = VERSIONED_ENV_DIR_NAME.match(name)
        if versioned_match:
            yield CondaTarget(versioned_match.group(1), version=versioned_match.group(2))

        unversioned_match = UNVERSIONED_ENV_DIR_NAME.match(name)
        if unversioned_match:
            yield CondaTarget(unversioned_match.group(1))


class CondaTarget:
    def __init__(
        self, package: str, version: Optional[str] = None, build: Optional[str] = None, channel: Optional[str] = None
    ) -> None:
        if SHELL_UNSAFE_PATTERN.search(package) is not None:
            raise ValueError(f"Invalid package [{package}] encountered.")
        self.capitalized_package = package
        self.package = package.lower()
        if version and SHELL_UNSAFE_PATTERN.search(version) is not None:
            raise ValueError(f"Invalid version [{version}] encountered.")
        self.version = version
        if build is not None and SHELL_UNSAFE_PATTERN.search(build) is not None:
            raise ValueError(f"Invalid build [{build}] encountered.")
        self.build = build
        if channel and SHELL_UNSAFE_PATTERN.search(channel) is not None:
            raise ValueError(f"Invalid version [{channel}] encountered.")
        self.channel = channel

    def __str__(self) -> str:
        attributes = f"package={self.package}"
        if self.version is not None:
            attributes += f",version={self.version}"
        if self.build is not None:
            attributes += f",build={self.build}"

        if self.channel:
            attributes += f",channel={self.channel}"

        return f"CondaTarget[{attributes}]"

    __repr__ = __str__

    @property
    def package_specifier(self) -> str:
        """Return a package specifier as consumed by conda install/create."""
        if self.version:
            spec = f"{self.package}={self.version}"
        else:
            spec = f"{self.package}=*"
        if self.build:
            spec += f"={self.build}"
        return spec

    @property
    def install_environment(self) -> str:
        """The dependency resolution and installation frameworks will
        expect each target to be installed it its own environment with
        a fixed and predictable name given package and version.
        Since Galaxy 23.1 the package name is lowercased as all Conda package
        names must be lowercase.
        """
        if self.version:
            return f"__{self.package}@{self.version}"
        else:
            return f"__{self.package}@_uv_"

    @property
    def capitalized_install_environment(self) -> str:
        """Same as install_environment() but using the original capitalized
        package name for backward compatibility with environments created before
        Galaxy 23.1 .
        """
        if self.version:
            return f"__{self.capitalized_package}@{self.version}"
        else:
            return f"__{self.capitalized_package}@_uv_"

    def __hash__(self) -> int:
        return hash((self.package, self.version, self.build, self.channel))

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, self.__class__):
            return (self.package, self.version, self.build, self.channel) == (
                other.package,
                other.version,
                other.build,
                other.channel,
            )
        return False


def hash_conda_packages(conda_packages: Iterable[CondaTarget], capitalized_package_names: bool = False) -> str:
    """Produce a unique hash on supplied packages.
    TODO: Ideally we would do this in such a way that preserved environments.
    """
    h = hashlib.new("sha256")
    for conda_package in conda_packages:
        h.update(
            smart_str(
                conda_package.capitalized_install_environment
                if capitalized_package_names
                else conda_package.install_environment
            )
        )
    return h.hexdigest()


# shell makes sense for planemo, in Galaxy this should just execute
# these commands as Python
def install_conda(conda_context: CondaContext, force_conda_build: bool = False) -> int:
    with tempfile.NamedTemporaryFile(suffix=".sh", prefix="conda_install", delete=False) as temp:
        script_path = temp.name
    install_cmd = ["bash", script_path, "-b", "-p", conda_context.conda_prefix]
    package_targets = list(CONDA_PACKAGE_SPECS)
    if force_conda_build or conda_context.use_local:
        package_targets.extend(CONDA_BUILD_SPECS)
    log.info("Installing conda, this may take several minutes.")
    try:
        download_to_file(conda_link(), script_path)
        exit_code = conda_context.shell_exec(install_cmd)
    except Exception:
        log.exception("Failed to install conda")
        return 1
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)
    if exit_code:
        return exit_code
    return conda_context.exec_install(package_targets, allow_local=False)


def install_conda_targets(
    conda_targets: Iterable[CondaTarget],
    conda_context: CondaContext,
    env_name: Optional[str] = None,
    allow_local: bool = True,
) -> int:
    """
    Return the process exit code (i.e. 0 in case of success).
    """
    if env_name is not None:
        create_args = [
            "--name",
            env_name,  # environment for package
        ]
        for conda_target in conda_targets:
            create_args.append(conda_target.package_specifier)
        return conda_context.exec_create(create_args, allow_local=allow_local)
    else:
        return conda_context.exec_install([t.package_specifier for t in conda_targets], allow_local=allow_local)


def install_conda_target(conda_target: CondaTarget, conda_context: CondaContext, skip_environment: bool = False) -> int:
    """
    Install specified target into a its own environment.

    Return the process exit code (i.e. 0 in case of success).
    """
    if not skip_environment:
        create_args = [
            "--name",
            conda_target.install_environment,  # environment for package
            conda_target.package_specifier,
        ]
        return conda_context.exec_create(create_args)
    else:
        return conda_context.exec_install([conda_target.package_specifier])


def cleanup_failed_install_of_environment(env: str, conda_context: CondaContext) -> int:
    if conda_context.has_env(env):
        return conda_context.exec_remove([env])
    return 0


def cleanup_failed_install(conda_target: CondaTarget, conda_context: CondaContext) -> int:
    return cleanup_failed_install_of_environment(conda_target.install_environment, conda_context=conda_context)


def best_search_result(
    conda_target: CondaTarget, conda_context: CondaContext, offline: bool = False, platform: Optional[str] = None
) -> Union[Tuple[None, None], Tuple[Dict[str, Any], bool]]:
    """Find best "conda search" result for specified target.

    Return (``None``, ``None``) if no results match.
    """
    # Cannot specify the version here (i.e. conda_target.package_specifier)
    # because if the version is not found, the exec_search() call would fail.
    search_args = [conda_target.package]
    try:
        res = conda_context.exec_search(search_args, json=True, offline=offline, platform=platform)
        # Use python's stable list sorting to sort by date,
        # then build_number, then version. The top of the list
        # then is the newest version with the newest build and
        # the latest update time.
        hits = json.loads(res).get(conda_target.package, [])[::-1]
        hits = sorted(hits, key=lambda hit: hit["build_number"], reverse=True)
        hits = sorted(hits, key=lambda hit: parse_version(hit["version"]), reverse=True)
    except commands.CommandLineException as e:
        log.error(f"Could not execute: '{e.command}'\n{e}")
        hits = []

    if len(hits) == 0:
        return (None, None)

    best_result = (hits[0], False)

    for hit in hits:
        if is_search_hit_exact(conda_target, hit):
            best_result = (hit, True)
            break

    return best_result


def is_search_hit_exact(conda_target: CondaTarget, search_hit: Dict[str, Any]) -> bool:
    # It'd be nice to make request verson of 1.0 match available
    # version of 1.0.3 or something like that.
    target_version = conda_target.version
    if target_version and search_hit["version"] != target_version:
        return False
    target_build = conda_target.build
    if target_build and search_hit["build"] != target_build:
        return False
    return True


def is_conda_target_installed(conda_target: CondaTarget, conda_context: CondaContext) -> bool:
    return conda_context.get_conda_target_installed_path(conda_target) is not None


def filter_installed_targets(conda_targets: Iterable[CondaTarget], conda_context: CondaContext) -> List[CondaTarget]:
    installed = functools.partial(is_conda_target_installed, conda_context=conda_context)
    return list(filter(installed, conda_targets))


def build_isolated_environment(
    conda_packages: Union[CondaTarget, List[CondaTarget]],
    conda_context: CondaContext,
    path: Optional[str] = None,
    copy: bool = False,
    quiet: bool = False,
) -> Tuple[str, int]:
    """Build a new environment (or reuse an existing one from hashes)
    for specified conda packages.
    """
    if not isinstance(conda_packages, list):
        conda_packages = [conda_packages]

    # Lots we could do in here, hashing, checking revisions, etc...
    tempdir = None
    try:
        hash = hash_conda_packages(conda_packages)
        tempdir = tempfile.mkdtemp(prefix="jobdeps", suffix=hash)
        tempdir_name = os.path.basename(tempdir)

        export_paths = []
        for conda_package in conda_packages:
            name = conda_package.install_environment
            export_path = os.path.join(tempdir, name)
            conda_context.export_list(name, export_path)
            export_paths.append(export_path)
        create_args = ["--unknown"]
        # Works in 3.19, 4.0 - 4.2 - not in 4.3.
        # Adjust fix if they fix Conda - xref
        # - https://github.com/galaxyproject/galaxy/issues/3635
        # - https://github.com/conda/conda/issues/2035
        offline_works = (conda_context.conda_version < Version("4.3")) or (
            conda_context.conda_version >= Version("4.4")
        )
        if offline_works:
            create_args.append("--offline")
        else:
            create_args.append("--use-index-cache")
        if path is None:
            create_args.extend(["--name", tempdir_name])
        else:
            create_args.extend(["--prefix", path])

        if copy:
            create_args.append("--copy")
        for export_path in export_paths:
            create_args.extend(["--file", export_path])

        stdout_path = None
        if quiet:
            stdout_path = "/dev/null"

        if path is not None and os.path.exists(path):
            exit_code = conda_context.exec_install(create_args, stdout_path=stdout_path)
        else:
            exit_code = conda_context.exec_create(create_args, stdout_path=stdout_path)

        return (path or tempdir_name, exit_code)
    finally:
        conda_context.exec_clean(quiet=quiet)
        if tempdir is not None:
            shutil.rmtree(tempdir)


def requirement_to_conda_targets(requirement: "ToolRequirement") -> Optional[CondaTarget]:
    conda_target = None
    if requirement.type == "package":
        assert requirement.name
        conda_target = CondaTarget(requirement.name, version=requirement.version)
    return conda_target


def requirements_to_conda_targets(requirements: Iterable["ToolRequirement"]) -> List[CondaTarget]:
    conda_targets = (requirement_to_conda_targets(_) for _ in requirements)
    return [c for c in conda_targets if c is not None]


__all__ = (
    "CondaContext",
    "CondaTarget",
    "install_conda",
    "install_conda_target",
    "requirements_to_conda_targets",
)
