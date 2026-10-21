from typing import (
    Any,
)

import pytest
from pydantic import ValidationError

from galaxy.tool_util_models import UserToolSource

TOOL: dict[str, Any] = {
    "class": "GalaxyUserTool",
    "id": "configfile-tool",
    "name": "Configfile tool",
    "version": "0.1.0",
    "container": "busybox",
    "shell_command": "sh script.sh",
    "inputs": [],
    "outputs": [{"type": "data", "name": "out", "from_work_dir": "out.txt"}],
}


def _tool_with_configfile_filename(filename: str) -> dict[str, Any]:
    return {**TOOL, "configfiles": [{"name": "script", "filename": filename, "content": "echo hi > out.txt"}]}


@pytest.mark.parametrize("filename", ["script.sh", ".hidden", "a..b", "sub/x", "./x", "a/b/c.txt"])
def test_relative_configfile_filename_accepted(filename):
    tool = UserToolSource(**_tool_with_configfile_filename(filename))
    assert tool.configfiles
    assert tool.configfiles[0].filename == filename


@pytest.mark.parametrize("filename", ["../x", "/abs/x", "sub/../../x", "a/../b", "..", ".", "", "x\0y"])
def test_configfile_filename_outside_working_directory_rejected(filename):
    with pytest.raises(ValidationError) as exc:
        UserToolSource(**_tool_with_configfile_filename(filename))
    codes = [error["type"] for error in exc.value.errors()]
    assert codes == ["dynamic_tool.configfile_filename_invalid"]


def test_configfile_without_filename_accepted():
    tool = UserToolSource(**{**TOOL, "configfiles": [{"name": "script", "content": "echo hi"}]})
    assert tool.configfiles
    assert tool.configfiles[0].filename is None
