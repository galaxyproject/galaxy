import enum
from dataclasses import dataclass
from typing import (
    List,
    Optional,
)

from typing_extensions import (
    NotRequired,
    TypedDict,
    Unpack,
)


class Runner(enum.StrEnum):
    LOCAL = "local"
    SLURM = "slurm"
    DRMAA = "drmaa"
    K8S = "k8s"
    CONDOR = "condor"


class CliConfigArgs(TypedDict, total=False):
    galaxy_version: NotRequired[Optional[str]]
    runner: NotRequired[Optional[Runner]]
    tpv: NotRequired[bool]
    docker: NotRequired[Optional[bool]]
    docker_cmd: NotRequired[Optional[str]]
    docker_host: NotRequired[Optional[str]]
    docker_sudo: NotRequired[Optional[bool]]
    docker_sudo_cmd: NotRequired[Optional[str]]
    docker_run_extra_arguments: NotRequired[Optional[str]]
    docker_extra_volume: NotRequired[Optional[List[str]]]
    singularity: NotRequired[Optional[bool]]
    singularity_cmd: NotRequired[Optional[str]]
    singularity_sudo: NotRequired[Optional[bool]]
    singularity_sudo_cmd: NotRequired[Optional[str]]
    singularity_extra_volume: NotRequired[Optional[List[str]]]


@dataclass
class ConfigArgs:
    galaxy_version: Optional[str] = None
    runner: Optional[Runner] = None
    tpv: Optional[bool] = None
    docker: Optional[bool] = None
    docker_cmd: Optional[str] = None
    docker_host: Optional[str] = None
    docker_sudo: Optional[bool] = None
    docker_sudo_cmd: Optional[str] = None
    docker_run_extra_arguments: Optional[str] = None
    docker_extra_volume: Optional[List[str]] = None
    singularity: Optional[bool] = None
    singularity_cmd: Optional[str] = None
    singularity_sudo: Optional[bool] = None
    singularity_sudo_cmd: Optional[str] = None
    singularity_extra_volume: Optional[List[str]] = None

    @staticmethod
    def from_dict(**data: Unpack[CliConfigArgs]) -> "ConfigArgs":
        return ConfigArgs(
            runner=data.get("runner", Runner.LOCAL),
            tpv=data.get("tpv", None),
            galaxy_version=data.get("galaxy_version", None),
            docker=data.get("docker", None),
            docker_cmd=data.get("docker_cmd", None),
            docker_host=data.get("docker_host", None),
            docker_sudo=data.get("docker_sudo", None),
            docker_sudo_cmd=data.get("docker_sudo_cmd", None),
            docker_run_extra_arguments=data.get("docker_run_extra_arguments", None),
            docker_extra_volume=data.get("docker_extra_volume", None),
            singularity=data.get("singularity", None),
            singularity_cmd=data.get("singularity_cmd", None),
            singularity_sudo=data.get("singularity_sudo", None),
            singularity_sudo_cmd=data.get("singularity_sudo_cmd", None),
            singularity_extra_volume=data.get("singularity_extra_volume", []),
        )
