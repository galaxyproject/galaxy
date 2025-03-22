import os
from dataclasses import dataclass
from textwrap import indent
from typing import (
    Dict,
    Iterable,
    List,
    Optional,
)

import yaml

from galaxy.util.container_volumes import DockerVolume
from .arg_parsing import config_args
from .templates import render
from .types import (
    ConfigArgs,
    Runner,
)

TEMPLATE = """
runners:
  local:
    load: galaxy.jobs.runners.local:LocalJobRunner
    # modify the number of threads working on local jobs here
    # workers: 4
{{ additional_runners }}
handling:
  assign:
    - db-skip-locked

execution:
  default: {{ default_environment }}
  environments:{{ local_environment }}{{ additional_environments }}
tools:
  - class: local
    environment: local
"""

DRMAA_RUNNER_TEMPLATE = """
  drmaa:
    load: galaxy.jobs.runners.drmaa:DRMAAJobRunner
    # modify below to specify a specific drmaa shared library
    # drmaa_library_path: /sge/lib/libdrmaa.so
"""

SLURM_RUNNER_TEMPLATE = """
  slurm:
    load: galaxy.jobs.runners.slurm:SlurmJobRunner
    # modify below to specify a specific drmaa shared library for slurm
    # drmaa_library_path: /usr/lib/slurm-drmaa/lib/libdrmaa.so.1
"""

CONDOR_RUNNER_TEMPLATE = """
  condor:
    load: galaxy.jobs.runners.condor:CondorJobRunner
"""

K8S_RUNNER_TEMPLATE = """
  k8s:
    load: galaxy.jobs.runners.kubernetes:KubernetesJobRunner
"""

DRMAA_ENVIRONMENT_TEMPLATE = """
    drmaa:
      runner: drmaa
      native_specification: "" """

SLURM_ENVIRONMENT_TEMPLATE = """
    # Information on connecting Galaxy to SLURM can be found at:
    # https://training.galaxyproject.org/training-material/topics/admin/tutorials/connect-to-compute-cluster/tutorial.html
    slurm:
      runner: slurm
      native_specification: "" """

CONDOR_ENVIRONMENT_TEMPLATE = """
    condor:
      runner: condor
      # universe: "vanilla"
      # Additional/override query ClassAd params can be specified here"""

K8S_ENVIRONMENT_TEMPLATE = """
    k8s:
      runner: k8s"""


COMMON_ENVIRONMENT_TEMPLATE = """
{%- if docker_config.enabled %}
docker_enabled: true
{%- if docker_config.sudo %}
docker_sudo: {{ docker_config.sudo }}
docker_sudo_cmd: {{ docker_config.sudo_cmd }}
{%- endif %}
docker_cmd: {{ docker_config.docker_cmd }}
{%- if docker_config.host %}
docker_host: {{ docker_config.host }}
{%- endif %}
docker_volumes: {{ docker_config.volumes }}
{%- if docker_config.run_extra_arguments %}
docker_run_extra_arguments: {{ docker_config.run_extra_arguments }}
{%- endif %}
{%- endif -%}
{%- if singularity_config.enabled %}
singularity_enabled: true
{%- if singularity_config.sudo %}
singularity_sudo: {{ singularity_config.sudo }}
singularity_sudo_cmd: {{ singularity_config.sudo_cmd }}
{%- endif %}
singularity_cmd: {{ singularity_config.singularity_cmd }}
singularity_volumes: {{ singularity_config.volumes }}
## May need to setup addition environment variables to get singularity working based on examples @
## https://training.galaxyproject.org/training-material/topics/admin/tutorials/connect-to-compute-cluster/tutorial.html
# env:
# - name: LC_ALL
#   value: C
# - name: APPTAINER_CACHEDIR
#   value: /tmp/singularity
# - name: APPTAINER_TMPDIR
#   value: /tmp
{%- endif -%}"""


TPV_ENVIRONMENT_24_2_TEMPLATE = """
    # Information on configuring TPV and leveraging the shared TPV Galaxy database for tools can be found at @
    # https://training.galaxyproject.org/training-material/topics/admin/tutorials/job-destinations/tutorial.html
    tpv:
      runner: dynamic
      type: python
      function: map_tool_to_destination
      rules_module: tpv.rules
      tpv_config_files:
      - https://gxy.io/tpv/db.yml
      - {{ cwd }}/tpv.yml  # TODO: create this file and setup a TPV destination
##  tpv.yml should contain something like:
# global:
#   default_inherits: default
# destinations:
"""

TPV_ENVIRONMENT_25_0_TEMPLATE = """
    # Information on configuring TPV and leveraging the shared TPV Galaxy database for tools can be found at @
    # https://training.galaxyproject.org/training-material/topics/admin/tutorials/job-destinations/tutorial.html
    tpv:
      runner: dynamic_tpv
      tpv_configs:
      - https://gxy.io/tpv/db.yml
      - destinations:"""

TPV_DESTINATION_SLURM = """
tpvdb_slurm:"""

TPV_DESTINATION_LOCAL = """
tpvdb_local:"""

TPV_DESTINATION_K8S = """
tpvdb_k8s:
  runner: k8s"""

TPV_DESTINATION_DRMAA = """
tpvdb_drmaa:
  runner: drmaa
  params:
    # adapt {cores} and {mem} to your DRM here - likely using native_specification
    native_specification: ""
"""

TPV_DESTINATION_CONDOR = """
tpvdb_condor:
  runner: condor
  params:
    request_cpus: "{cores}"
    # universe: "vanilla"
    # Additional/override query ClassAd params can be specified here
"""


# class that lets Planemo computed stuff be taken into account when deciding how containers
# are mounted (ensuring test data and tools are in the final containers tools run in).
@dataclass
class DevelopmentContext:
    test_data_dir: Optional[str]
    all_tool_paths: List[str]


@dataclass
class DockerConfig:
    enabled: bool
    host: Optional[str]
    volumes: str
    sudo: bool
    sudo_cmd: str
    docker_cmd: str
    run_extra_arguments: str


@dataclass
class SingularityConfig:
    enabled: bool
    volumes: str
    sudo: bool
    sudo_cmd: str
    singularity_cmd: str


def to_docker_config(dev_context: DevelopmentContext, config: ConfigArgs) -> DockerConfig:
    enabled = bool(config.docker)
    host = config.docker_host
    sudo = config.docker_sudo or False
    sudo_cmd = str(config.docker_sudo_cmd or "sudo")
    docker_cmd = str(config.docker_cmd or "docker")
    run_extra_arguments = str(config.docker_run_extra_arguments or "")

    volumes = list(config.docker_extra_volume or [])
    if dev_context.test_data_dir:
        volumes.append(f"{dev_context.test_data_dir}:ro")

    docker_volumes_str = "$defaults"
    if volumes:
        # exclude tool directories, these are mounted :ro by $defaults
        all_tool_dirs = {os.path.dirname(tool_path) for tool_path in dev_context.all_tool_paths}
        extra_volumes_str = ",".join(str(v) for v in create_docker_volumes(volumes) if v.path not in all_tool_dirs)
        docker_volumes_str = f"{docker_volumes_str},{extra_volumes_str}"

    return DockerConfig(
        enabled=enabled,
        host=host,
        volumes=docker_volumes_str,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
        docker_cmd=docker_cmd,
        run_extra_arguments=run_extra_arguments,
    )


def to_singularity_config(dev_context: DevelopmentContext, config: ConfigArgs) -> SingularityConfig:
    enabled = bool(config.singularity)
    sudo = config.singularity_sudo or False
    sudo_cmd = str(config.singularity_sudo_cmd or "sudo")
    singularity_cmd = str(config.singularity_cmd or "singularity")

    volumes = list(config.singularity_extra_volume or [])
    if dev_context.test_data_dir:
        volumes.append(f"{dev_context.test_data_dir}:ro")

    singularity_volumes_str = "$defaults"
    if volumes:
        # exclude tool directories, these are mounted :ro by $defaults
        all_tool_dirs = {os.path.dirname(tool_path) for tool_path in dev_context.all_tool_paths}
        extra_volumes_str = ",".join(str(v) for v in create_docker_volumes(volumes) if v.path not in all_tool_dirs)
        singularity_volumes_str = f"{singularity_volumes_str},{extra_volumes_str}"

    return SingularityConfig(
        enabled=enabled,
        sudo=sudo,
        sudo_cmd=sudo_cmd,
        volumes=singularity_volumes_str,
        singularity_cmd=singularity_cmd,
    )


def build_job_config(
    config: ConfigArgs,
    dev_context: Optional[DevelopmentContext] = None,
) -> str:
    dev_context = dev_context or DevelopmentContext(None, [])
    runner = config.runner
    tpv = config.tpv
    galaxy_version = config.galaxy_version or "25.0"
    docker_config = to_docker_config(dev_context, config)
    singularity_config = to_singularity_config(dev_context, config)
    environment_docker_stuff = render(
        COMMON_ENVIRONMENT_TEMPLATE,
        docker_config=docker_config,
        singularity_config=singularity_config,
    )
    additional_runners = ""
    additional_environments = ""
    default_environment = "local"
    local_environment = f"""
    local:
      runner: local{ indent(environment_docker_stuff, " " * 6) }
"""
    tpv_runner_destination_template = TPV_DESTINATION_LOCAL
    if runner == Runner.SLURM:
        additional_runners += SLURM_RUNNER_TEMPLATE
        default_environment = "slurm"
        additional_environments += SLURM_ENVIRONMENT_TEMPLATE + indent(environment_docker_stuff, " " * 6)
        tpv_runner_destination_template = TPV_DESTINATION_SLURM
    elif runner == Runner.K8S:
        additional_runners += K8S_RUNNER_TEMPLATE
        additional_environments += K8S_ENVIRONMENT_TEMPLATE + indent(environment_docker_stuff, " " * 6)
        default_environment = "k8s"
        tpv_runner_destination_template = TPV_DESTINATION_K8S
    elif runner == Runner.DRMAA:
        additional_runners += DRMAA_RUNNER_TEMPLATE
        additional_environments += DRMAA_ENVIRONMENT_TEMPLATE + indent(environment_docker_stuff, " " * 6)
        default_environment = "drmaa"
        tpv_runner_destination_template = TPV_DESTINATION_DRMAA
    elif runner == Runner.CONDOR:
        additional_runners += CONDOR_RUNNER_TEMPLATE
        additional_environments += CONDOR_ENVIRONMENT_TEMPLATE + indent(environment_docker_stuff, " " * 6)
        default_environment = "condor"
        tpv_runner_destination_template = TPV_DESTINATION_CONDOR

    if config.tpv:
        if galaxy_version < "25.0":
            tpv_environment = render(TPV_ENVIRONMENT_24_2_TEMPLATE, cwd=os.getcwd())
            if not environment_docker_stuff and tpv_runner_destination_template.endswith(":"):
                environment_extras = " {}"
            else:
                environment_extras = indent(environment_docker_stuff, "#     ")

            tpv_environment += indent(tpv_runner_destination_template, "#   ") + environment_extras
        else:
            if not environment_docker_stuff and tpv_runner_destination_template.endswith(":"):
                environment_extras = " {}"
            else:
                environment_extras = indent(environment_docker_stuff, " " * 12)
            tpv_environment = (
                TPV_ENVIRONMENT_25_0_TEMPLATE + indent(tpv_runner_destination_template, " " * 10) + environment_extras
            )
        if additional_environments:
            additional_environments += "\n"
        additional_environments += tpv_environment

    if tpv:
        default_environment = "tpv"

    config_str = render(
        TEMPLATE,
        additional_runners=additional_runners,
        additional_environments=additional_environments,
        local_environment=local_environment,
        default_environment=default_environment,
    )
    yaml.safe_load(config_str)  # try loading it just to assure we're building valid YAML
    return config_str


def create_docker_volumes(paths: Iterable[str]) -> Iterable[DockerVolume]:
    """
    Creates string of the format "host_path:target_path:mode" and deduplicates overlapping mounts.
    """
    docker_volumes: Dict[str, DockerVolume] = {}
    for path in paths:
        docker_volume = DockerVolume.from_str(path)
        if docker_volume.path in docker_volumes:
            # volume has been specified already, make sure we use "rw" if any of the modes are "rw"
            if docker_volume.mode == "rw" or docker_volumes[docker_volume.path].mode == "rw":
                docker_volumes[docker_volume.path].mode = "rw"
        else:
            docker_volumes[docker_volume.path] = docker_volume
    return docker_volumes.values()


def summarize(cli: str):
    planemo_cli = cli.replace("--", "DOUBLE_DASH").replace("-", "_").replace("DOUBLE_DASH", "--")
    as_argv = [x for x in cli.split() if x]
    config = config_args(as_argv)
    return f"""

```
galaxy-job-config-init {cli}
```

-or-

```
planemo job_config_init {planemo_cli}
```

generate the follow job configuration YAML file:

```yaml{ build_job_config(config) }
```
"""


def summary_markdown():
    extra = ""
    markdown = f"""# Job Configuration Examples

This page provides examples of Galaxy job configuration files generated by the `galaxy-job-config-init` command.

## Without Shared TPV Database ()

### Local Runner and No Containers

{ summarize(f" {extra}") }

### Local Runner and Docker

{ summarize(f"--docker {extra}") }

### Local Runner and Singularity

{ summarize(f"--singularity {extra}") }

### SLURM Runner and No Containers

{ summarize(f"--runner slurm {extra}") }

### DRMAA Runner and No Containers

{ summarize(f"--runner drmaa {extra}") }

### Condor Runner and No Containers

{ summarize(f"--runner condor {extra}") }

### K8S Runner and Docker

{ summarize(f"--runner k8s --docker {extra}") }

### SLURM Runner and Singularity

{ summarize(f"--runner slurm {extra} --singularity") }

## With TPV in 25.0+

### Local Runner and No Containers

{ summarize(f"--tpv {extra}") }

### Local Runner and Docker

{ summarize(f"--docker --tpv {extra}") }

### Local Runner and Singularity

{ summarize(f"--singularity --tpv {extra}") }

### SLURM Runner and No Containers

{ summarize(f"--runner slurm --tpv {extra}") }

### DRMAA Runner and No Containers

{ summarize(f"--runner drmaa --tpv {extra}") }

### Condor Runner and No Containers

{ summarize(f"--runner condor --tpv {extra}") }

### K8S Runner and Docker

{ summarize(f"--runner k8s --docker --tpv {extra}") }

## With Legacy TPV in 24.2

### Local Runner and No Containers

{ summarize(f"--tpv --galaxy-version 24.2 {extra}") }

### SLURM Runner and Singularity

{ summarize(f"--runner slurm --tpv --singularity  --galaxy-version 24.2 {extra}") }

"""
    return markdown
