import functools
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile

import packaging.version
import six
from six.moves import shlex_quote

from galaxy.util import unicodify
from . import (
    commands,
    installable
)

log = logging.getLogger(__name__)

# Not sure there are security concerns, lets just fail fast if we are going
# break shell commands we are building.
SHELL_UNSAFE_PATTERN = re.compile(r"[\s\"']")

IS_OS_X = sys.platform == "darwin"

# BSD 3-clause
CONDA_LICENSE = "http://docs.continuum.io/anaconda/eula"
VERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@(.*)")
UNVERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@_uv_")
USE_PATH_EXEC_DEFAULT = False
CONDA_VERSION = "4.3.33"
CONDA_BUILD_VERSION = "2.1.18"
USE_LOCAL_DEFAULT = False


def conda_link():
    if IS_OS_X:
        url = "https://repo.continuum.io/miniconda/Miniconda3-4.3.31-MacOSX-x86_64.sh"
    else:
        if sys.maxsize > 2**32:
            url = "https://repo.continuum.io/miniconda/Miniconda3-4.3.31-Linux-x86_64.sh"
        else:
            url = "https://repo.continuum.io/miniconda/Miniconda3-4.3.31-Linux-x86.sh"
    return url


def find_conda_prefix(conda_prefix=None):
    """ If supplied conda_prefix is not set, default to the default location
    for Miniconda installs.
    """
    if conda_prefix is None:
        home = os.path.expanduser("~")
        miniconda_2_dest = os.path.join(home, "miniconda2")
        miniconda_3_dest = os.path.join(home, "miniconda3")
        # Prefer miniconda3 install if both available
        if os.path.exists(miniconda_3_dest):
            return miniconda_3_dest
        elif os.path.exists(miniconda_2_dest):
            return miniconda_2_dest
        else:
            return miniconda_3_dest
    return conda_prefix


class CondaContext(installable.InstallableContext):
    installable_description = "Conda"

    def __init__(self, conda_prefix=None, conda_exec=None,
                 shell_exec=None, debug=False, ensure_channels='',
                 condarc_override=None, use_path_exec=USE_PATH_EXEC_DEFAULT,
                 copy_dependencies=False, use_local=USE_LOCAL_DEFAULT):
        self.condarc_override = condarc_override
        if not conda_exec and use_path_exec:
            conda_exec = commands.which("conda")
        if conda_exec:
            conda_exec = os.path.normpath(conda_exec)
        self.conda_exec = conda_exec
        self.debug = debug
        self.shell_exec = shell_exec or commands.shell
        self.copy_dependencies = copy_dependencies

        if conda_prefix is None:
            info = self.conda_info()
            if info and "default_prefix" in info:
                conda_prefix = info["default_prefix"]
        if conda_prefix is None:
            conda_prefix = find_conda_prefix(conda_prefix)

        self.conda_prefix = conda_prefix
        if conda_exec is None:
            self.conda_exec = self._bin("conda")
        if ensure_channels:
            if not isinstance(ensure_channels, list):
                ensure_channels = [c for c in ensure_channels.split(",") if c]
        else:
            ensure_channels = None
        self.ensure_channels = ensure_channels
        self._conda_version = None
        self._miniconda_version = None
        self._conda_build_available = None
        self.use_local = use_local

    @property
    def conda_version(self):
        if self._conda_version is None:
            self._guess_conda_properties()
        return self._conda_version

    @property
    def conda_build_available(self):
        if self._conda_build_available is None:
            self._guess_conda_properties()
        return self._conda_build_available

    def _guess_conda_properties(self):
        conda_meta_path = self._conda_meta_path
        # Perhaps we should call "conda info --json" and parse it but for now we are going
        # to assume the default.
        conda_version = packaging.version.parse(CONDA_VERSION)
        conda_build_available = False
        miniconda_version = "3"

        if os.path.exists(conda_meta_path):
            for package in os.listdir(conda_meta_path):
                package_parts = package.split("-")
                if len(package_parts) < 3:
                    continue
                package = '-'.join(package_parts[:-2])
                version = package_parts[-2]
                # build = package_parts[-1]
                if package == "conda":
                    conda_version = packaging.version.parse(version)
                if package == "python" and version.startswith("2"):
                    miniconda_version = "2"
                if package == "conda-build":
                    conda_build_available = True

        self._conda_version = conda_version
        self._miniconda_version = miniconda_version
        self._conda_build_available = conda_build_available

    @property
    def _conda_meta_path(self):
        return os.path.join(self.conda_prefix, "conda-meta")

    @property
    def _override_channels_args(self):
        override_channels_args = []
        if self.ensure_channels:
            override_channels_args.append("--override-channels")
            for channel in self.ensure_channels:
                override_channels_args.extend(["--channel", channel])
        return override_channels_args

    def ensure_conda_build_installed_if_needed(self):
        if self.use_local and not self.conda_build_available:
            conda_targets = [CondaTarget("conda-build", version=CONDA_BUILD_VERSION)]
            # Cannot use --use-local during installation of conda-build.
            return install_conda_targets(conda_targets, conda_context=self, env_name=None, allow_local=False)
        else:
            return 0

    def conda_info(self):
        if self.conda_exec is not None:
            info_out = commands.execute([self.conda_exec, "info", "--json"])
            info_out = unicodify(info_out)
            info = json.loads(info_out)
            return info
        else:
            return None

    def is_conda_installed(self):
        """
        Check if conda_exec exists
        """
        if os.path.exists(self.conda_exec):
            return True
        else:
            return False

    def can_install_conda(self):
        """
        If conda_exec is set to a path outside of conda_prefix,
        there is no use installing conda into conda_prefix, since it can't be used by galaxy.
        If conda_exec equals conda_prefix/bin/conda, we can install conda if either conda_prefix
        does not exist or is empty.
        """
        conda_exec = os.path.abspath(self.conda_exec)
        conda_prefix_plus_exec = os.path.abspath(os.path.join(self.conda_prefix, 'bin/conda'))
        if conda_exec == conda_prefix_plus_exec:
            if not os.path.exists(self.conda_prefix):
                return True
            elif os.listdir(self.conda_prefix) == []:
                os.rmdir(self.conda_prefix)  # Conda's install script fails if path exists (even if empty).
                return True
            else:
                log.warning("Cannot install Conda because conda_prefix '%s' exists and is not empty.",
                            self.conda_prefix)
                return False
        else:
            log.warning("Skipping installation of Conda into conda_prefix '%s', "
                        "since conda_exec '%s' is set to a path outside of conda_prefix.",
                        self.conda_prefix, self.conda_exec)
            return False

    def exec_command(self, operation, args, stdout_path=None):
        """
        Execute the requested command.

        Return the process exit code (i.e. 0 in case of success).
        """
        cmd = [self.conda_exec]
        if self.debug:
            cmd.append("--debug")
        cmd.append(operation)
        cmd.extend(args)
        env = {}
        if self.condarc_override:
            env["CONDARC"] = self.condarc_override
        cmd_string = ' '.join(map(shlex_quote, cmd))
        kwds = dict()
        try:
            if stdout_path:
                kwds['stdout'] = open(stdout_path, 'w')
                cmd_string += " > '%s'" % stdout_path
            conda_exec_home = env['HOME'] = tempfile.mkdtemp(prefix='conda_exec_home_')  # We don't want to pollute ~/.conda, which may not even be writable
            log.debug("Executing command: %s", cmd_string)
            return self.shell_exec(cmd, env=env, **kwds)
        except Exception:
            log.exception("Failed to execute command: %s", cmd_string)
            return 1
        finally:
            if kwds.get('stdout'):
                kwds['stdout'].close()
            if conda_exec_home:
                shutil.rmtree(conda_exec_home, ignore_errors=True)

    def exec_create(self, args, allow_local=True, stdout_path=None):
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        create_base_args = [
            "-y"
        ]
        if allow_local and self.use_local:
            create_base_args.extend(["--use-local"])
        create_base_args.extend(self._override_channels_args)
        create_base_args.extend(args)
        return self.exec_command("create", create_base_args, stdout_path=stdout_path)

    def exec_remove(self, args):
        """
        Remove a conda environment using conda env remove -y --name `args`.

        Return the process exit code (i.e. 0 in case of success).
        """
        remove_base_args = [
            "remove",
            "-y",
            "--name"
        ]
        remove_base_args.extend(args)
        return self.exec_command("env", remove_base_args)

    def exec_install(self, args, allow_local=True, stdout_path=None):
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        install_base_args = [
            "-y"
        ]
        if allow_local and self.use_local:
            install_base_args.append("--use-local")
        install_base_args.extend(self._override_channels_args)
        install_base_args.extend(args)
        return self.exec_command("install", install_base_args, stdout_path=stdout_path)

    def exec_clean(self, args=[], quiet=False):
        """
        Clean up after conda installation.

        Return the process exit code (i.e. 0 in case of success).
        """
        clean_base_args = [
            "--tarballs",
            "-y"
        ]
        clean_args = clean_base_args + args
        stdout_path = None
        if quiet:
            stdout_path = "/dev/null"
        return self.exec_command("clean", clean_args, stdout_path=stdout_path)

    def export_list(self, name, path):
        """
        Return the process exit code (i.e. 0 in case of success).
        """
        return self.exec_command("list", [
            "--name", name,
            "--export"
        ], stdout_path=path)

    def env_path(self, env_name):
        return os.path.join(self.envs_path, env_name)

    @property
    def envs_path(self):
        return os.path.join(self.conda_prefix, "envs")

    def has_env(self, env_name):
        env_path = self.env_path(env_name)
        return os.path.isdir(env_path)

    @property
    def deactivate(self):
        return self._bin("deactivate")

    @property
    def activate(self):
        return self._bin("activate")

    def is_installed(self):
        return self.is_conda_installed()

    def can_install(self):
        return self.can_install_conda()

    @property
    def parent_path(self):
        return os.path.dirname(os.path.abspath(self.conda_prefix))

    def _bin(self, name):
        return os.path.join(self.conda_prefix, "bin", name)


def installed_conda_targets(conda_context):
    envs_path = conda_context.envs_path
    dir_contents = os.listdir(envs_path) if os.path.exists(envs_path) else []
    for name in dir_contents:
        versioned_match = VERSIONED_ENV_DIR_NAME.match(name)
        if versioned_match:
            yield CondaTarget(versioned_match.group(1), versioned_match.group(2))

        unversioned_match = UNVERSIONED_ENV_DIR_NAME.match(name)
        if unversioned_match:
            yield CondaTarget(unversioned_match.group(1))


@six.python_2_unicode_compatible
class CondaTarget(object):

    def __init__(self, package, version=None, channel=None):
        if SHELL_UNSAFE_PATTERN.search(package) is not None:
            raise ValueError("Invalid package [%s] encountered." % package)
        self.package = package
        if version and SHELL_UNSAFE_PATTERN.search(version) is not None:
            raise ValueError("Invalid version [%s] encountered." % version)
        self.version = version
        if channel and SHELL_UNSAFE_PATTERN.search(channel) is not None:
            raise ValueError("Invalid version [%s] encountered." % channel)
        self.channel = channel

    def __str__(self):
        attributes = "package=%s" % self.package
        if self.version is not None:
            attributes = "%s,version=%s" % (self.package, self.version)
        else:
            attributes = "%s,unversioned" % self.package

        if self.channel:
            attributes = "%s,channel=%s" % self.channel

        return "CondaTarget[%s]" % attributes

    __repr__ = __str__

    @property
    def package_specifier(self):
        """ Return a package specifier as consumed by conda install/create.
        """
        if self.version:
            return "%s=%s" % (self.package, self.version)
        else:
            return self.package

    @property
    def install_environment(self):
        """ The dependency resolution and installation frameworks will
        expect each target to be installed it its own environment with
        a fixed and predictable name given package and version.
        """
        if self.version:
            return "__%s@%s" % (self.package, self.version)
        else:
            return "__%s@_uv_" % (self.package)

    def __hash__(self):
        return hash((self.package, self.version, self.channel))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return (self.package, self.version, self.channel) == (other.package, other.version, other.channel)
        return False

    def __ne__(self, other):
        return not(self == other)


def hash_conda_packages(conda_packages, conda_target=None):
    """ Produce a unique hash on supplied packages.
    TODO: Ideally we would do this in such a way that preserved environments.
    """
    h = hashlib.new('sha256')
    for conda_package in conda_packages:
        h.update(conda_package.install_environment)
    return h.hexdigest()


# shell makes sense for planemo, in Galaxy this should just execute
# these commands as Python
def install_conda(conda_context, force_conda_build=False):
    f, script_path = tempfile.mkstemp(suffix=".sh", prefix="conda_install")
    os.close(f)
    download_cmd = commands.download_command(conda_link(), to=script_path, quote_url=False)
    install_cmd = ['bash', script_path, '-b', '-p', conda_context.conda_prefix]
    package_targets = [
        "conda=%s" % CONDA_VERSION,
    ]
    if force_conda_build or conda_context.use_local:
        package_targets.append("conda-build=%s" % CONDA_BUILD_VERSION)
    log.info("Installing conda, this may take several minutes.")
    try:
        exit_code = conda_context.shell_exec(download_cmd)
        if exit_code:
            return exit_code
        exit_code = conda_context.shell_exec(install_cmd)
    except Exception:
        log.exception('Failed to install conda')
        return 1
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)
    if exit_code:
        return exit_code
    return conda_context.exec_install(package_targets, allow_local=False)


def install_conda_targets(conda_targets, conda_context, env_name=None, allow_local=True):
    """
    Return the process exit code (i.e. 0 in case of success).
    """
    if env_name is not None:
        create_args = [
            "--name", env_name,  # environment for package
        ]
        for conda_target in conda_targets:
            create_args.append(conda_target.package_specifier)
        return conda_context.exec_create(create_args, allow_local=allow_local)
    else:
        return conda_context.exec_install([t.package_specifier for t in conda_targets], allow_local=allow_local)


def install_conda_target(conda_target, conda_context, skip_environment=False):
    """
    Install specified target into a its own environment.

    Return the process exit code (i.e. 0 in case of success).
    """
    if not skip_environment:
        create_args = [
            "--name", conda_target.install_environment,  # environment for package
            conda_target.package_specifier,
        ]
        return conda_context.exec_create(create_args)
    else:
        return conda_context.exec_install([conda_target.package_specifier])


def cleanup_failed_install_of_environment(env, conda_context):
    if conda_context.has_env(env):
        conda_context.exec_remove([env])


def cleanup_failed_install(conda_target, conda_context=None):
    cleanup_failed_install_of_environment(conda_target.install_environment, conda_context=conda_context)


def best_search_result(conda_target, conda_context, channels_override=None, offline=False):
    """Find best "conda search" result for specified target.

    Return ``None`` if no results match.
    """
    search_cmd = [conda_context.conda_exec, "search", "--full-name", "--json"]
    if offline:
        search_cmd.append("--offline")
    if channels_override:
        search_cmd.append("--override-channels")
        for channel in channels_override:
            search_cmd.extend(["--channel", channel])
    else:
        search_cmd.extend(conda_context._override_channels_args)
    search_cmd.append(conda_target.package)
    res = commands.execute(search_cmd)
    res = unicodify(res)
    hits = json.loads(res).get(conda_target.package, [])
    hits = sorted(hits, key=lambda hit: packaging.version.parse(hit['version']), reverse=True)

    if len(hits) == 0:
        return (None, None)

    best_result = (hits[0], False)

    for hit in hits:
        if is_search_hit_exact(conda_target, hit):
            best_result = (hit, True)
            break

    return best_result


def is_search_hit_exact(conda_target, search_hit):
    target_version = conda_target.version
    # It'd be nice to make request verson of 1.0 match available
    # version of 1.0.3 or something like that.
    return not target_version or search_hit['version'] == target_version


def is_conda_target_installed(conda_target, conda_context):
    # fail by default
    if conda_context.has_env(conda_target.install_environment):
        return True
    else:
        return False


def filter_installed_targets(conda_targets, conda_context):
    installed = functools.partial(is_conda_target_installed,
                                  conda_context=conda_context)
    return list(filter(installed, conda_targets))


def build_isolated_environment(
    conda_packages,
    conda_context,
    path=None,
    copy=False,
    quiet=False,
):
    """ Build a new environment (or reuse an existing one from hashes)
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
            conda_context.export_list(
                name,
                export_path
            )
            export_paths.append(export_path)
        create_args = ["--unknown"]
        # Works in 3.19, 4.0 - 4.2 - not in 4.3.
        # Adjust fix if they fix Conda - xref
        # - https://github.com/galaxyproject/galaxy/issues/3635
        # - https://github.com/conda/conda/issues/2035
        offline_works = (conda_context.conda_version < packaging.version.parse("4.3")) or \
                        (conda_context.conda_version >= packaging.version.parse("4.4"))
        if offline_works:
            create_args.extend(["--offline"])
        else:
            create_args.extend(["--use-index-cache"])
        if path is None:
            create_args.extend(["--name", tempdir_name])
        else:
            create_args.extend(["--prefix", path])

        if copy:
            create_args.append("--copy")
        for export_path in export_paths:
            create_args.extend([
                "--file", export_path
            ])

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


def requirement_to_conda_targets(requirement):
    conda_target = None
    if requirement.type == "package":
        conda_target = CondaTarget(requirement.name,
                                   version=requirement.version)
    return conda_target


def requirements_to_conda_targets(requirements):
    conda_targets = (requirement_to_conda_targets(_) for _ in requirements)
    return [c for c in conda_targets if c is not None]


__all__ = (
    'CondaContext',
    'CondaTarget',
    'install_conda',
    'install_conda_target',
    'requirements_to_conda_targets',
)
