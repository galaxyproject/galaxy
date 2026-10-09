from typing import Optional

import pytest

from galaxy.jobs.mapper import JobMappingException
from galaxy.jobs.platform_routing import platform_destination
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.util.bunch import Bunch


class MockDependencyManager:
    def __init__(self, platforms: list[str]):
        self.platforms = platforms
        self.calls: list[ToolRequirements] = []

    def platforms_for_requirements(self, requirements):
        self.calls.append(requirements)
        return self.platforms


class MockJobConfig:
    def __init__(self, platforms: dict[str, Optional[str]]):
        self.platforms = platforms

    def get_destination(self, destination_id):
        params = {}
        if self.platforms[destination_id]:
            params["platform"] = self.platforms[destination_id]
        return Bunch(id=destination_id, params=params)


def _app(available: list[str], destination_platforms: Optional[dict[str, Optional[str]]] = None):
    return Bunch(
        toolbox=Bunch(dependency_manager=MockDependencyManager(available)),
        job_config=MockJobConfig(destination_platforms or {}),
    )


def _tool(with_requirements: bool = True):
    requirements = ToolRequirements([ToolRequirement(name="bwa", version="0.7.17", type="package")])
    return Bunch(id="bwa_tool", requirements=requirements if with_requirements else ToolRequirements([]))


JOB = Bunch(id=7)
MAPPING = {"slurm_x86": "linux-64", "slurm_arm": "linux-aarch64", "pulsar_mac": "osx-arm64"}


def test_first_matching_destination_in_given_order():
    app = _app(["linux-64", "linux-aarch64"])
    assert platform_destination(app, _tool(), JOB, MAPPING) == "slurm_x86"
    reordered = {"slurm_arm": "linux-aarch64", "slurm_x86": "linux-64"}
    assert platform_destination(app, _tool(), JOB, reordered) == "slurm_arm"


def test_skips_destinations_without_environments():
    app = _app(["linux-aarch64", "osx-arm64"])
    assert platform_destination(app, _tool(), JOB, MAPPING) == "slurm_arm"
    app = _app(["osx-arm64"])
    assert platform_destination(app, _tool(), JOB, MAPPING) == "pulsar_mac"


def test_requirements_are_passed_to_the_dependency_manager():
    app = _app(["linux-64"])
    tool = _tool()
    platform_destination(app, tool, JOB, MAPPING)
    (requirements,) = app.toolbox.dependency_manager.calls
    assert [r.name for r in requirements] == ["bwa"]


def test_list_of_destinations_reads_platform_from_job_config():
    app = _app(["osx-arm64"], {"slurm_x86": "linux-64", "slurm_arm": "linux-aarch64", "pulsar_mac": "osx-arm64"})
    assert platform_destination(app, _tool(), JOB, ["slurm_x86", "slurm_arm", "pulsar_mac"]) == "pulsar_mac"


def test_list_ignores_destinations_without_platform_param():
    app = _app(["linux-64"], {"plain": None, "slurm_x86": "linux-64"})
    assert platform_destination(app, _tool(), JOB, ["plain", "slurm_x86"]) == "slurm_x86"


def test_tool_without_requirements_gets_first_destination():
    app = _app([])
    assert platform_destination(app, _tool(with_requirements=False), JOB, MAPPING) == "slurm_x86"
    assert app.toolbox.dependency_manager.calls == []


def test_default_when_nothing_matches():
    app = _app(["win-64"])
    assert platform_destination(app, _tool(), JOB, MAPPING, default="fallback") == "fallback"


def test_raises_when_nothing_matches_and_no_default():
    app = _app(["win-64"])
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(), JOB, MAPPING)
    message = exc_info.value.failure_message
    assert "bwa_tool" in message
    assert "win-64" in message
    assert "linux-aarch64" in message


def test_raises_without_installed_platforms():
    app = _app([])
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(), JOB, MAPPING)
    assert "none" in exc_info.value.failure_message


def test_empty_destinations_raise():
    with pytest.raises(JobMappingException):
        platform_destination(_app([]), _tool(), JOB, [])
