import pytest

from galaxy.jobs.mapper import JobMappingException
from galaxy.jobs.platform_routing import platform_destination
from galaxy.tool_util.deps.requirements import (
    ToolRequirement,
    ToolRequirements,
)
from galaxy.util.bunch import Bunch


class MockDependencyManager:
    def __init__(self, platforms: list[str], configured: list[str] | None = None, auto_install: bool = False):
        self.platforms = platforms
        self.auto_install = auto_install
        self.configured = ["linux-64"] if configured is None else configured
        self.calls: list[ToolRequirements] = []

    def configured_conda_platforms(self):
        return self.configured

    def conda_auto_install_enabled(self):
        return self.auto_install

    def platforms_for_requirements(self, requirements):
        self.calls.append(requirements)
        return self.platforms


class MockJobConfig:
    def __init__(self, platforms: dict[str, str | None]):
        self.platforms = platforms

    def get_destination(self, destination_id):
        params = {}
        if self.platforms[destination_id]:
            params["platform"] = self.platforms[destination_id]
        return Bunch(id=destination_id, params=params)


def _app(
    available: list[str],
    destination_platforms: dict[str, str | None] | None = None,
    configured: list[str] | None = None,
    auto_install: bool = False,
):
    return Bunch(
        toolbox=Bunch(dependency_manager=MockDependencyManager(available, configured, auto_install)),
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


def test_listed_destination_without_platform_param_is_a_configuration_error():
    app = _app(["linux-64"], {"plain": None, "slurm_x86": "linux-64"})
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(), JOB, ["slurm_x86", "plain"])
    message = exc_info.value.failure_message
    assert "'plain'" in message
    assert "platform" in message
    assert app.toolbox.dependency_manager.calls == []


def test_mapping_entry_without_platform_is_a_configuration_error():
    app = _app(["linux-64"])
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(with_requirements=False), JOB, {"slurm_x86": "linux-64", "plain": ""})
    assert "'plain'" in exc_info.value.failure_message


def test_no_configured_platforms_is_named_in_the_message():
    app = _app([], configured=[])
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(), JOB, MAPPING)
    message = exc_info.value.failure_message
    assert "conda_platforms" in message
    assert "no conda platforms are configured" in message
    assert "bwa_tool" in message


def test_default_is_used_even_without_configured_platforms():
    app = _app([], configured=[])
    assert platform_destination(app, _tool(), JOB, MAPPING, default="fallback") == "fallback"


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


def test_first_job_of_a_new_tool_goes_to_the_native_destination_with_auto_install():
    configured = ["linux-64", "linux-aarch64", "osx-arm64"]
    app = _app([], configured=configured, auto_install=True)
    assert platform_destination(app, _tool(), JOB, MAPPING) == "slurm_x86"
    # the first native destination in the given order
    mapping = {"slurm_arm": "linux-aarch64", "native_b": "linux-64", "native_a": "linux-64"}
    assert platform_destination(app, _tool(), JOB, mapping) == "native_b"
    # takes precedence over the default
    assert platform_destination(app, _tool(), JOB, MAPPING, default="fallback") == "slurm_x86"


def test_auto_install_does_not_apply_once_something_is_installed():
    app = _app(["linux-aarch64"], configured=["linux-64", "linux-aarch64"], auto_install=True)
    assert platform_destination(app, _tool(), JOB, MAPPING) == "slurm_arm"
    app = _app(["win-64"], configured=["linux-64", "linux-aarch64"], auto_install=True)
    with pytest.raises(JobMappingException):
        platform_destination(app, _tool(), JOB, MAPPING)


def test_auto_install_without_native_destination_falls_through():
    app = _app([], configured=["linux-64", "linux-aarch64"], auto_install=True)
    with pytest.raises(JobMappingException):
        platform_destination(app, _tool(), JOB, {"slurm_arm": "linux-aarch64"})
    assert platform_destination(app, _tool(), JOB, {"slurm_arm": "linux-aarch64"}, default="fb") == "fb"


def test_without_auto_install_nothing_installed_raises_and_mentions_installing():
    app = _app([], configured=["linux-64", "linux-aarch64"], auto_install=False)
    with pytest.raises(JobMappingException) as exc_info:
        platform_destination(app, _tool(), JOB, MAPPING)
    message = exc_info.value.failure_message
    assert "none" in message
    assert "installed first" in message
    assert "admin dependency API or UI" in message
