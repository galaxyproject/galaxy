import contextlib
import functools
import glob
import hashlib
import json
import logging
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from collections.abc import (
    Callable,
    Iterable,
    Iterator,
)
from typing import (
    Any,
    TYPE_CHECKING,
)

from packaging.version import Version

from galaxy.tool_util.version import parse_version
from galaxy.util import (
    commands,
    download_to_file,
    listify,
    smart_str,
    which,
)
from galaxy.util.filelock import (
    FileLock,
    FileLockException,
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
CONDA_PACKAGE_SPECS = ("conda>=23.7.0", "conda-libmamba-solver", "pyopenssl>=22.1.0")
CONDA_BUILD_SPECS = ("conda-build>=3.22.0",)
USE_LOCAL_DEFAULT = False
PLATFORMS_DIRECTORY_NAME = "platforms"
PLATFORM_OK_MARKER = ".galaxy-conda-platform-ok"
PLATFORM_LOCK_TIMEOUT = 300
LOCKS_DIRECTORY_NAME = ".locks"
PLATFORM_SUBDIR_PATTERN = re.compile(r"^[a-z0-9]+-[a-z0-9_]+$")
# Virtual package overrides that let conda solve for a platform other than
# the one it is running on.
DEFAULT_PLATFORM_OVERRIDES: dict[str, dict[str, str]] = {
    "linux": {"CONDA_OVERRIDE_GLIBC": "2.17"},
    "osx": {"CONDA_OVERRIDE_OSX": "11.0"},
}


def patched_binary_files(prefix: str) -> list[str]:
    """Existing files under ``prefix`` that conda patched, according to its conda-meta records."""
    files: list[str] = []
    for record_path in sorted(glob.glob(os.path.join(prefix, "conda-meta", "*.json"))):
        try:
            with open(record_path) as fh:
                paths = json.load(fh).get("paths_data", {}).get("paths", [])
        except (OSError, ValueError, AttributeError):
            log.warning("Could not read conda package record '%s'", record_path, exc_info=True)
            continue
        for entry in paths:
            if not isinstance(entry, dict) or entry.get("file_mode") != "binary" or "prefix_placeholder" not in entry:
                continue
            relative = entry.get("_path")
            if not relative:
                continue
            path = os.path.join(prefix, str(relative))
            if os.path.isfile(path) and path not in files:
                files.append(path)
    return files


def parse_platforms(platforms: str | Iterable[str] | None) -> list[str]:
    """Normalize a comma separated string or a list of conda subdirs.

    Invalid entries are dropped with a warning, duplicates are removed
    while keeping the order.
    """
    result: list[str] = []
    items = [platforms] if isinstance(platforms, str) else list(platforms or [])
    for item in items:
        for platform_ in str(item).split(","):
            platform_ = platform_.strip()
            if not platform_:
                continue
            if not PLATFORM_SUBDIR_PATTERN.match(platform_):
                log.warning("Ignoring invalid conda platform '%s'", platform_)
                continue
            if platform_ not in result:
                result.append(platform_)
    return result


def conda_link() -> str:
    arch = platform.machine()
    if IS_OS_X:
        if "arm64" in arch:
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh"
        else:
            url = "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh"
    else:
        if "arm64" in arch or "aarch64" in arch:
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
    _conda_build_available: bool | None
    _conda_version: Version | None
    _libmamba_solver_available: bool | None

    def __init__(
        self,
        conda_prefix: str | None = None,
        conda_exec: str | list[str] | None = None,
        shell_exec: Callable[..., int] | None = None,
        debug: bool = False,
        ensure_channels: str | list[str] = "",
        condarc_override: str | None = None,
        use_path_exec: bool = USE_PATH_EXEC_DEFAULT,
        copy_dependencies: bool = False,
        use_local: bool = USE_LOCAL_DEFAULT,
        platforms: str | list[str] | None = None,
        platform_overrides: dict[str, dict[str, str | None]] | None = None,
        codesign_exec: str | None = None,
    ) -> None:
        self.condarc_override = condarc_override
        if not conda_exec and use_path_exec:
            conda_exec = which("conda")
        if conda_exec and isinstance(conda_exec, str):
            conda_exec = os.path.normpath(conda_exec)
        self.debug = debug
        self.shell_exec = shell_exec or commands.shell
        self.copy_dependencies = copy_dependencies
        # ``conda info`` is a subprocess spawning the conda binary (~1-2s).
        # It is queried several times over a context's life (availability
        # probe, conda version, conda-build availability), so cache the
        # result. ``_reset_conda_properties`` clears it after any install so
        # a re-probe reflects the new state.
        self._conda_info: dict[str, Any] | None = None

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
        self.ensure_channels: list[str] = listify(ensure_channels)
        self.use_local = use_local
        self.platforms: list[str] = parse_platforms(platforms)
        self.platform_overrides: dict[str, dict[str, str]] = platform_overrides or {}
        self._native_platform: str | None = None
        self._native_platform_failed = False
        self.codesign_exec: str | None = codesign_exec or which("rcodesign")
        self._reset_conda_properties()

    def _reset_conda_properties(self) -> None:
        self._conda_info = None
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
    def _override_channels_args(self) -> list[str]:
        override_channels_args = []
        if self.ensure_channels:
            override_channels_args.append("--override-channels")
            for channel in self.ensure_channels:
                override_channels_args.extend(["--channel", channel])
        return override_channels_args

    @property
    def _solver_args(self) -> list[str]:
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

    def conda_info(self) -> dict[str, Any]:
        if self._conda_info is None:
            cmd = listify(self.conda_exec) + ["info", "--json"]
            info_out = commands.execute(cmd)
            self._conda_info = json.loads(info_out)
        return self._conda_info

    def is_conda_installed(self) -> bool:
        """
        Check if conda_info() works
        """
        try:
            self.conda_info()
            return True
        except Exception:
            return False

    def can_install_conda(self) -> bool:
        """
        If conda_exec is set to a path outside of conda_prefix,
        there is no use installing conda into conda_prefix, since it can't be used by galaxy.
        If conda_exec equals conda_prefix/bin/conda, we can install conda if either conda_prefix
        does not exist or is empty.
        """
        assert isinstance(self.conda_exec, str), "conda_exec is not a str"
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

    def exec_command(
        self,
        operation: str,
        args: list[str],
        stdout_path: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> int:
        """
        Execute the requested command.

        ``extra_env`` holds additional environment variables for this call only.

        Return the process exit code (i.e. 0 in case of success).
        """
        cmd = listify(self.conda_exec) + operation.split()
        if self.debug:
            cmd.append("--debug")
        cmd.extend(args)
        env = {}
        if self.condarc_override:
            env["CONDARC"] = self.condarc_override
        if extra_env:
            env.update(extra_env)
        cmd_string = shlex.join(cmd)
        kwds: dict[str, Any] = {}
        conda_exec_home: str | None = None
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

    def is_package_installed(self, pkg_name: str, version: str | None = None) -> bool:
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

    def exec_create(
        self,
        args: Iterable[str],
        allow_local: bool = True,
        stdout_path: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> int:
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
            ret = self.exec_command("create", create_args, stdout_path=stdout_path, extra_env=extra_env)
            if ret == 0:
                break
        return ret

    def exec_remove(self, args: list[str]) -> int:
        """
        Remove a conda environment using conda env remove -y --name `args`.

        Return the process exit code (i.e. 0 in case of success).
        """
        remove_args = ["-y", "--name"]
        remove_args.extend(args)
        return self.exec_command("env remove", remove_args)

    def exec_install(
        self,
        args: Iterable[str],
        allow_local: bool = True,
        stdout_path: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> int:
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
            ret = self.exec_command("install", install_args, stdout_path=stdout_path, extra_env=extra_env)
            if ret == 0:
                break
        if ret == 0:
            self._reset_conda_properties()
        return ret

    def exec_clean(self, args: list[str] | None = None, quiet: bool = False) -> int:
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
        self, args: list[str], json: bool = False, offline: bool = False, platform: str | None = None
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

    @property
    def native_platform(self) -> str:
        """The conda subdir of the machine conda runs on (cached)."""
        if self._native_platform is None:
            if self._native_platform_failed:
                raise RuntimeError("The native conda platform could not be determined")
            try:
                self._native_platform = self.conda_info()["platform"]
            except Exception:
                # Remembered, so that routing does not run "conda info" again on every call.
                self._native_platform_failed = True
                log.exception("Could not determine the native conda platform, ignoring configured platforms")
                raise
        assert isinstance(self._native_platform, str)
        return self._native_platform

    @property
    def foreign_platforms(self) -> list[str]:
        """Configured platforms other than the native one."""
        if not self.platforms:
            return []
        try:
            native = self.native_platform
        except Exception:
            return []
        return [p for p in self.platforms if p != native]

    @property
    def configured_platforms(self) -> list[str]:
        """The native platform followed by the configured foreign platforms."""
        if not self.platforms:
            return []
        try:
            return [self.native_platform] + self.foreign_platforms
        except Exception:
            return []

    def is_native_platform(self, subdir: str | None) -> bool:
        return not subdir or subdir == self.native_platform

    def platform_prefix(self, subdir: str) -> str:
        """Conda base for ``subdir``: ``conda_prefix`` if native, else ``<conda_prefix>/platforms/<subdir>``."""
        if self.is_native_platform(subdir):
            return self.conda_prefix
        return os.path.join(self.conda_prefix, PLATFORMS_DIRECTORY_NAME, subdir)

    def platform_env_path(self, subdir: str, env_name: str) -> str:
        return os.path.join(self.platform_prefix(subdir), "envs", env_name)

    def platform_activate(self, subdir: str | None) -> str:
        if not subdir or self.is_native_platform(subdir):
            return self.activate
        return os.path.join(self.platform_prefix(subdir), "bin", "activate")

    def platform_env_vars(self, subdir: str) -> dict[str, str]:
        """Environment variables for solving for ``subdir`` from another platform.

        Defaults set the glibc (linux-*) or macOS (osx-*) virtual package version;
        ``platform_overrides`` ({subdir: {variable: value}}) is applied on top.
        """
        env = {"CONDA_SUBDIR": subdir}
        env.update(DEFAULT_PLATFORM_OVERRIDES.get(subdir.split("-", 1)[0], {}))
        env.update({str(k): str(v) for k, v in (self.platform_overrides.get(subdir) or {}).items()})
        return env

    def platform_has_env(self, subdir: str, env_name: str) -> bool:
        """Cheap filesystem check, a foreign environment counts once its base exists and its marker is written."""
        if self.is_native_platform(subdir):
            return self.has_env(env_name)
        if not os.path.isfile(self.platform_activate(subdir)):
            return False
        return os.path.isfile(os.path.join(self.platform_env_path(subdir, env_name), PLATFORM_OK_MARKER))

    def mark_platform_env_ok(self, subdir: str, env_name: str) -> bool:
        """Write the marker that makes a foreign environment usable, False if that is not possible."""
        env_path = self.platform_env_path(subdir, env_name)
        if not os.path.isfile(self.platform_activate(subdir)):
            log.warning("Conda base of platform %s is missing, not marking environment %s", subdir, env_name)
            return False
        if not os.path.isdir(env_path):
            return False
        try:
            with open(os.path.join(env_path, PLATFORM_OK_MARKER), "w"):
                pass
        except OSError:
            log.warning("Could not write platform marker in '%s'", env_path, exc_info=True)
            return False
        return True

    @contextlib.contextmanager
    def env_lock(self, env_name: str, timeout: Optional[Union[int, float]] = None) -> Iterator[bool]:
        """Lock for all creation work on ``env_name`` (native and foreign), yields False if it could not be taken.

        The lock file is ``<conda_prefix>/.locks/<env_name>.lock``, outside of ``envs`` where the
        environment name pattern would pick it up as an environment.
        """
        lock = None
        if timeout is None:
            timeout = PLATFORM_LOCK_TIMEOUT
        try:
            lock_dir = os.path.join(self.conda_prefix, LOCKS_DIRECTORY_NAME)
            os.makedirs(lock_dir, exist_ok=True)
            lock = FileLock(os.path.join(lock_dir, env_name), timeout=timeout)
            lock.acquire()
        except FileLockException:
            log.warning("Timed out waiting for the lock of conda environment %s", env_name)
            lock = None
        except OSError:
            log.warning("Could not lock conda environment %s", env_name, exc_info=True)
            lock = None
        try:
            yield lock is not None
        finally:
            if lock is not None:
                lock.release()

    def sign_platform_files(self, subdir: str, prefix: str) -> bool:
        """Ad-hoc sign the Mach-O files conda rewrote in ``prefix`` (osx-* platforms only).

        Conda patches the install prefix into binaries, which invalidates their code signature,
        and only re-signs them when it runs on macOS. The files are taken from the conda-meta
        records (binary files with a prefix placeholder). Returns False if the files could not
        be signed (no signer configured, or the signer failed for at least one file).
        """
        if not subdir.startswith("osx-"):
            return True
        files = patched_binary_files(prefix)
        if not self.codesign_exec:
            if files:
                log.warning("No code signer available, not signing %d files in '%s'", len(files), prefix)
            return not files
        signed = 0
        failed = 0
        for path in files:
            try:
                result = subprocess.run([self.codesign_exec, "sign", path], capture_output=True, text=True, check=False)
                returncode, stderr = result.returncode, result.stderr
            except OSError as e:
                returncode, stderr = 1, str(e)
            if returncode == 0:
                signed += 1
            else:
                failed += 1
                log.warning("Failed to sign '%s' (exit code %s):\n%s", path, returncode, stderr)
        log.info("Signed %d files (%d failed) in '%s' for platform %s", signed, failed, prefix, subdir)
        return failed == 0

    def ensure_platform_bases(self) -> None:
        """Create the conda base of every foreign platform that lacks one.

        Failures are logged and never raised.
        """
        for subdir in self.foreign_platforms:
            base = self.platform_prefix(subdir)
            if os.path.exists(os.path.join(base, "conda-meta", "history")):
                continue
            log.info("Creating conda base for platform %s in %s, this may take several minutes.", subdir, base)
            try:
                os.makedirs(os.path.dirname(base), exist_ok=True)
                args = ["--yes", "--platform", subdir, "-p", base]
                args.extend(self._override_channels_args)
                args.extend(["conda", "python"])
                with tempfile.NamedTemporaryFile("r", suffix=".log") as out:
                    ret = self.exec_command(
                        "create", args, stdout_path=out.name, extra_env=self.platform_env_vars(subdir)
                    )
                    if ret != 0:
                        log.warning(
                            "Failed to create conda base for platform %s (exit code %s):\n%s",
                            subdir,
                            ret,
                            out.read(),
                        )
                    elif not self.sign_platform_files(subdir, base):
                        log.warning("Conda base for platform %s contains unsigned files", subdir)
            except Exception:
                log.warning("Failed to create conda base for platform %s", subdir, exc_info=True)

    def create_platform_environments(
        self,
        env_name: str,
        specs: Iterable[str],
        allow_local: bool = True,
    ) -> dict[str, bool]:
        """Create ``env_name`` on the foreign platforms that do not have it yet.

        The caller holds :meth:`env_lock` of ``env_name``. Platforms that already have the
        environment are skipped (and reported as successful). A failure is logged as a warning,
        and does not raise. Returns {subdir: success}.
        """
        specs = list(specs)
        results: dict[str, bool] = {}
        for subdir in self.foreign_platforms:
            if self.platform_has_env(subdir, env_name):
                results[subdir] = True
                continue
            env_path = self.platform_env_path(subdir, env_name)
            existed_before = os.path.exists(env_path)
            try:
                with tempfile.NamedTemporaryFile("r", suffix=".log") as out:
                    ret = self.exec_create(
                        ["--platform", subdir, "-p", env_path] + specs,
                        allow_local=allow_local,
                        stdout_path=out.name,
                        extra_env=self.platform_env_vars(subdir),
                    )
                    output = out.read()
            except Exception:
                log.warning("Failed to create conda environment %s for platform %s", env_name, subdir, exc_info=True)
                ret, output = 1, ""
            if ret == 0:
                try:
                    signed = self.sign_platform_files(subdir, env_path)
                except Exception:
                    log.warning("Failed to sign files of environment %s for %s", env_name, subdir, exc_info=True)
                    signed = False
                if signed and self.mark_platform_env_ok(subdir, env_name):
                    results[subdir] = True
                else:
                    log.warning(
                        "Environment %s for platform %s has unsigned files or no usable base and is not marked usable",
                        env_name,
                        subdir,
                    )
                    results[subdir] = False
            else:
                log.warning(
                    "Could not create conda environment %s for platform %s (exit code %s):\n%s",
                    env_name,
                    subdir,
                    ret,
                    output,
                )
                if not existed_before:
                    shutil.rmtree(env_path, ignore_errors=True)
                results[subdir] = False
        return results

    def remove_platform_environments(self, env_name: str) -> None:
        if not env_name or not env_name.strip() or env_name in (".", "..") or os.sep in env_name:
            log.warning("Not removing platform environments for invalid environment name '%s'", env_name)
            return
        for subdir in self.foreign_platforms:
            shutil.rmtree(self.platform_env_path(subdir, env_name), ignore_errors=True)

    def has_env(self, env_name: str) -> bool:
        env_path = self.env_path(env_name)
        return os.path.isdir(env_path)

    def get_conda_target_installed_path(self, conda_target: "CondaTarget") -> str | None:
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
        self, package: str, version: str | None = None, build: str | None = None, channel: str | None = None
    ) -> None:
        if SHELL_UNSAFE_PATTERN.search(package) is not None or not package:
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


def _create_on_all_platforms(
    conda_context: CondaContext,
    env_name: str,
    native_create_args: list[str],
    specs: list[str],
    allow_local: bool = True,
) -> int:
    """Create the named environment natively, then on each configured foreign platform.

    Without configured platforms this is the plain native create. Otherwise both steps run under the
    lock of the environment, so that concurrent installs do not create or delete the same directories.
    Only the native exit code is returned, foreign failures are logged.
    """
    if not conda_context.platforms:
        return conda_context.exec_create(native_create_args, allow_local=allow_local)
    with conda_context.env_lock(env_name) as locked:
        if not locked:
            # Native install as before, a later install adds the foreign copies.
            return conda_context.exec_create(native_create_args, allow_local=allow_local)
        ret = 0 if conda_context.has_env(env_name) else conda_context.exec_create(native_create_args, allow_local)
        if ret == 0:
            conda_context.create_platform_environments(env_name, specs, allow_local=allow_local)
    return ret


def install_conda_targets(
    conda_targets: Iterable[CondaTarget],
    conda_context: CondaContext,
    env_name: str | None = None,
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
        specs = [conda_target.package_specifier for conda_target in conda_targets]
        create_args.extend(specs)
        return _create_on_all_platforms(conda_context, env_name, create_args, specs, allow_local)
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
        return _create_on_all_platforms(
            conda_context, conda_target.install_environment, create_args, [conda_target.package_specifier]
        )
    else:
        return conda_context.exec_install([conda_target.package_specifier])


def cleanup_failed_install_of_environment(env: str, conda_context: CondaContext) -> int:
    if conda_context.has_env(env):
        return conda_context.exec_remove([env])
    return 0


def cleanup_failed_install(conda_target: CondaTarget, conda_context: CondaContext) -> int:
    return cleanup_failed_install_of_environment(conda_target.install_environment, conda_context=conda_context)


def best_search_result(
    conda_target: CondaTarget, conda_context: CondaContext, offline: bool = False, platform: str | None = None
) -> tuple[None, None] | tuple[dict[str, Any], bool]:
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


def is_search_hit_exact(conda_target: CondaTarget, search_hit: dict[str, Any]) -> bool:
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


def filter_installed_targets(conda_targets: Iterable[CondaTarget], conda_context: CondaContext) -> list[CondaTarget]:
    installed = functools.partial(is_conda_target_installed, conda_context=conda_context)
    return list(filter(installed, conda_targets))


def build_isolated_environment(
    conda_packages: CondaTarget | list[CondaTarget],
    conda_context: CondaContext,
    path: str | None = None,
    copy: bool = False,
    quiet: bool = False,
) -> tuple[str, int]:
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


def split_version_build(version: str | None) -> tuple[str | None, str | None]:
    """Split version string into version and build.

    Handles '=' separator (conda format) and '--' separator (mulled format).
    """
    if not version:
        return version, None
    build = None
    if "=" in version:
        version, build = version.split("=")
    elif "--" in version:
        version, build = version.split("--")
    return version, build


def requirement_to_conda_targets(requirement: "ToolRequirement") -> CondaTarget | None:
    conda_target = None
    if requirement.type == "package":
        assert requirement.name
        version, build = split_version_build(requirement.version)
        conda_target = CondaTarget(requirement.name, version=version, build=build)
    return conda_target


def requirements_to_conda_targets(requirements: Iterable["ToolRequirement"]) -> list[CondaTarget]:
    conda_targets = (requirement_to_conda_targets(_) for _ in requirements)
    return [c for c in conda_targets if c is not None]


__all__ = (
    "CondaContext",
    "CondaTarget",
    "install_conda",
    "parse_platforms",
    "install_conda_target",
    "requirements_to_conda_targets",
    "split_version_build",
)
