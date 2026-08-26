"""Tests for the ContainerImageShape linter and the lint_user_tool_source helper."""

from copy import deepcopy

import pytest
from pydantic import ValidationError

from galaxy.tool_util.lint import (
    get_lint_context_for_tool_source,
    lint_user_tool_source,
)
from galaxy.tool_util.linters.containers import ContainerImageShape
from galaxy.tool_util.parser.util import ParseException
from galaxy.tool_util.parser.yaml import YamlToolSource
from galaxy.tool_util_models import UserToolSource

VALID_TOOL = {
    "class": "GalaxyUserTool",
    "id": "my-cool-tool",
    "name": "My Cool Tool",
    "version": "0.1.0",
    "description": "A cool tool.",
    "container": "quay.io/biocontainers/python:3.13",
    "shell_command": "head -n '$(inputs.n_lines)' '$(inputs.data_input.path)' > out.txt",
    "inputs": [
        {"type": "integer", "name": "n_lines"},
        {"type": "data", "name": "data_input"},
    ],
    "outputs": [
        {"type": "data", "name": "out", "from_work_dir": "out.txt"},
    ],
    "citations": [
        {"type": "doi", "content": "10.1234/abc.def"},
    ],
}


def _doc(**overrides):
    base = deepcopy(VALID_TOOL)
    base.update(overrides)
    return base


@pytest.mark.parametrize(
    "container",
    [
        "quay.io/biocontainers/samtools:1.17",
        "docker://my-registry/image:tag",
        "oras://example.org/image",
        "busybox",
        "ubuntu:latest",
        "library/python:3.11-slim",
    ],
)
def test_valid_container_shapes_pass_lint(container):
    tool_source = YamlToolSource(_doc(container=container))
    ctx = get_lint_context_for_tool_source(tool_source)
    container_warns = [m for m in ctx.warn_messages if m.linter == ContainerImageShape.name()]
    assert container_warns == []


@pytest.mark.parametrize("bad_container", ["definitely not a container", "foo bar baz"])
def test_invalid_container_shapes_warn(bad_container):
    tool_source = YamlToolSource(_doc(container=bad_container))
    ctx = get_lint_context_for_tool_source(tool_source)
    container_warns = [m for m in ctx.warn_messages if m.linter == ContainerImageShape.name()]
    assert len(container_warns) == 1
    assert "does not match a recognized shape" in container_warns[0].message


def test_lint_user_tool_source_returns_empty_on_clean_tool():
    user_tool = UserToolSource.model_validate(VALID_TOOL)
    assert lint_user_tool_source(user_tool) == []


def test_lint_user_tool_source_surfaces_container_shape_failure():
    user_tool = UserToolSource.model_validate(_doc(container="totally bogus value"))
    bullets = lint_user_tool_source(user_tool)
    assert any("does not match a recognized shape" in b for b in bullets)
    assert any(b.startswith(f"{ContainerImageShape.name()}:") for b in bullets)


def test_user_tool_source_accepts_container_requirement():
    source = _doc(
        container=None,
        requirements=[
            {
                "type": "container",
                "container": {"type": "docker", "container_id": "busybox"},
            }
        ],
    )
    tool = UserToolSource.model_validate(source)
    assert tool.container is None


def test_user_tool_source_requires_a_container_form():
    source = _doc(container=None)
    with pytest.raises(ValidationError, match="set container or add a container requirement"):
        UserToolSource.model_validate(source)


def test_parser_reads_container_requirement():
    tool_source = YamlToolSource(
        _doc(
            container=None,
            requirements=[
                {
                    "type": "container",
                    "container": {
                        "type": "singularity",
                        "container_id": "oras://example.org/image:tag",
                    },
                }
            ],
        )
    )
    _, containers, _, _, _ = tool_source.parse_requirements()
    assert len(containers) == 1
    assert containers[0].type == "singularity"
    assert containers[0].identifier == "oras://example.org/image:tag"


MALFORMED_CONTAINER_REQUIREMENTS = [
    {"type": "container", "container_id": "busybox"},
    {"type": "container", "container": {"type": "docker"}},
    {"type": "container"},
]


@pytest.mark.parametrize("requirement", MALFORMED_CONTAINER_REQUIREMENTS)
def test_user_tool_rejects_malformed_container_requirement(requirement):
    tool_source = YamlToolSource(_doc(container=None, requirements=[requirement]))

    with pytest.raises(ParseException, match="must set container.container_id"):
        tool_source.parse_requirements()


@pytest.mark.parametrize("requirement", MALFORMED_CONTAINER_REQUIREMENTS)
def test_linting_reports_unparseable_user_tool_once(requirement):
    tool_source = YamlToolSource(_doc(container=None, requirements=[requirement]))

    ctx = get_lint_context_for_tool_source(tool_source)

    assert [m.linter for m in ctx.error_messages] == ["ToolParse"]
    assert "must set container.container_id" in ctx.error_messages[0].message


@pytest.mark.parametrize("requirement", MALFORMED_CONTAINER_REQUIREMENTS)
def test_non_user_tool_keeps_malformed_container_requirement(requirement):
    # Matches the XML parser, which turns a container element with no image into a
    # ContainerDescription with an empty identifier rather than failing to load.
    source = _doc(container=None, requirements=[requirement])
    source["class"] = "GalaxyTool"
    tool_source = YamlToolSource(source)

    _, containers, _, _, _ = tool_source.parse_requirements()

    assert [c.identifier for c in containers] == [""]


def test_parser_defaults_container_requirement_type_to_docker():
    tool_source = YamlToolSource(
        _doc(container=None, requirements=[{"type": "container", "container": {"container_id": "busybox"}}])
    )

    _, containers, _, _, _ = tool_source.parse_requirements()

    assert containers[0].type == "docker"


def test_top_level_container_takes_precedence_over_requirement():
    tool_source = YamlToolSource(
        _doc(
            container="quay.io/biocontainers/python:3.13",
            requirements=[
                {
                    "type": "container",
                    "container": {"type": "docker", "container_id": "busybox:latest"},
                }
            ],
        )
    )
    _, containers, _, _, _ = tool_source.parse_requirements()
    assert len(containers) == 1
    assert containers[0].identifier == "quay.io/biocontainers/python:3.13"
