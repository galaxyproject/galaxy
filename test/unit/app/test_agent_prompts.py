"""Hold the agent prompt files to the schemas they claim to teach.

``custom_tool_structured.md`` is a system prompt whose entire job is telling a
model what shape validates. Nothing else reads it, so when the models narrow --
as when ``YamlDataParameter.format`` became a ``list[str]`` -- its examples go
stale silently and the prompt starts teaching YAML that consumers reject.

Validating against pydantic alone is not enough. ``_split_format`` normalizes the
legacy comma-separated string form, so ``format: fastq`` satisfies pydantic while
the dumped JSON Schema (what a structured-output consumer actually enforces)
rejects it. These tests check both.
"""

import re
from pathlib import Path
from typing import (
    Any,
)

import jsonschema
import pytest
import yaml

from galaxy.tool_util_models import UserToolSourceAuthoringView
from galaxy.util import galaxy_directory

PROMPT_DIR = Path(galaxy_directory()) / "lib" / "galaxy" / "agents" / "prompts"
CUSTOM_TOOL_PROMPT = PROMPT_DIR / "custom_tool_structured.md"

YAML_FENCE = re.compile(r"```yaml\n(.*?)```", re.DOTALL)
INPUT_REF = re.compile(r"\$\(inputs\.([A-Za-z_][A-Za-z0-9_]*)")


def _yaml_blocks(path: Path) -> list[tuple[int, Any]]:
    """Parse every ```yaml fence in a prompt, keyed by position for readable failures."""
    blocks = []
    for index, raw in enumerate(YAML_FENCE.findall(path.read_text())):
        blocks.append((index, yaml.safe_load(raw)))
    return blocks


def _as_tool(fragment: dict[str, Any]) -> dict[str, Any]:
    """Splice a prompt fragment into an otherwise-valid tool.

    Most examples in the prompt are fragments -- a bare ``inputs:`` list, a
    ``configfiles:`` entry -- that only mean anything in the context of a whole
    tool. Any input the fragment's command references is declared automatically so
    the cross-reference validator doesn't fire on an excerpt taken out of context.
    """
    tool: dict[str, Any] = {
        "class": "GalaxyUserTool",
        "id": "example-tool",
        "name": "Example tool",
        "version": "0.1.0",
        "container": "busybox",
        "shell_command": "true",
        "inputs": [],
        "outputs": [],
        **fragment,
    }
    referenced = set(INPUT_REF.findall(tool["shell_command"]))
    for configfile in tool.get("configfiles") or []:
        referenced |= set(INPUT_REF.findall(configfile.get("content", "")))
    declared = {declared_input["name"] for declared_input in tool["inputs"]}
    for name in sorted(referenced - declared):
        tool["inputs"].append({"name": name, "type": "data"})
    return tool


def _prompt_examples() -> list[tuple[int, dict[str, Any]]]:
    return [(index, _as_tool(block)) for index, block in _yaml_blocks(CUSTOM_TOOL_PROMPT) if isinstance(block, dict)]


@pytest.mark.parametrize("index,tool", _prompt_examples())
def test_custom_tool_prompt_examples_satisfy_pydantic(index: int, tool: dict[str, Any]) -> None:
    """Every YAML example in the prompt must validate as a tool."""
    UserToolSourceAuthoringView.model_validate(tool)


@pytest.mark.parametrize("index,tool", _prompt_examples())
def test_custom_tool_prompt_examples_satisfy_json_schema(index: int, tool: dict[str, Any]) -> None:
    """And must satisfy the dumped schema, which has no before-validators to lean on.

    This is the half that catches a scalar where the model declares a list.
    """
    schema = UserToolSourceAuthoringView.model_json_schema()
    errors = sorted(jsonschema.Draft202012Validator(schema).iter_errors(tool), key=str)
    assert not errors, "\n".join(f"{list(error.absolute_path)}: {error.message}" for error in errors)


def test_custom_tool_prompt_documents_a_data_input_format() -> None:
    """Guard the specific drift that started this: ``format`` is a list, not a scalar.

    Without this the prompt could quietly regress to ``format: fastq`` in an example
    that declares no ``format`` at all and still pass the checks above.
    """
    formats = [
        declared_input["format"]
        for _, tool in _prompt_examples()
        for declared_input in tool["inputs"]
        if "format" in declared_input
    ]
    assert formats, "prompt no longer shows a data input format at all"
    for declared_format in formats:
        assert isinstance(declared_format, list), f"data input format must be a list, got {declared_format!r}"
