import argparse
from typing import List

from .types import (
    ConfigArgs,
    Runner,
)

DESCRIPTION = "Generate job configuration YAML."

HELP_GALAXY_VERSION = "Generate job config YAML for this version of Galaxy."
HELP_RUNNER = "Galaxy runner (e.g. DRM) to target (defaults to 'local' requiring no external resource manager)."
HELP_TPV = "Enable shared TPV database."
HELP_DOCKER = "Enable Docker."
HELP_DOCKER_CMD = "Command used to launch docker (defaults to 'docker')."
HELP_DOCKER_HOST = "Docker host."
HELP_DOCKER_SUDO = "Use sudo with Docker."
HELP_DOCKER_SUDO_CMD = "Docker sudo command."
HELP_DOCKER_RUN_EXTRA_ARGUMENTS = "Extra arguments for Docker run."
HELP_DOCKER_EXTRA_VOLUME = "Extra Docker volumes."
HELP_SINGULARITY = "Enable Singularity."
HELP_SINGULARITY_CMD = "Command used to execute singularity (defaults to 'singularity')."
HELP_SINGULARITY_SUDO = "Use sudo with Singularity."
HELP_SINGULARITY_SUDO_CMD = "Singularity sudo command."
HELP_SINGULARITY_EXTRA_VOLUME = "Extra Singularity volumes."


def config_args(argv: List[str]):
    parser = argparser()
    args = parser.parse_args(argv)
    config_args = ConfigArgs(
        galaxy_version=args.galaxy_version,
        runner=Runner(args.runner) if args.runner else None,
        tpv=args.tpv,
        docker=args.docker,
        docker_cmd=args.docker_cmd,
        docker_host=args.docker_host,
        docker_sudo=args.docker_sudo,
        docker_sudo_cmd=args.docker_sudo_cmd,
        docker_run_extra_arguments=args.docker_run_extra_arguments,
        docker_extra_volume=args.docker_extra_volume,
        singularity=args.singularity,
        singularity_cmd=args.singularity_cmd,
        singularity_sudo=args.singularity_sudo,
        singularity_sudo_cmd=args.singularity_sudo_cmd,
        singularity_extra_volume=args.singularity_extra_volume,
    )
    return config_args


def argparser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--galaxy-version", type=str, help=HELP_GALAXY_VERSION)
    parser.add_argument("--runner", type=str, choices=[e.value for e in Runner], help=HELP_RUNNER)
    parser.add_argument("--tpv", action="store_true", help=HELP_TPV)
    parser.add_argument("--docker", action="store_true", help=HELP_DOCKER)
    parser.add_argument("--docker-cmd", type=str, help=HELP_DOCKER_CMD)
    parser.add_argument("--docker-host", type=str, help=HELP_DOCKER_HOST)
    parser.add_argument("--docker-sudo", action="store_true", help=HELP_DOCKER_SUDO)
    parser.add_argument("--docker-sudo-cmd", type=str, help=HELP_DOCKER_SUDO_CMD)
    parser.add_argument("--docker-run-extra-arguments", type=str, help=HELP_DOCKER_RUN_EXTRA_ARGUMENTS)
    parser.add_argument("--docker-extra-volume", type=str, nargs="*", help=HELP_DOCKER_EXTRA_VOLUME)
    parser.add_argument("--singularity", action="store_true", help=HELP_SINGULARITY)
    parser.add_argument("--singularity-cmd", type=str, help=HELP_SINGULARITY_CMD)
    parser.add_argument("--singularity-sudo", action="store_true", help=HELP_SINGULARITY_SUDO)
    parser.add_argument("--singularity-sudo-cmd", type=str, help=HELP_SINGULARITY_SUDO_CMD)
    parser.add_argument("--singularity-extra-volume", type=str, nargs="*", help=HELP_SINGULARITY_EXTRA_VOLUME)
    return parser
