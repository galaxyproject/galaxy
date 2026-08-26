"""Validate executable examples in the user-defined tool authoring help."""

import json
import re
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from cwl_utils.types import CWLObjectType

from galaxy.tool_util.lint import lint_user_tool_source
from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.dynamic_tool_models import (
    DynamicUnprivilegedToolCreatePayload,
)
from galaxy.tool_util_models.tool_source import JavascriptRequirement
from galaxy.tools.expressions import do_eval

PROJECT_ROOT = Path(__file__).parents[3]
HELP_PATH = PROJECT_ROOT / "client" / "src" / "components" / "Tool" / "authoringHelp.yml"
HELP_GENERATOR_PATH = PROJECT_ROOT / "doc" / "gen_authoring_doc.py"
FENCED_BLOCK = re.compile(r"```(?P<language>\w+)\n(?P<source>.*?)\n```", re.DOTALL)
INPUT_REFERENCE = re.compile(r"inputs\.([A-Za-z_][A-Za-z0-9_]*)(\.path)?")
KNOWN_FENCE_LANGUAGES = {"console", "json", "yaml"}
BASE_TOOL: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "documentation-example",
    "name": "Documentation Example",
    "version": "0.1.0",
    "container": "quay.io/biocontainers/python:3.13",
    "shell_command": "true",
    "inputs": [],
    "outputs": [],
}
PARAMETER_RUNTIME_INPUTS: dict[str, Any] = {
    "include_header": True,
    "plot_color": "#ff0000",
    "search_options": {"mode": "sensitive", "iterations": 3},
    "input_file": {"path": "/tmp/input.txt"},
    "reads": {
        "elements": {
            "forward": {"path": "/tmp/forward.fastq"},
            "reverse": {"path": "/tmp/reverse.fastq"},
        }
    },
    "threshold": 0.05,
    "num_lines": 10,
    "extra_files": [
        {"input_file": {"path": "/tmp/first.txt"}},
        {"input_file": {"path": "/tmp/second.txt"}},
    ],
    "advanced": {"threshold": 0.1},
    "mode": "fast",
    "motif": "ACGT",
}


def _help_data() -> dict[str, Any]:
    help_data = yaml.safe_load(HELP_PATH.read_text())
    quick_start = yaml.safe_dump(UserToolSource.model_json_schema()["examples"][0], sort_keys=False).rstrip()
    for section in help_data["sections"]:
        section["body"] = section["body"].replace("{{quick_start_example}}", quick_start)
    return help_data


def _blocks(language: str) -> list[tuple[str, str]]:
    return [
        (section["id"], match.group("source"))
        for section in _help_data()["sections"]
        for match in FENCED_BLOCK.finditer(section["body"])
        if match.group("language") == language
    ]


YAML_BLOCKS = _blocks("yaml")
JSON_BLOCKS = _blocks("json")
CONSOLE_BLOCKS = _blocks("console")


def _add_input(tool_dict: dict[str, Any], name: str, parameter_type: str) -> None:
    inputs = tool_dict.setdefault("inputs", [])
    if not any(parameter["name"] == name for parameter in inputs):
        inputs.append({"name": name, "type": parameter_type})


def _supply_fragment_context(tool_dict: dict[str, Any]) -> None:
    templated_text = [tool_dict.get("shell_command", "")]
    templated_text.extend(configfile.get("content", "") for configfile in tool_dict.get("configfiles") or [])
    for text in templated_text:
        for name, path_suffix in INPUT_REFERENCE.findall(text):
            _add_input(tool_dict, name, "data" if path_suffix else "text")

    for test in tool_dict.get("tests") or []:
        for name, value in (test.get("inputs") or {}).items():
            parameter_type = "data" if isinstance(value, dict) and value.get("class") == "File" else "text"
            _add_input(tool_dict, name, parameter_type)
        declared_outputs = {output.get("name") for output in tool_dict.get("outputs") or []}
        for name in test.get("outputs") or {}:
            if name not in declared_outputs:
                tool_dict.setdefault("outputs", []).append(
                    {"name": name, "type": "data", "from_work_dir": f"{name}.txt"}
                )


def _tool_from_fragment(section_id: str, source: str) -> UserToolSource:
    fragment = yaml.safe_load(source)
    tool_dict = fragment if section_id in {"quick-start", "tool-format"} else {**deepcopy(BASE_TOOL), **fragment}
    _supply_fragment_context(tool_dict)
    return UserToolSource.model_validate(tool_dict)


def _runtime_inputs(tool: UserToolSource) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for parameter_wrapper in tool.inputs:
        parameter = parameter_wrapper.root
        if parameter.type == "data":
            values[parameter.name] = {"path": f"/tmp/{parameter.name}.txt"}
        elif parameter.type == "integer":
            values[parameter.name] = parameter.value if parameter.value is not None else 10
        elif parameter.type == "float":
            values[parameter.name] = parameter.value if parameter.value is not None else 0.5
        elif parameter.type == "boolean":
            values[parameter.name] = parameter.value
        else:
            values[parameter.name] = getattr(parameter, "value", None) or "example"
    return values


def _javascript_requirements(tool: UserToolSource) -> list[JavascriptRequirement]:
    return [requirement for requirement in tool.requirements or [] if isinstance(requirement, JavascriptRequirement)]


def _assert_shell_syntax(source: str) -> None:
    result = subprocess.run(["sh", "-n"], input=source, text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr


def test_all_documentation_fences_are_recognized_and_closed() -> None:
    for section in _help_data()["sections"]:
        matches = list(FENCED_BLOCK.finditer(section["body"]))
        assert section["body"].count("```") == len(matches) * 2, f"unclosed code fence in {section['id']}"
        assert {match.group("language") for match in matches} <= KNOWN_FENCE_LANGUAGES


def test_generated_documentation_resolves_schema_sections() -> None:
    result = subprocess.run(
        [sys.executable, str(HELP_GENERATOR_PATH), str(HELP_PATH)],
        text=True,
        capture_output=True,
        check=True,
    )

    assert "{{" not in result.stdout
    assert "## Getting Started" in result.stdout
    assert "## Detailed reference" in result.stdout
    assert "(quick-start)=" in result.stdout
    assert "(discover-datasets)=" in result.stdout
    assert "(validator-regex)=" in result.stdout
    assert "### Quick start" in result.stdout
    assert "#### Validators" in result.stdout
    assert "#### regex validator" in result.stdout
    assert "[`regex` #](#validator-regex)" in result.stdout
    assert "[`shell_command` #](#expressions)" in result.stdout
    assert "[`discover_datasets` #](#discover-datasets)" in result.stdout
    assert "(output-data-format-source)=" in result.stdout
    assert "(output-data-metadata-source)=" in result.stdout
    assert "##### format_source" in result.stdout
    assert "##### metadata_source" in result.stdout
    assert "`format_source` can be used to assign" in result.stdout
    assert "`metadata_source` can be used to copy" in result.stdout
    assert "[`format_source` #](#output-data-format-source)" in result.stdout
    assert "[`metadata_source` #](#output-data-metadata-source)" in result.stdout
    assert "format_source: reads" in result.stdout
    assert "metadata_source: intervals" in result.stdout
    assert "name: reads" in result.stdout
    assert "name: intervals" in result.stdout
    assert "User-defined tools discover them by matching filenames" in result.stdout
    assert "galaxy.json" not in result.stdout
    assert "**Datatypes page**" in result.stdout
    assert "](/datatypes)" not in result.stdout
    assert "shell_command: grep" in result.stdout


@pytest.mark.parametrize(
    ("section_id", "source"),
    YAML_BLOCKS,
    ids=[section_id for section_id, _ in YAML_BLOCKS],
)
def test_documented_yaml_fragments_validate_and_lint(section_id: str, source: str) -> None:
    tool = _tool_from_fragment(section_id, source)

    assert lint_user_tool_source(tool) == []


@pytest.mark.parametrize(
    ("section_id", "source"),
    JSON_BLOCKS,
    ids=[section_id for section_id, _ in JSON_BLOCKS],
)
def test_documented_json_payloads_validate_and_lint(section_id: str, source: str) -> None:
    payload = DynamicUnprivilegedToolCreatePayload.model_validate(json.loads(source))
    tool = payload.representation

    assert lint_user_tool_source(tool) == [], section_id
    evaluated_command = do_eval(tool.shell_command, _runtime_inputs(tool), _javascript_requirements(tool))
    _assert_shell_syntax(evaluated_command)


@pytest.mark.parametrize(
    ("section_id", "source"),
    CONSOLE_BLOCKS,
    ids=[section_id for section_id, _ in CONSOLE_BLOCKS],
)
def test_documented_console_snippets_have_valid_shell_syntax(section_id: str, source: str) -> None:
    shell_source = "\n".join(line.removeprefix("$ ") for line in source.splitlines())

    _assert_shell_syntax(shell_source)


@pytest.mark.parametrize(
    ("section_id", "source"),
    YAML_BLOCKS,
    ids=[section_id for section_id, _ in YAML_BLOCKS],
)
def test_documented_commands_and_configfiles_evaluate(section_id: str, source: str) -> None:
    tool = _tool_from_fragment(section_id, source)
    runtime_inputs = _runtime_inputs(tool)
    javascript_requirements = _javascript_requirements(tool)

    evaluated_command = do_eval(tool.shell_command, runtime_inputs, javascript_requirements)
    _assert_shell_syntax(evaluated_command)
    for configfile in tool.configfiles or []:
        evaluated_content = do_eval(configfile.content, runtime_inputs, javascript_requirements)
        if configfile.filename and configfile.filename.endswith(".sh"):
            _assert_shell_syntax(evaluated_content)
    for requirement in javascript_requirements:
        assert do_eval("$(1)", {}, [requirement]) == 1


def test_documented_expression_forms_evaluate() -> None:
    runtime_inputs: CWLObjectType = {"num_lines": 10, "query": {"path": "/tmp/query.txt"}}

    assert do_eval("$(inputs.num_lines)", runtime_inputs) == 10
    assert do_eval("$(inputs.query.path)", runtime_inputs) == "/tmp/query.txt"
    assert do_eval("${ return inputs.num_lines * 2 }", runtime_inputs) == 20


def test_parameter_shell_command_examples_evaluate_and_have_valid_shell_syntax() -> None:
    definitions = UserToolSource.model_json_schema()["$defs"]
    mapping = definitions["YamlGalaxyToolParameter"]["discriminator"]["mapping"]

    for parameter_type, reference in mapping.items():
        definition = definitions[reference.rsplit("/", 1)[-1]]
        evaluated = do_eval(definition["x-shell-command"], PARAMETER_RUNTIME_INPUTS)
        _assert_shell_syntax(evaluated)
        assert "$(inputs." not in evaluated, parameter_type
