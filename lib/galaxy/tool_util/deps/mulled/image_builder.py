import collections
import logging
import os
import shlex
import tempfile
from string import Template

from galaxy.tool_util.deps.commands import (
    execute,
    shell_process,
)
from galaxy.tool_util.deps.docker_util import (
    build_command as docker_build_command,
    command_list as docker_command_list,
)
from galaxy.tool_util.deps.mulled.mulled_build import DEFAULT_CHANNELS
from galaxy.tool_util.deps.singularity_util import (
    build_command as singularity_build_command,
    command_list as singularity_command_list,
)
from galaxy.util import unicodify

log = logging.Logger(__name__)

DOCKERFILE_INITIAL_BUILD = Template("""FROM $BUILDIMAGE
$PREINSTALL
RUN conda install $CHANNEL_ARGS $TARGET_ARGS -p /usr/local --copy --yes $VERBOSE
$POSTINSTALL""")
DOCKERFILE_BUILD_TO_DESTINATION = Template("""FROM $DESTINATION_IMAGE
COPY --from=0 /usr/local /usr/local
$ENV_STATEMENTS""")
SINGULARITY_INITIAL_BUILD = Template("""Bootstrap: docker
From: $BUILDIMAGE
Stage: build
%post
    $PREINSTALL
    /opt/conda/bin/conda install $CHANNEL_ARGS $TARGET_ARGS -p /usr/local --copy --yes $VERBOSE
    $POSTINSTALL
%test
    true
""")
SINGULARITY_BUILD_TO_DESTINATION = Template("""Bootstrap: docker
From: $DESTINATION_IMAGE
Stage: final

# install binary from stage one
%files from build
  /usr/local /usr/local
$ENV_STATEMENTS""")
DEFAULT_BUILDIMAGE = "continuumio/miniconda3:latest"
DEFAULT_DESTINATION_IMAGE = "bgruening/busybox-bash:0.1"
DEFAULT_EXTENDED_BASE_IMAGE = "bioconda/extended-base-image:latest"
IMAGE_INFO = collections.namedtuple("ImageInfo", "contents path repo build_command")
# TODO: generalize to docker + singularity
# TODO: enable tests in containers
# TODO: add build context
# TODO: cli


class DockerContainerBuilder(object):
    """Builds docker containers whose software is installed by Conda."""

    first_stage_template = DOCKERFILE_INITIAL_BUILD
    second_stage_template = DOCKERFILE_BUILD_TO_DESTINATION
    recipe = 'Dockerfile'
    container_type = 'docker'
    run_prefix = "RUN "

    def __init__(self,
                 repo,
                 target_args,
                 builder_image=DEFAULT_BUILDIMAGE,
                 preinstall='',
                 channels=DEFAULT_CHANNELS,
                 verbose=False,
                 postinstall='',
                 destination_image=None,
                 artifact_dir=None,
                 ):
        self.repo = repo
        self.target_args = target_args
        self.builder_image = builder_image
        self.preinstall = preinstall
        self.channels = channels
        self.verbose = verbose
        self.postinstall = postinstall
        self.destination_image = destination_image
        self._artifact_dir = artifact_dir
        self.recipe_stage1 = None
        self.recipe_stage2 = None

    @property
    def image(self):
        return self.repo

    def build_command(self, path):
        return docker_build_command(image=self.image, docker_build_path=path)

    def run_command(self, command):
        command.insert(0, self.image)
        return docker_command_list('run', command)

    def exec_command(self, command, redirect_output=False):
        if redirect_output:
            p = shell_process(command)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                raise Exception("Executing command '%s' failed with exit code %d" % (" ".join(command), p.returncode))
        else:
            return unicodify(execute(command))

    @property
    def artifact_dir(self):
        if self._artifact_dir is None:
            self._artifact_dir = tempfile.mkdtemp(prefix="%s_%s" % (self.container_type, shlex.quote(self.repo)))
        return self._artifact_dir

    def write_recipe(self, recipe_contents):
        recipe_path = os.path.join(self.artifact_dir, self.recipe)
        with open(recipe_path, "w") as recipe:
            recipe.write(recipe_contents)
        return recipe_path

    def template_stage1(self):
        if self.preinstall:
            self.preinstall = "%s%s &&" % (self.run_prefix, self.preinstall)
        if self.postinstall:
            self.postinstall = "%s%s &&" % (self.run_prefix, self.postinstall)
        if self.verbose:
            verbose = '--verbose'
        else:
            verbose = ''
        channels_args = " ".join(("-c %s" % c for c in self.channels))
        recipe_contents = self.first_stage_template.substitute(
            BUILDIMAGE=self.builder_image,
            PREINSTALL=self.preinstall,
            CHANNEL_ARGS=channels_args,
            TARGET_ARGS=self.target_args,
            VERBOSE=verbose,
            POSTINSTALL=self.postinstall,
        )
        log.info("Building image for Dockerfile contents:\n%s", recipe_contents)
        return recipe_contents

    def build_info(self, template_function):
        recipe_contents = template_function()
        recipe_path = self.write_recipe(recipe_contents)
        build_command = self.build_command(recipe_path)
        return IMAGE_INFO(contents=recipe_contents, path=recipe_path, repo=self.repo, build_command=build_command)

    def run_in_container(self, command):
        return self.exec_command(self.run_command(command))

    def image_requires_extended_base(self):
        output = self.run_in_container(command=[
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

    def get_conda_env_vars(self):
        original_variables = self.run_in_container(command=["bash", "-c", 'source /opt/conda/bin/activate base && env'])
        new_variables = self.run_in_container(command=["bash", "-c", 'source /opt/conda/bin/activate /usr/local && env'])
        original_variables = dict(line.split('=') for line in original_variables.splitlines())
        new_variables = dict(line.split('=') for line in new_variables.splitlines())
        new_keys = set(new_variables) - set(original_variables)
        return {k: new_variables[k] for k in new_keys}

    def template_env_vars(self, env_vars):
        return "\n".join(["ENV {k} {v}\n".format(k=k, v=v) for k, v in env_vars.items()])

    def get_destination_image(self):
        if self.destination_image:
            return self.destination_image
        else:
            return DEFAULT_EXTENDED_BASE_IMAGE if self.image_requires_extended_base() else DEFAULT_DESTINATION_IMAGE

    def template_stage2(self):
        destination_image = self.get_destination_image()
        conda_env_vars = self.get_conda_env_vars()
        env_statements = self.template_env_vars(conda_env_vars)
        second_stage_contents = self.second_stage_template.substitute(
            DESTINATION_IMAGE=destination_image,
            ENV_STATEMENTS=env_statements,
        )
        dockerfile_contents = "%s\n%s" % (self.recipe_stage1.contents, second_stage_contents)
        return dockerfile_contents

    def build_stage(self, stage):
        return self.exec_command(stage.build_command, redirect_output=True)

    def build_image(self):
        self.recipe_stage1 = self.build_info(self.template_stage1)
        self.build_stage(self.recipe_stage1)
        self.recipe_stage2 = self.build_info(self.template_stage2)
        self.build_stage(self.recipe_stage2)


class SingularityContainerBuilder(DockerContainerBuilder):

    first_stage_template = SINGULARITY_INITIAL_BUILD
    second_stage_template = SINGULARITY_BUILD_TO_DESTINATION
    recipe = "singularity.def"
    container_type = "singularity"
    run_prefix = ""

    @property
    def image(self):
        return os.path.join(self.artifact_dir, "%s.sif" % self.repo)

    def build_command(self, path):
        return singularity_build_command(self.image, path)

    def run_command(self, command):
        command.insert(0, self.image)
        return singularity_command_list('exec', command)

    def template_env_vars(self, env_vars):
        return "%environment\n" + "\n".join(["    export {k}={v}\n".format(k=k, v=v) for k, v in env_vars.items()])
