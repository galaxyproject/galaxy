"""Authoring contracts exercised by forms and jobs from raw YAML/JSON sources."""

from pathlib import Path

import pytest

from galaxy_test.base.populators import DescribeUserTool

TOOL_DIR = Path(__file__).resolve().parents[3] / "test" / "functional" / "tools"
SOURCE_DIR = Path(__file__).resolve().parents[1] / "base" / "data" / "user_tools"


def _sources(tool_id, yaml_directory=TOOL_DIR / "parameters"):
    return [
        pytest.param(yaml_directory / f"{tool_id}.yml", id=f"{tool_id}-yaml"),
        pytest.param(SOURCE_DIR / f"{tool_id}.json", id=f"{tool_id}-json"),
    ]


class UnsupportedStructuralInput(Exception):
    pass


@pytest.mark.parametrize(
    "user_tool", _sources("gx_user_repeat", SOURCE_DIR) + _sources("gx_user_section", SOURCE_DIR), indirect=True
)
@pytest.mark.xfail(strict=True, raises=UnsupportedStructuralInput, reason="#23888: canonical groups fail API parsing")
def test_user_structural_contract(user_tool: DescribeUserTool):
    response = user_tool.build_raw()
    if response.status_code == 500:
        raise UnsupportedStructuralInput(response.text)
    assert response.status_code == 200, response.text
    assert response.json()["inputs"][0]["name"] == "group"
