import functools
import hashlib
import json
import os
import re
import shutil
from sys import platform as _platform
import tempfile

import six
import yaml

from ..deps import commands

# Not sure there are security concerns, lets just fail fast if we are going
# break shell commands we are building.
SHELL_UNSAFE_PATTERN = re.compile(r"[\s\"']")

IS_OS_X = _platform == "darwin"

# BSD 3-clause
CONDA_LICENSE = "http://docs.continuum.io/anaconda/eula"
VERSIONED_ENV_DIR_NAME = re.compile(r"__package__(.*)@__version__(.*)")
UNVERSIONED_ENV_DIR_NAME = re.compile(r"__package__(.*)@__unversioned__")
USE_PATH_EXEC_DEFAULT = False


def conda_link():
    if IS_OS_X:
        url = "https://repo.continuum.io/miniconda/Miniconda-latest-MacOSX-x86_64.sh"
    else:
        url = "https://repo.continuum.io/miniconda/Miniconda-latest-Linux-x86_64.sh"
    return url


def find_conda_prefix(conda_prefix=None):
    """ If supplied conda_prefix is not set, default to the default location
    for Miniconda installs.
    """
    if conda_prefix is None:
        return os.path.join(os.path.expanduser("~"), "miniconda2")
    return conda_prefix


class CondaContext(object):

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
        env = {}
        condarc_override = self.condarc_override
        if condarc_override:
            env["CONDARC"] = condarc_override
        self.shell_exec(command, env=env)

    def exec_create(self, args):
        create_base_args = [
            "-y"
        ]
        create_base_args.extend(args)
        return self.exec_command("create", create_base_args)

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
            return "__package__%s@__version__%s" % (self.package, self.version)
        else:
            return "__package__%s@__unversioned__" % (self.package)


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
    f, script_path = tempfile.mkstemp(suffix=".bash", prefix="conda_install")
    os.close(f)
    download_cmd = " ".join(commands.download_command(conda_link(), to=script_path, quote_url=True))
    install_cmd = "bash '%s' -b -p '%s'" % (script_path, conda_context.conda_prefix)
    full_command = "%s; %s" % (download_cmd, install_cmd)
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
    conda_context.exec_create(create_args)


def is_conda_target_installed(conda_target, conda_context=None):
    conda_context = _ensure_conda_context(conda_context)
    return conda_context.has_env(conda_target.install_environment)


def filter_installed_targets(conda_targets, conda_context=None):
    conda_context = _ensure_conda_context(conda_context)
    installed = functools.partial(is_conda_target_installed,
                                  conda_context=conda_context)
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
