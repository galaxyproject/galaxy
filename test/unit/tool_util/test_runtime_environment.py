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
from galaxy.tool_util.lint import get_lint_context_for_tool_source
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


def test_runtime_environment_lint():
    source = XmlToolSource(
        parse_xml_string_to_etree(
            '<tool id="test" name="test" version="1"><requirements><runtime_environment_variable name="SERVICE_TOKEN" description="Service token"/><runtime_environment_variable name="PATH"/></requirements></tool>'
        )
    )
    ctx = get_lint_context_for_tool_source(source)
    assert any("Reserved runtime" in m.message for m in ctx.error_messages)
    source = XmlToolSource(
        parse_xml_string_to_etree(
            '<tool id="test" name="test" version="1"><requirements><runtime_environment_variable name="SERVICE_TOKEN" description="Service token"/></requirements></tool>'
        )
    )
    ctx = get_lint_context_for_tool_source(source)
    assert any("use <credentials>" in m.message for m in ctx.warn_messages)
    assert any("Service token" in m.message for m in ctx.info_messages)


def _write_python_script(path, body):
    # A shebang can't hold an interpreter path containing spaces, as CI's does.
    source = path.with_suffix(".py")
    source.write_text(body)
    path.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(source))} "$@"\n')
    path.chmod(0o755)


@pytest.mark.parametrize("runtime,sudo", [("docker", False), ("singularity", False), ("docker", True)])
def test_forwarding_preserves_unset_empty_and_legacy_overrides(tmp_path, runtime, sudo):
    # Simulate only runtime argument/environment handling, so this test needs no daemon or image.
    runtime_script = tmp_path / runtime
    if runtime == "docker":
        body = """
import json, os, sys
if sys.argv[1] != 'run':
    sys.exit(0)
result = {}
args = iter(sys.argv[2:])
for arg in args:
    if arg == '-e':
        directive = next(args)
        name, sep, value = directive.partition('=')
        if sep:
            result[name] = value
        elif name in os.environ:
            result[name] = os.environ[name]
print(json.dumps(result))
"""
    else:
        body = """
import json, os
print(json.dumps({k[len('SINGULARITYENV_'):]: v for k, v in os.environ.items() if k.startswith('SINGULARITYENV_')}))
"""
    sudo_script = tmp_path / "sudo"
    # Like a sudoers rule without SETENV: options that preserve the caller's environment are refused.
    sudo_body = """
import os, sys
args = sys.argv[1:]
while args and args[0].startswith('--'):
    option = args.pop(0)
    if option != '--non-interactive':
        raise RuntimeError('Unexpected sudo option: ' + option)
os.execve(args[0], args, {})
"""
    _write_python_script(sudo_script, sudo_body)
    if sudo:
        body += "\nassert 'UNRELATED_SECRET' not in os.environ\n"
    _write_python_script(runtime_script, body)
    container_class = DockerContainer if runtime == "docker" else SingularityContainer
    container = container_class(
        container_id="image",
        app_info=AppInfo(container_image_cache_path=str(tmp_path)),
        tool_info=ToolInfo(env_pass_through=["DECLARED", "EMPTY", "UNSET", "OVERRIDE", "SOURCED"]),
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
    command = 'SOURCED="from a sourced file";\n' + container.containerize_command("true")
    value = 'spaces "quotes" $dollars `backticks`\nnewlines'
    result = subprocess.run(
        ["bash", "-c", command],
        env={"DECLARED": value, "EMPTY": "", "OVERRIDE": "forwarded", "UNRELATED_SECRET": "host-only"},
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout) == {
        "DECLARED": value,
        "EMPTY": "",
        "OVERRIDE": "legacy",
        "SOURCED": "from a sourced file",
    }
    assert value not in command


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
