import json
import shlex
import subprocess
import sys

import pytest
from pydantic import ValidationError

from galaxy.tool_util.deps.container_classes import (
    DockerContainer,
    SingularityContainer,
)
from galaxy.tool_util.deps.dependencies import (
    AppInfo,
    JobInfo,
    ToolInfo,
)
from galaxy.tool_util.output_checker import (
    merge_runtime_environment_warnings,
    runtime_environment_job_messages,
)
from galaxy.tool_util.parser.stdio import StdioErrorLevel
from galaxy.tool_util.parser.xml import XmlToolSource
from galaxy.tool_util.runtime_environment import required_environment_checks
from galaxy.tool_util_models import (
    UserToolSource,
    YamlToolSource,
)
from galaxy.tool_util_models.runtime_environment import RuntimeEnvironmentVariable
from galaxy.util import parse_xml_string_to_etree


@pytest.mark.parametrize(
    "name", ["PATH", "LD_PRELOAD", "GALAXY_SLOTS", "_GALAXY_X", "SINGULARITYENV_X", "APPTAINER_X", "bad-name", "1VAR"]
)
def test_invalid_names(name):
    with pytest.raises(ValidationError):
        RuntimeEnvironmentVariable(name=name)


def test_required_check_preserves_empty_and_reports_names_only(tmp_path):
    variables = [
        RuntimeEnvironmentVariable(name="MISSING", required=True),
        RuntimeEnvironmentVariable(name="EMPTY", required=True),
        RuntimeEnvironmentVariable(name="OPTIONAL"),
    ]
    warning_file = tmp_path / "outputs" / "runtime_environment_warnings"
    warning_file.parent.mkdir()
    subprocess.run(
        ["sh", "-c", required_environment_checks(variables, str(warning_file))], env={"EMPTY": ""}, check=True
    )
    assert warning_file.read_text() == "MISSING\n"
    messages = runtime_environment_job_messages(str(tmp_path))
    assert messages[0]["type"] == "runtime_environment_warning"
    assert messages[0]["variable_names"] == ["MISSING"]
    assert messages[0]["error_level"] == StdioErrorLevel.WARNING


def test_xml_runtime_environment():
    source = XmlToolSource(
        parse_xml_string_to_etree(
            '<tool><requirements><runtime_environment_variable name="_JAVA_OPTIONS" description="JVM options"/><runtime_environment_variable name="LICENSE_SERVER" required="true"/></requirements></tool>'
        )
    )
    variables = source.parse_runtime_environment_variables()
    assert variables[0].description == "JVM options"
    assert variables[0].required is False
    assert variables[1].required is True


def test_yaml_installed_and_user_tools():
    VALID_TOOL = {
        "class": "GalaxyUserTool",
        "id": "test",
        "name": "Test Tool",
        "version": "1",
        "container": "busybox:1",
        "shell_command": "echo test > out.txt",
        "inputs": [],
        "outputs": [{"type": "data", "name": "out", "from_work_dir": "out.txt"}],
    }

    tool = {**VALID_TOOL, "runtime_environment_variables": [{"name": "_JAVA_OPTIONS"}]}
    with pytest.raises(ValidationError, match="extra_forbidden"):
        UserToolSource.model_validate(tool)
    tool["class"] = "GalaxyTool"
    assert YamlToolSource.model_validate(tool).runtime_environment_variables[0].name == "_JAVA_OPTIONS"


# Fake runtimes print, as JSON, the environment the container would get and the
# names in their own (client) environment, so no daemon or image is needed.
FAKE_DOCKER = """
import json, os, sys
if sys.argv[1] != 'run':
    sys.exit(0)
container = {}
args = iter(sys.argv[2:])
for arg in args:
    if arg == '-e':
        name, sep, value = next(args).partition('=')
        if sep:
            container[name] = value
        elif name in os.environ:
            container[name] = os.environ[name]
print(json.dumps({'container': container, 'client': sorted(os.environ)}))
"""

FAKE_SINGULARITY = """
import json, os
prefix = 'SINGULARITYENV_'
container = {k[len(prefix):]: v for k, v in os.environ.items() if k.startswith(prefix)}
print(json.dumps({'container': container, 'client': sorted(os.environ)}))
"""

# Like a sudoers rule without SETENV: options that preserve the caller's environment are refused.
STRICT_SUDO = """
import os, sys
args = sys.argv[1:]
while args and args[0].startswith('--'):
    option = args.pop(0)
    if option != '--non-interactive':
        raise RuntimeError('Unexpected sudo option: ' + option)
os.execve(args[0], args, {})
"""

TRICKY_VALUE = 'spaces "quotes" $dollars `backticks`\nnewlines'
FORWARDED_NAMES = ["DECLARED", "EMPTY", "UNSET", "OVERRIDE", "SOURCED"]
HOST_ENVIRONMENT = {"DECLARED": TRICKY_VALUE, "EMPTY": "", "OVERRIDE": "forwarded", "UNRELATED_SECRET": "host-only"}
# Set by the job script itself, as a sourced file or executed setup command would.
JOB_SCRIPT_SETUP = 'SOURCED="from a sourced file";\n'

RUNTIMES = pytest.mark.parametrize(
    "runtime,sudo",
    [("docker", False), ("singularity", False), ("docker", True)],
    ids=["docker", "singularity", "docker_sudo"],
)


def _write_python_script(path, body):
    # A shebang can't hold an interpreter path containing spaces, as CI's does.
    source = path.with_suffix(".py")
    source.write_text(body)
    path.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(source))} "$@"\n')
    path.chmod(0o755)


def _containerize(tmp_path, runtime: str, sudo: bool) -> str:
    """Containerize a no-op command, with OVERRIDE also set through the legacy runtime-specific param."""
    runtime_script = tmp_path / runtime
    _write_python_script(runtime_script, FAKE_DOCKER if runtime == "docker" else FAKE_SINGULARITY)
    sudo_script = tmp_path / "sudo"
    _write_python_script(sudo_script, STRICT_SUDO)
    container_class = DockerContainer if runtime == "docker" else SingularityContainer
    container = container_class(
        container_id="image",
        app_info=AppInfo(container_image_cache_path=str(tmp_path)),
        tool_info=ToolInfo(env_pass_through=FORWARDED_NAMES),
        destination_info={
            f"{runtime}_cmd": str(runtime_script),
            f"{runtime}_env_OVERRIDE": "legacy",
            f"{runtime}_volumes": "",
            f"{runtime}_sudo": sudo,
            f"{runtime}_sudo_cmd": f"{sudo_script} --non-interactive",
        },
        job_info=JobInfo(str(tmp_path), None, str(tmp_path), None, None, "galaxy", set()),
        container_description=None,
    )
    return JOB_SCRIPT_SETUP + container.containerize_command("true")


def _run(command: str) -> dict:
    result = subprocess.run(["bash", "-c", command], env=HOST_ENVIRONMENT, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


@RUNTIMES
def test_forwarded_values_reach_container_intact(tmp_path, runtime, sudo):
    container_environment = _run(_containerize(tmp_path, runtime, sudo))["container"]
    assert container_environment["DECLARED"] == TRICKY_VALUE
    assert container_environment["SOURCED"] == "from a sourced file"


@RUNTIMES
def test_empty_stays_empty_and_unset_stays_unset(tmp_path, runtime, sudo):
    container_environment = _run(_containerize(tmp_path, runtime, sudo))["container"]
    assert container_environment["EMPTY"] == ""
    assert "UNSET" not in container_environment


@RUNTIMES
def test_runtime_specific_params_override_forwarded_values(tmp_path, runtime, sudo):
    assert _run(_containerize(tmp_path, runtime, sudo))["container"]["OVERRIDE"] == "legacy"


@RUNTIMES
def test_only_forwarded_names_reach_container(tmp_path, runtime, sudo):
    assert set(_run(_containerize(tmp_path, runtime, sudo))["container"]) == {
        "DECLARED",
        "EMPTY",
        "OVERRIDE",
        "SOURCED",
    }


@RUNTIMES
def test_values_stay_out_of_container_command(tmp_path, runtime, sudo):
    assert TRICKY_VALUE not in _containerize(tmp_path, runtime, sudo)


def test_docker_sudo_needs_no_environment_preservation(tmp_path):
    # STRICT_SUDO refuses --preserve-env and hands docker an empty environment.
    outcome = _run(_containerize(tmp_path, "docker", sudo=True))
    assert "UNRELATED_SECRET" not in outcome["client"]
    assert outcome["container"]["DECLARED"] == TRICKY_VALUE


def test_merge_task_runtime_warnings(tmp_path):
    task_dirs = [tmp_path / "task_0", tmp_path / "task_1"]
    for task, directory, names in [
        (task_dirs[0], "outputs", "FIRST\nSHARED\n"),
        (task_dirs[1], "metadata", "SHARED\nSECOND\ninvalid-name\n"),
        (tmp_path / "task_unrelated", "outputs", "UNRELATED\n"),
    ]:
        path = task / directory / "runtime_environment_warnings"
        path.parent.mkdir(parents=True)
        path.write_text(names)
    merge_runtime_environment_warnings(str(tmp_path), [str(task) for task in task_dirs])
    messages = runtime_environment_job_messages(str(tmp_path))
    assert len(messages) == 1
    assert messages[0]["variable_names"] == ["FIRST", "SHARED", "SECOND"]
    assert messages[0]["error_level"] == StdioErrorLevel.WARNING

    # A retry with all requirements satisfied must clear stale warnings.
    for task in task_dirs:
        for warning_file in task.glob("*/runtime_environment_warnings"):
            warning_file.write_text("")
    merge_runtime_environment_warnings(str(tmp_path), [str(task) for task in task_dirs])
    assert runtime_environment_job_messages(str(tmp_path)) == []
