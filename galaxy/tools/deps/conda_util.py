import functools
import hashlib
import json
import logging
import os
import re
import shutil
import tempfile

from distutils.version import LooseVersion
from sys import platform as _platform

import six
import yaml

from ..deps import commands
from ..deps import installable

log = logging.getLogger(__name__)

# Not sure there are security concerns, lets just fail fast if we are going
# break shell commands we are building.
SHELL_UNSAFE_PATTERN = re.compile(r"[\s\"']")

IS_OS_X = _platform == "darwin"

# BSD 3-clause
CONDA_LICENSE = "http://docs.continuum.io/anaconda/eula"
VERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@(.*)")
UNVERSIONED_ENV_DIR_NAME = re.compile(r"__(.*)@_uv_")
USE_PATH_EXEC_DEFAULT = False
CONDA_VERSION = "3.19.3"


def conda_link():
    if IS_OS_X:
        url = "https://repo.continuum.io/miniconda/Miniconda2-4.0.5-MacOSX-x86_64.sh"
    else:
        url = "https://repo.continuum.io/miniconda/Miniconda2-4.0.5-Linux-x86_64.sh"
    return url


def find_conda_prefix(conda_prefix=None):
    """ If supplied conda_prefix is not set, default to the default location
    for Miniconda installs.
    """
    if conda_prefix is None:
        return os.path.join(os.path.expanduser("~"), "miniconda2")
    return conda_prefix


class CondaContext(installable.InstallableContext):
    installable_description = "Conda"

    def __init__(self, conda_prefix=None, conda_exec=None,
                 shell_exec=None, debug=False, ensure_channels='',
                 condarc_override=None, use_path_exec=USE_PATH_EXEC_DEFAULT):
        self.condarc_override = condarc_override
        if not conda_exec and use_path_exec:
            conda_exec = commands.which("conda")
        if conda_exec:
            conda_exec = os.path.normpath(conda_exec)
        self.conda_exec = conda_exec
        self.debug = debug
        self.shell_exec = shell_exec or commands.shell

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
        self.ensured_channels = False

    def ensure_channels_configured(self):
        if not self.ensured_channels:
            self.ensured_channels = True

            changed = False
            conda_conf = self.load_condarc()
            if "channels" not in conda_conf:
                conda_conf["channels"] = []
            channels = conda_conf["channels"]
            for channel in self.ensure_channels:
                if channel not in channels:
                    changed = True
                    channels.append(channel)

            if changed:
                self.save_condarc(conda_conf)

    def conda_info(self):
        if self.conda_exec is not None:
            info_out = commands.execute([self.conda_exec, "info", "--json"])
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

    def load_condarc(self):
        condarc = self.condarc
        if os.path.exists(condarc):
            with open(condarc, "r") as f:
                return yaml.safe_load(f)
        else:
            return {"channels": ["defaults"]}

    def save_condarc(self, conf):
        condarc = self.condarc
        try:
            with open(condarc, "w") as f:
                return yaml.safe_dump(conf, f)
        except IOError:
            template = ("Failed to update write to path [%s] while attempting to update conda configuration, "
                        "please update the configuration to override the condarc location or "
                        "grant this application write to the parent directory.")
            message = template % condarc
            raise Exception(message)

    @property
    def condarc(self):
        if self.condarc_override:
            return self.condarc_override
        else:
            home = os.path.expanduser("~")
            return os.path.join(home, ".condarc")

    def command(self, operation, args):
        if isinstance(args, list):
            args = " ".join(args)
        conda_prefix = self.conda_exec
        if self.debug:
            conda_prefix += " --debug"
        return "%s %s %s" % (conda_prefix, operation, args)

    def exec_command(self, operation, args):
        command = self.command(operation, args)
        env = {'HOME': self.conda_prefix}  # We don't want to pollute ~/.conda, which may not even be writable
        condarc_override = self.condarc_override
        if condarc_override:
            env["CONDARC"] = condarc_override
        return self.shell_exec(command, env=env)

    def exec_create(self, args):
        create_base_args = [
            "-y"
        ]
        create_base_args.extend(args)
        return self.exec_command("create", create_base_args)

    def exec_remove(self, args):
        remove_base_args = [
            "remove",
            "-y",
            "--name"
        ]
        remove_base_args.extend(args)
        return self.exec_command("env", remove_base_args)

    def exec_install(self, args):
        install_base_args = [
            "-y"
        ]
        install_base_args.extend(args)
        return self.exec_command("install", install_base_args)

    def export_list(self, name, path):
        return self.exec_command("list", [
            "--name", name,
            "--export", ">", path
        ])

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
def install_conda(conda_context=None):
    conda_context = _ensure_conda_context(conda_context)
    f, script_path = tempfile.mkstemp(suffix=".sh", prefix="conda_install")
    os.close(f)
    download_cmd = " ".join(commands.download_command(conda_link(), to=script_path, quote_url=True))
    install_cmd = "bash '%s' -b -p '%s'" % (script_path, conda_context.conda_prefix)
    fix_version_cmd = "%s install -y -q conda=%s " % (os.path.join(conda_context.conda_prefix, 'bin/conda'), CONDA_VERSION)
    full_command = "%s && %s && %s" % (download_cmd, install_cmd, fix_version_cmd)
    try:
        return conda_context.shell_exec(full_command)
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)


def install_conda_target(conda_target, conda_context=None):
    """ Install specified target into a its own environment.
    """
    conda_context = _ensure_conda_context(conda_context)
    conda_context.ensure_channels_configured()
    create_args = [
        "--name", conda_target.install_environment,  # enviornment for package
        conda_target.package_specifier,
    ]
    return conda_context.exec_create(create_args)


def cleanup_failed_install(conda_target, conda_context=None):
    conda_context = _ensure_conda_context(conda_context)
    if conda_context.has_env(conda_target.install_environment):
        conda_context.exec_remove([conda_target.install_environment])


def best_search_result(conda_target, conda_context=None, channels_override=None):
    """Find best "conda search" result for specified target.

    Return ``None`` if no results match.
    """
    conda_context = _ensure_conda_context(conda_context)
    if not channels_override:
        conda_context.ensure_channels_configured()

    search_cmd = [conda_context.conda_exec, "search", "--full-name", "--json"]
    if channels_override:
        search_cmd.append("--override-channels")
        for channel in channels_override:
            search_cmd.extend(["--channel", channel])
    search_cmd.append(conda_target.package)
    res = commands.execute(search_cmd)
    hits = json.loads(res).get(conda_target.package, [])
    hits = sorted(hits, key=lambda hit: LooseVersion(hit['version']), reverse=True)

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


def is_target_available(conda_target, conda_context=None, channels_override=None):
    """Check if a specified target is available for installation.

    If the package name exists return ``True`` (the ``bool``). If in addition
    the version matches exactly return "exact" (a string). Otherwise return
    ``False``.
    """
    (best_hit, exact) = best_search_result(conda_target, conda_context, channels_override)
    if best_hit:
        return 'exact' if exact else True
    else:
        return False


def is_conda_target_installed(conda_target, conda_context=None, verbose_install_check=False):
    conda_context = _ensure_conda_context(conda_context)
    # fail by default
    success = False
    if conda_context.has_env(conda_target.install_environment):
        if not verbose_install_check:
            return True
        # because export_list directs output to a file we
        # need to make a temporary file, not use StringIO
        f, package_list_file = tempfile.mkstemp(suffix='.env_packages')
        os.close(f)
        conda_context.export_list(conda_target.install_environment, package_list_file)
        search_pattern = conda_target.package_specifier + '='
        with open(package_list_file) as input_file:
            for line in input_file:
                if line.startswith(search_pattern):
                    success = True
                    break
        os.remove(package_list_file)
    return success


def filter_installed_targets(conda_targets, conda_context=None, verbose_install_check=False):
    conda_context = _ensure_conda_context(conda_context)
    installed = functools.partial(is_conda_target_installed,
                                  conda_context=conda_context,
                                  verbose_install_check=verbose_install_check)
    return filter(installed, conda_targets)


def build_isolated_environment(
    conda_packages,
    path=None,
    copy=False,
    conda_context=None,
):
    """ Build a new environment (or reuse an existing one from hashes)
    for specified conda packages.
    """
    if not isinstance(conda_packages, list):
        conda_packages = [conda_packages]

    # Lots we could do in here, hashing, checking revisions, etc...
    conda_context = _ensure_conda_context(conda_context)
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
        create_args = ["--unknown", "--offline"]
        if path is None:
            create_args.extend(["--name", tempdir_name])
        else:
            create_args.extend(["--prefix", path])

        if copy:
            create_args.append("--copy")
        for export_path in export_paths:
            create_args.extend([
                "--file", export_path, ">", "/dev/null"
            ])

        if path is not None and os.path.exists(path):
            exit_code = conda_context.exec_install(create_args)
        else:
            exit_code = conda_context.exec_create(create_args)

        return (path or tempdir_name, exit_code)
    finally:
        shutil.rmtree(tempdir)


def requirement_to_conda_targets(requirement, conda_context=None):
    conda_target = None
    if requirement.type == "package":
        conda_target = CondaTarget(requirement.name,
                                   version=requirement.version)
    return conda_target


def requirements_to_conda_targets(requirements, conda_context=None):
    r_to_ct = functools.partial(requirement_to_conda_targets,
                                conda_context=conda_context)
    conda_targets = map(r_to_ct, requirements)
    return [c for c in conda_targets if c is not None]


def _ensure_conda_context(conda_context):
    if conda_context is None:
        conda_context = CondaContext()
    return conda_context


__all__ = [
    'CondaContext',
    'CondaTarget',
    'install_conda',
    'install_conda_target',
    'requirements_to_conda_targets',
]
