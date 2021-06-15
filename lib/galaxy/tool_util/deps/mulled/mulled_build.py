#!/usr/bin/env python
"""Build a mulled image for specified conda targets.

Examples

Build a mulled image with:

    mulled-build build 'samtools=1.3.1--4,bedtools=2.22'

"""

import json
import logging
import os
import shlex
import shutil
import stat
import string
import subprocess
import sys
from sys import platform as _platform

import yaml

from galaxy.tool_util.deps import installable
from galaxy.tool_util.deps.conda_util import best_search_result
from galaxy.tool_util.deps.docker_util import command_list as docker_command_list
from galaxy.util import (
    commands,
    safe_makedirs,
    unicodify,
)
from ._cli import arg_parser
from .util import (
    build_target,
    conda_build_target_str,
    create_repository,
    get_file_from_recipe_url,
    PrintProgress,
    quay_repository,
    v1_image_name,
    v2_image_name,
)
from ..conda_compat import MetaData

log = logging.getLogger(__name__)

DIRNAME = os.path.dirname(__file__)
DEFAULT_BASE_IMAGE = os.environ.get("DEFAULT_BASE_IMAGE", "quay.io/bioconda/base-glibc-busybox-bash:latest")
DEFAULT_EXTENDED_BASE_IMAGE = os.environ.get("DEFAULT_EXTENDED_BASE_IMAGE", "quay.io/bioconda/base-glibc-debian-bash:latest")
if 'DEFAULT_MULLED_CONDA_CHANNELS' in os.environ:
    DEFAULT_CHANNELS = os.environ['DEFAULT_MULLED_CONDA_CHANNELS'].split(',')
else:
    DEFAULT_CHANNELS = ["conda-forge", "bioconda"]
DEFAULT_REPOSITORY_TEMPLATE = "quay.io/${namespace}/${image}"
DEFAULT_BINDS = ["build/dist:/usr/local/"]
DEFAULT_WORKING_DIR = '/source/'
IS_OS_X = _platform == "darwin"
INVOLUCRO_VERSION = "1.1.2"
DEST_BASE_IMAGE = os.environ.get('DEST_BASE_IMAGE', None)
CONDA_IMAGE = os.environ.get('CONDA_IMAGE', None)

SINGULARITY_TEMPLATE = """Bootstrap: docker
From: %(base_image)s

%%setup

    echo "Copying conda environment"
    mkdir -p /tmp/conda
    cp -r /data/dist/* /tmp/conda/

%%post
    rm -R /usr/local || true
    mkdir -p /usr/local
    cp -R /tmp/conda/* /usr/local/

%%test
    %(container_test)s
"""


def involucro_link():
    if IS_OS_X:
        url = f"https://github.com/mvdbeek/involucro/releases/download/v{INVOLUCRO_VERSION}/involucro.darwin"
    else:
        url = f"https://github.com/involucro/involucro/releases/download/v{INVOLUCRO_VERSION}/involucro"
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
            tests.append(' && '.join(f'python -c "import {imp}"' for imp in tests_imports))
        elif tests_imports and ('perl' in requirements or 'perl-threaded' in requirements):
            tests.append(' && '.join(f'''perl -e "use {imp};\"''' for imp in tests_imports))

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
    cmd = ['git', 'log', '--diff-filter=ACMRTUXB', '--name-only', '--pretty=""', f'--since="{hours} hours ago"']
    changed_files = unicodify(subprocess.check_output(cmd, cwd=recipes_dir)).splitlines()
    pkg_list = {x for x in changed_files if x.startswith('recipes/') and x.endswith('meta.yaml')}
    for pkg in pkg_list:
        if pkg and os.path.exists(os.path.join(recipes_dir, pkg)):
            yield (get_pkg_name(args, pkg), get_tests(args, pkg))


def conda_versions(pkg_name, file_name):
    """Return all conda version strings for a specified package name."""
    j = json.load(open(file_name))
    ret = list()
    for pkg in j['packages'].values():
        if pkg['name'] == pkg_name:
            ret.append(f"{pkg['version']}--{pkg['build']}")
    return ret


def get_conda_hits_for_targets(targets, conda_context):
    search_results = (best_search_result(t, conda_context, platform='linux-64')[0] for t in targets)
    return [r for r in search_results if r]


def base_image_for_targets(targets, conda_context=None):
    hits = get_conda_hits_for_targets(targets, conda_context or CondaInDockerContext())
    for hit in hits:
        try:
            tarball = get_file_from_recipe_url(hit['url'])
            meta_content = unicodify(tarball.extractfile('info/about.json').read())
            if json.loads(meta_content).get('extra', {}).get('container', {}).get('extended-base', False):
                return DEFAULT_EXTENDED_BASE_IMAGE
            elif yaml.safe_load(unicodify(tarball.extractfile('info/recipe/meta.yaml').read())).get('extra', {}).get('container', {}).get('extended-base', False):
                return DEFAULT_EXTENDED_BASE_IMAGE
        except Exception:
            log.warning("Could not load metadata.yaml for '%s', version '%s'", hit['name'], hit['version'], exc_info=True)
    return DEFAULT_BASE_IMAGE


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
    singularity_image_dir="singularity_import", base_image=None,
    determine_base_image=True,
):
    targets = list(targets)
    if involucro_context is None:
        involucro_context = InvolucroContext()

    image_function = v1_image_name if hash_func == "v1" else v2_image_name
    if len(targets) > 1 and image_build is None:
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
                assert len(image_name_parts) == 2, f": not allowed in image name [{repo_template_kwds['image']}]"
                target_tag = image_name_parts[1]

            if tags and (target_tag is None or target_tag in tags):
                raise BuildExistsException()
        if "push" in command and "error_type" in repo_data and oauth_token:
            # Explicitly create the repository so it can be built as public.
            create_repository(repo_template_kwds["namespace"], repo_name, oauth_token)

    for channel in channels:
        if channel.startswith('file://'):
            bind_path = channel[7:]
            binds.append(f'/{bind_path}:/{bind_path}')

    channels = ",".join(channels)
    target_str = ",".join(map(conda_build_target_str, targets))
    bind_str = ",".join(binds)
    involucro_args = [
        '-f', f'{DIRNAME}/invfile.lua',
        '-set', f"CHANNELS={channels}",
        '-set', f"TARGETS={target_str}",
        '-set', f"REPO={repo}",
        '-set', f"BINDS={bind_str}",
    ]
    dest_base_image = None
    if base_image:
        dest_base_image = base_image
    elif DEST_BASE_IMAGE:
        dest_base_image = DEST_BASE_IMAGE
    elif determine_base_image:
        dest_base_image = base_image_for_targets(targets)

    if dest_base_image:
        involucro_args.extend(["-set", f"DEST_BASE_IMAGE={dest_base_image}"])
    if CONDA_IMAGE:
        involucro_args.extend(["-set", f"CONDA_IMAGE={CONDA_IMAGE}"])
    if verbose:
        involucro_args.extend(["-set", "VERBOSE=1"])
    if singularity:
        singularity_image_name = repo_template_kwds['image']
        involucro_args.extend(["-set", "SINGULARITY=1"])
        involucro_args.extend(["-set", f"SINGULARITY_IMAGE_NAME={singularity_image_name}"])
        involucro_args.extend(["-set", f"SINGULARITY_IMAGE_DIR={singularity_image_dir}"])
        involucro_args.extend(["-set", f"USER_ID={os.getuid()}:{os.getgid()}"])
    if test:
        involucro_args.extend(["-set", f"TEST={test}"])
    if conda_version is not None:
        verbose = "--verbose" if verbose else "--quiet"
        involucro_args.extend(["-set", f"PREINSTALL=conda install {verbose} --yes conda={conda_version}"])
    involucro_args.append(command)
    if test_files:
        test_bind = []
        for test_file in test_files:
            if ':' not in test_file:
                if os.path.exists(test_file):
                    test_bind.append(f"{test_file}:{DEFAULT_WORKING_DIR}/{test_file}")
            else:
                if os.path.exists(test_file.split(':')[0]):
                    test_bind.append(test_file)
        if test_bind:
            involucro_args.insert(6, '-set')
            involucro_args.insert(7, f"TEST_BINDS={','.join(test_bind)}")
    cmd = involucro_context.build_command(involucro_args)
    print(f"Executing: {' '.join(shlex.quote(_) for _ in cmd)}")
    if dry_run:
        return 0
    ensure_installed(involucro_context, True)
    if singularity:
        if not os.path.exists(singularity_image_dir):
            safe_makedirs(singularity_image_dir)
        with open(os.path.join(singularity_image_dir, 'Singularity.def'), 'w+') as sin_def:
            fill_template = SINGULARITY_TEMPLATE % {'container_test': test, 'base_image': dest_base_image or DEFAULT_BASE_IMAGE}
            sin_def.write(fill_template)
    with PrintProgress():
        ret = involucro_context.exec_command(involucro_args)
    if singularity:
        # we can not remove this folder as it contains the image wich is owned by root
        pass
        # shutil.rmtree('./singularity_import')
    return ret


def context_from_args(args):
    verbose = "2" if not args.verbose else "3"
    return InvolucroContext(involucro_bin=args.involucro_path, verbose=verbose)


class CondaInDockerContext:

    @property
    def conda_exec(self):
        conda_image = CONDA_IMAGE or 'continuumio/miniconda3:latest'
        return docker_command_list('run', [conda_image, 'conda'])

    @property
    def _override_channels_args(self):
        override_channels_args = ['--override-channels']
        for channel in DEFAULT_CHANNELS:
            override_channels_args.extend(["--channel", channel])
        return override_channels_args


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
        return [self.involucro_bin, f"-v={self.verbose}"] + involucro_args

    def exec_command(self, involucro_args):
        cmd = self.build_command(involucro_args)
        # Create ./build dir manually, otherwise Docker will do it as root
        created_build_dir = False
        if not os.path.exists('build'):
            created_build_dir = True
            os.mkdir('./build')
        try:
            res = self.shell_exec(cmd)
        finally:
            # delete build directory in any case
            if created_build_dir:
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


def install_involucro(involucro_context):
    install_path = os.path.abspath(involucro_context.involucro_bin)
    involucro_context.involucro_bin = install_path
    download_cmd = commands.download_command(involucro_link(), to=install_path)
    exit_code = involucro_context.shell_exec(download_cmd)
    if exit_code:
        return exit_code
    try:
        os.chmod(install_path, os.stat(install_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return 0
    except Exception:
        log.exception("Failed to make file '%s' executable", install_path)
        return 1


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
    parser.add_argument('--singularity-image-dir', dest="singularity_image_dir",
                        help="Directory to write singularity images too.")
    parser.add_argument('-n', '--namespace', dest='namespace', default="biocontainers",
                        help='quay.io namespace.')
    parser.add_argument('-r', '--repository_template', dest='repository_template', default=DEFAULT_REPOSITORY_TEMPLATE,
                        help='Docker repository target for publication (only quay.io or compat. API is currently supported).')
    parser.add_argument('-c', '--channels', dest='channels', default=",".join(DEFAULT_CHANNELS),
                        help='Comma separated list of target conda channels.')
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
            if "=" in version:
                version, build = version.split('=')
            elif "--" in version:
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
    if hasattr(args, "channels"):
        kwds["channels"] = args.channels.split(',')
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
    if hasattr(args, "singularity_image_dir") and args.singularity_image_dir:
        kwds["singularity_image_dir"] = args.singularity_image_dir

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
