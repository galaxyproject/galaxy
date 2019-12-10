import collections
import logging
import os
import shlex
import subprocess
import tempfile
from string import Template

from galaxy.tool_util.deps.mulled.mulled_build import DEFAULT_CHANNELS
from galaxy.util import unicodify

log = logging.Logger(__name__)

DOCKERFILE_INITIAL_BUILD = Template("""FROM $BUILDIMAGE
$PREINSTALL
RUN conda install $CHANNEL_ARGS $TARGET_ARGS -p /usr/local --copy --yes $VERBOSE
$POSTINSTALL""")
DOCKERFILE_BUILD_TO_DESTINATION = Template("""FROM $DESTINATION_IMAGE
COPY --from=0 /usr/local /usr/local
$ENV_STATEMENTS""")
DEFAULT_BUILDIMAGE = "continuumio/miniconda3:latest"
DEFAULT_DESTINATION_IMAGE = "bgruening/busybox-bash:0.1"
DEFAULT_EXTENDED_BASE_IMAGE = "bioconda/extended-base-image:latest"
DOCKERFILE_INFO = collections.namedtuple("DockerfileInfo", "contents path repo build_command")


def get_docker_info(contents, repo):
    dockerfile_path = write_dockerfile(contents, repo)
    CMD = ['docker', 'build', '-t', repo, os.path.dirname(dockerfile_path)]
    return DOCKERFILE_INFO(contents=contents, path=dockerfile_path, repo=repo, build_command=CMD)


def write_dockerfile(contents, repo):
    initial_build_dir = tempfile.mkdtemp(prefix="docker_build_%s" % shlex.quote(repo))
    dockerfile_path = os.path.join(initial_build_dir, "Dockerfile") 
    with open(dockerfile_path, "w") as dockerfile:
        dockerfile.write(contents)
    return dockerfile_path


def build_image(dockerfile_info):
    try:
        subprocess.check_call(dockerfile_info.build_command, stderr=subprocess.STDOUT)
    except Exception as e:
        error_message = "Error building docker image"
        if isinstance(e, subprocess.CalledProcessError):
            error_message += "\nOutput was:\n%s" % e.output
        raise Exception(error_message)


def run_in_container(image, command):
    CMD = ['docker', "run", image]
    CMD.extend(command)
    return unicodify(subprocess.check_output(CMD, stderr=subprocess.STDOUT))


def image_requires_extended_base(image):
    output = run_in_container(image=image, command=[
        "find",
        "/opt/conda/pkgs",
        "-name",
        "meta.yaml",
        "-exec",
        "grep",
        "extended-base: true",
        "{}",
        ";",
    ])
    return output.strip() == 'extended-base: true'


def collect_conda_env_vars(image):
    original_variables = run_in_container(image=image, command=["bash", "-c", 'source activate base && env'])
    new_variables = run_in_container(image=image, command=["bash", "-c", 'source activate /usr/local && env'])
    original_variables = dict(line.split('=') for line in original_variables.splitlines())
    new_variables = dict(line.split('=') for line in new_variables.splitlines())
    new_keys = set(new_variables) - set(original_variables)
    return {k: new_variables[k] for k in new_keys}


def build_initial_docker_info(
        repo,
        target_args,
        builder_image=DEFAULT_BUILDIMAGE,
        preinstall='',
        channels=DEFAULT_CHANNELS,
        verbose=False,
        postinstall=''):
    """
    Installs Conda packages using the official Miniconda Docker image.
    """
    if preinstall:
        preinstall = "RUN %s &&" % preinstall
    if postinstall:
        postinstall = "RUN %s &&" % postinstall
    if verbose:
        verbose = '--verbose'
    else:
        verbose = ''
    channels_args = " ".join(("-c %s" % c for c in channels))
    dockerfile_contents = DOCKERFILE_INITIAL_BUILD.substitute(
        BUILDIMAGE=builder_image,
        PREINSTALL=preinstall,
        CHANNEL_ARGS=channels_args,
        TARGET_ARGS=target_args,
        VERBOSE=verbose,
        POSTINSTALL=postinstall,
    )
    log.info("Building image for following Dockerfile:\n%s", dockerfile_contents)
    return get_docker_info(dockerfile_contents, repo)


def build_destination_docker_info(initial_dockerfile_info, destination_image, env_statements):
    second_stage_contents = DOCKERFILE_BUILD_TO_DESTINATION.substitute(
        DESTINATION_IMAGE=destination_image,
        ENV_STATEMENTS=env_statements,
    )
    dockerfile_contents = "%s\n%s" % (initial_dockerfile_info.contents, second_stage_contents)
    return get_docker_info(dockerfile_contents, initial_dockerfile_info.repo)


def get_destination_docker_info(dockerfile_info, destination_image=None):
    env_vars = collect_conda_env_vars(dockerfile_info.repo)
    env_statements = "\n".join(["ENV {k} {v}\n".format(k=k, v=v) for k, v in env_vars.items()])
    if destination_image is None:
        destination_image = DEFAULT_EXTENDED_BASE_IMAGE if image_requires_extended_base(dockerfile_info.repo) else DEFAULT_DESTINATION_IMAGE
    return build_destination_docker_info(
        initial_dockerfile_info=dockerfile_info,
        destination_image=destination_image,
        env_statements=env_statements,
    )
