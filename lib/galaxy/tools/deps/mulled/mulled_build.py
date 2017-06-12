#!/usr/bin/env python
"""Build a mulled image for specified conda targets.

Examples

Build a mulled image with:

    mulled-build build 'samtools=1.3.1--4,bedtools=2.22'

"""
from __future__ import print_function

import json
import os
import shutil
import string
import subprocess
import sys
from sys import platform as _platform

try:
    import yaml
except ImportError:
    yaml = None

from galaxy.tools.deps import commands, installable

from ._cli import arg_parser
from .util import (
    build_target,
    conda_build_target_str,
    create_repository,
    quay_repository,
    v1_image_name,
    v2_image_name,
)
from ..conda_compat import MetaData

DIRNAME = os.path.dirname(__file__)
DEFAULT_CHANNEL = "bioconda"
DEFAULT_EXTRA_CHANNELS = ["conda-forge", "r"]
DEFAULT_CHANNELS = [DEFAULT_CHANNEL] + DEFAULT_EXTRA_CHANNELS
DEFAULT_REPOSITORY_TEMPLATE = "quay.io/${namespace}/${image}"
DEFAULT_BINDS = ["build/dist:/usr/local/"]
DEFAULT_WORKING_DIR = '/source/'
IS_OS_X = _platform == "darwin"
INVOLUCRO_VERSION = "1.1.2"
DEST_BASE_IMAGE = os.environ.get('DEST_BASE_IMAGE', None)

SINGULARITY_TEMPLATE = """Bootstrap: docker
From: bgruening/busybox-bash:0.1

%%setup

    echo "Copying conda environment"
    mkdir -p /tmp/conda
    cp -r /data/dist/* /tmp/conda/

%%post
    mkdir -p /usr/local
    cp -R /tmp/conda/* /usr/local/

%%test
    %(container_test)s
"""


def involucro_link():
    if IS_OS_X:
        url = "https://github.com/involucro/involucro/releases/download/v%s/involucro.darwin" % INVOLUCRO_VERSION
    else:
        url = "https://github.com/involucro/involucro/releases/download/v%s/involucro" % INVOLUCRO_VERSION
    return url


def get_tests(args, pkg_path):
    """Extract test cases given a recipe's meta.yaml file."""
    recipes_dir = args.recipes_dir

    tests = []
    input_dir = os.path.dirname(os.path.join(recipes_dir, pkg_path))
    recipe_meta = MetaData(input_dir)

    tests_commands = recipe_meta.get_value('test/commands')
    tests_imports = recipe_meta.get_value('test/imports')
    requirements = recipe_meta.get_value('requirements/run')

    if tests_imports or tests_commands:
        if tests_commands:
            tests.append(' && '.join(tests_commands))
        if tests_imports and 'python' in requirements:
            tests.append(' && '.join('python -c "import %s"' % imp for imp in tests_imports))
        elif tests_imports and ('perl' in requirements or 'perl-threaded' in requirements):
            tests.append(' && '.join('''perl -e "use %s;"''' % imp for imp in tests_imports))

    tests = ' && '.join(tests)
    tests = tests.replace('$R ', 'Rscript ')
    return tests


def get_pkg_name(args, pkg_path):
    """Extract the package name from a given meta.yaml file."""
    recipes_dir = args.recipes_dir

    input_dir = os.path.dirname(os.path.join(recipes_dir, pkg_path))
    recipe_meta = MetaData(input_dir)
    return recipe_meta.get_value('package/name')


def get_affected_packages(args):
    """Return a list of all meta.yaml file that where modified/created recently.

    Length of time to check for indicated by the ``hours`` parameter.
    """
    recipes_dir = args.recipes_dir
    hours = args.diff_hours
    cmd = """cd '%s' && git log --diff-filter=ACMRTUXB --name-only --pretty="" --since="%s hours ago" | grep -E '^recipes/.*/meta.yaml' | sort | uniq""" % (recipes_dir, hours)
    pkg_list = check_output(cmd, shell=True)
    ret = list()
    for pkg in pkg_list.strip().split('\n'):
        if pkg and os.path.exists(os.path.join( recipes_dir, pkg )):
            ret.append( (get_pkg_name(args, pkg), get_tests(args, pkg)) )
    return ret


def check_output(cmd, shell=True):
    return subprocess.check_output(cmd, shell=shell)


def conda_versions(pkg_name, file_name):
    """Return all conda version strings for a specified package name."""
    j = json.load(open(file_name))
    ret = list()
    for pkg in j['packages'].values():
        if pkg['name'] == pkg_name:
            ret.append('%s--%s' % (pkg['version'], pkg['build']))
    return ret


class BuildExistsException(Exception):
    """Exception indicating mull_targets is skipping an existing build.

    If mull_targets is called with rebuild=False and the target built is already published
    an instance of this exception is thrown.
    """


def mull_targets(
    targets, involucro_context=None,
    command="build", channels=DEFAULT_CHANNELS, namespace="biocontainers",
    test='true', test_files=None, image_build=None, name_override=None,
    repository_template=DEFAULT_REPOSITORY_TEMPLATE, dry_run=False,
    conda_version=None, verbose=False, binds=DEFAULT_BINDS, rebuild=True,
    oauth_token=None, hash_func="v2", singularity=False,
):
    targets = list(targets)
    if involucro_context is None:
        involucro_context = InvolucroContext()

    image_function = v1_image_name if hash_func == "v1" else v2_image_name
    if len(targets) > 2 and image_build is None:
        # Force an image build in this case - this seems hacky probably
        # shouldn't work this way but single case broken else wise.
        image_build = "0"

    repo_template_kwds = {
        "namespace": namespace,
        "image": image_function(targets, image_build=image_build, name_override=name_override)
    }
    repo = string.Template(repository_template).safe_substitute(repo_template_kwds)

    if not rebuild or "push" in command:
        repo_name = repo_template_kwds["image"].split(":", 1)[0]
        repo_data = quay_repository(repo_template_kwds["namespace"], repo_name)
        if not rebuild:
            tags = repo_data.get("tags", [])

            target_tag = None
            if ":" in repo_template_kwds["image"]:
                image_name_parts = repo_template_kwds["image"].split(":")
                assert len(image_name_parts) == 2, ": not allowed in image name [%s]" % repo_template_kwds["image"]
                target_tag = image_name_parts[1]

            if tags and (target_tag is None or target_tag in tags):
                raise BuildExistsException()
        if "push" in command and "error_type" in repo_data and oauth_token:
            # Explicitly create the repository so it can be built as public.
            create_repository(repo_template_kwds["namespace"], repo_name, oauth_token)

    for channel in channels:
        if channel.startswith('file://'):
            bind_path = channel.lstrip('file://')
            binds.append('/%s:/%s' % (bind_path, bind_path))

    channels = ",".join(channels)
    target_str = ",".join(map(conda_build_target_str, targets))
    bind_str = ",".join(binds)
    involucro_args = [
        '-f', '%s/invfile.lua' % DIRNAME,
        '-set', "CHANNELS='%s'" % channels,
        '-set', "TEST='%s'" % test,
        '-set', "TARGETS='%s'" % target_str,
        '-set', "REPO='%s'" % repo,
        '-set', "BINDS='%s'" % bind_str,
    ]

    if DEST_BASE_IMAGE:
        involucro_args.extend(["-set", "DEST_BASE_IMAGE='%s'" % DEST_BASE_IMAGE])
    if verbose:
        involucro_args.extend(["-set", "VERBOSE='1'"])
    if singularity:
        singularity_image_name = repo_template_kwds['image']
        involucro_args.extend(["-set", "SINGULARITY='1'"])
        involucro_args.extend(["-set", "SINGULARITY_IMAGE_NAME='%s'" % singularity_image_name])
        involucro_args.extend(["-set", "USER_ID='%s:%s'" % (os.getuid(), os.getgid() )])
    if conda_version is not None:
        verbose = "--verbose" if verbose else "--quiet"
        involucro_args.extend(["-set", "PREINSTALL='conda install %s --yes conda=%s'" % (verbose, conda_version)])
    involucro_args.append(command)
    if test_files:
        test_bind = []
        for test_file in test_files:
            if ':' not in test_file:
                if os.path.exists(test_file):
                    test_bind.append("%s:%s/%s" % (test_file, DEFAULT_WORKING_DIR, test_file))
            else:
                if os.path.exists(test_file.split(':')[0]):
                    test_bind.append(test_file)
        if test_bind:
            involucro_args.insert(6, '-set')
            involucro_args.insert(7, "TEST_BINDS='%s'" % ",".join(test_bind))
    print(" ".join(involucro_context.build_command(involucro_args)))
    if not dry_run:
        ensure_installed(involucro_context, True)
        if singularity:
            if not os.path.exists('./singularity_import'):
                os.mkdir('./singularity_import')
            with open('./singularity_import/Singularity', 'w+') as sin_def:
                fill_template = SINGULARITY_TEMPLATE % {'container_test': test}
                sin_def.write(fill_template)
        ret = involucro_context.exec_command(involucro_args)
        if singularity:
            # we can not remove this folder as it contains the image wich is owned by root
            pass
            # shutil.rmtree('./singularity_import')
        return ret
    return 0


def context_from_args(args):
    verbose = "2" if not args.verbose else "3"
    return InvolucroContext(involucro_bin=args.involucro_path, verbose=verbose)


class InvolucroContext(installable.InstallableContext):

    installable_description = "Involucro"

    def __init__(self, involucro_bin=None, shell_exec=None, verbose="3"):
        if involucro_bin is None:
            if os.path.exists("./involucro"):
                self.involucro_bin = "./involucro"
            else:
                self.involucro_bin = "involucro"
        else:
            self.involucro_bin = involucro_bin
        self.shell_exec = shell_exec or commands.shell
        self.verbose = verbose

    def build_command(self, involucro_args):
        return [self.involucro_bin, "-v=%s" % self.verbose] + involucro_args

    def exec_command(self, involucro_args):
        cmd = self.build_command(involucro_args)
        # Create ./build dir manually, otherwise Docker will do it as root
        os.mkdir('./build')
        try:
            res = self.shell_exec(" ".join(cmd))
        finally:
            # delete build directory in any case
            shutil.rmtree('./build')
        return res

    def is_installed(self):
        return os.path.exists(self.involucro_bin)

    def can_install(self):
        return True

    @property
    def parent_path(self):
        return os.path.dirname(os.path.abspath(self.involucro_bin))


def ensure_installed(involucro_context, auto_init):
    return installable.ensure_installed(involucro_context, install_involucro, auto_init)


def install_involucro(involucro_context=None, to_path=None):
    install_path = os.path.abspath(involucro_context.involucro_bin)
    involucro_context.involucro_bin = install_path
    download_cmd = " ".join(commands.download_command(involucro_link(), to=install_path, quote_url=True))
    full_cmd = "%s && chmod +x %s" % (download_cmd, install_path)
    return involucro_context.shell_exec(full_cmd)


def add_build_arguments(parser):
    """Base arguments describing how to 'mull'."""
    parser.add_argument('--involucro-path', dest="involucro_path", default=None,
                        help="Path to involucro (if not set will look in working directory and on PATH).")
    parser.add_argument('--dry-run', dest='dry_run', action="store_true",
                        help='Just print commands instead of executing them.')
    parser.add_argument('--verbose', dest='verbose', action="store_true",
                        help='Cause process to be verbose.')
    parser.add_argument('--singularity', action="store_true",
                        help='Additionally build a singularity image.')
    parser.add_argument('-n', '--namespace', dest='namespace', default="biocontainers",
                        help='quay.io namespace.')
    parser.add_argument('-r', '--repository_template', dest='repository_template', default=DEFAULT_REPOSITORY_TEMPLATE,
                        help='Docker repository target for publication (only quay.io or compat. API is currently supported).')
    parser.add_argument('-c', '--channel', dest='channel', default=DEFAULT_CHANNEL,
                        help='Target conda channel')
    parser.add_argument('--extra-channels', dest='extra_channels', default=",".join(DEFAULT_EXTRA_CHANNELS),
                        help='Dependent conda channels.')
    parser.add_argument('--conda-version', dest="conda_version", default=None,
                        help="Change to specified version of Conda before installing packages.")
    parser.add_argument('--oauth-token', dest="oauth_token", default=None,
                        help="If set, use this token when communicating with quay.io API.")
    parser.add_argument('--check-published', dest="rebuild", action='store_false')
    parser.add_argument('--hash', dest="hash", choices=["v1", "v2"], default="v2")


def add_single_image_arguments(parser):
    parser.add_argument("--name-override", dest="name_override", default=None,
                        help="Override mulled image name - this is not recommended since metadata will not be detectable from the name of resulting images")
    parser.add_argument("--image-build", dest="image_build", default=None,
                        help="Build a versioned variant of this image.")


def target_str_to_targets(targets_raw):
    def parse_target(target_str):
        if "=" in target_str:
            package_name, version = target_str.split("=", 1)
            build = None
            if "--" in version:
                version, build = version.split('--')
            target = build_target(package_name, version, build)
        else:
            target = build_target(target_str)
        return target

    targets = [parse_target(_) for _ in targets_raw.split(",")]
    return targets


def args_to_mull_targets_kwds(args):
    kwds = {}
    if hasattr(args, "image_build"):
        kwds["image_build"] = args.image_build
    if hasattr(args, "name_override"):
        kwds["name_override"] = args.name_override
    if hasattr(args, "namespace"):
        kwds["namespace"] = args.namespace
    if hasattr(args, "dry_run"):
        kwds["dry_run"] = args.dry_run
    if hasattr(args, "singularity"):
        kwds["singularity"] = args.singularity
    if hasattr(args, "test"):
        kwds["test"] = args.test
    if hasattr(args, "test_files"):
        if args.test_files:
            kwds["test_files"] = args.test_files.split(",")
    if hasattr(args, "channel"):
        channels = [args.channel]
        if hasattr(args, "extra_channels"):
            channels += args.extra_channels.split(",")
        kwds["channels"] = channels
    if hasattr(args, "command"):
        kwds["command"] = args.command
    if hasattr(args, "repository_template"):
        kwds["repository_template"] = args.repository_template
    if hasattr(args, "conda_version"):
        kwds["conda_version"] = args.conda_version
    if hasattr(args, "oauth_token"):
        kwds["oauth_token"] = args.oauth_token
    if hasattr(args, "rebuild"):
        kwds["rebuild"] = args.rebuild
    if hasattr(args, "hash"):
        kwds["hash_func"] = args.hash

    kwds["involucro_context"] = context_from_args(args)

    return kwds


def main(argv=None):
    """Main entry-point for the CLI tool."""
    parser = arg_parser(argv, globals())
    add_build_arguments(parser)
    add_single_image_arguments(parser)
    parser.add_argument('command', metavar='COMMAND', help='Command (build-and-test, build, all)')
    parser.add_argument('targets', metavar="TARGETS", default=None, help="Build a single container with specific package(s).")
    parser.add_argument('--repository-name', dest="repository_name", default=None, help="Name of mulled container (leave blank to auto-generate based on packages - recommended).")
    parser.add_argument('--test', help='Provide a test command for the container.')
    parser.add_argument('--test-files', help='Provide test-files that may be required to run the test command. Individual mounts are separated by comma.'
                                             'The source:dest docker syntax is respected. If relative file paths are given, files will be mounted in /source/<relative_file_path>')
    args = parser.parse_args()
    targets = target_str_to_targets(args.targets)
    sys.exit(mull_targets(targets, **args_to_mull_targets_kwds(args)))


__all__ = ("main", )


if __name__ == '__main__':
    main()
