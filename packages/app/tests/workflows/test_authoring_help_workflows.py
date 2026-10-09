import re
from pathlib import Path

import pytest
import yaml
from gxformat2 import python_to_workflow

HELP_PATH = Path(__file__).resolve().parents[3] / "client" / "src" / "components" / "Tool" / "authoringHelp.yml"
YAML_BLOCK = re.compile(r"```yaml\n(?P<source>.*?)\n```", re.DOTALL)


def _documented_workflows() -> list[tuple[str, dict]]:
    workflows = []
    for section in yaml.safe_load(HELP_PATH.read_text())["sections"]:
        for match in YAML_BLOCK.finditer(section["body"]):
            if match.group("source").startswith("class: GalaxyWorkflow\n"):
                workflows.append((section["id"], yaml.safe_load(match.group("source"))))
    return workflows


DOCUMENTED_WORKFLOWS = _documented_workflows()


def test_authoring_help_documents_a_workflow() -> None:
    assert DOCUMENTED_WORKFLOWS


@pytest.mark.parametrize(
    ("section_id", "workflow"),
    DOCUMENTED_WORKFLOWS,
    ids=[section_id for section_id, _ in DOCUMENTED_WORKFLOWS],
)
def test_documented_workflow_converts_with_embedded_tool(section_id: str, workflow: dict) -> None:
    native = python_to_workflow(workflow, None, workflow_directory=None)
    tool_steps = [step for step in native["steps"].values() if step["type"] == "tool"]

    assert tool_steps, section_id
    for step in tool_steps:
        assert step["tool_representation"]["class"] == "GalaxyUserTool"
        assert not step.get("tool_id")
