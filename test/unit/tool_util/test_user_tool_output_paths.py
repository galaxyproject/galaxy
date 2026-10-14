import pytest
from pydantic import ValidationError

from galaxy.tool_util_models import UserToolSource
from galaxy.tool_util_models.tool_outputs import IncomingUserToolOutputDataset


def _output(from_work_dir):
    return {"name": "output", "type": "data", "format": "txt", "from_work_dir": from_work_dir}


@pytest.mark.parametrize(
    "from_work_dir",
    [
        "output.txt",
        "results/output.txt",
        "a/b/out-1_v2+x.tsv",
        ".hidden",
        "index",
        "./output.txt",
        "a..b",
        "out put.txt",
    ],
)
def test_accepts_relative_work_dir_path(from_work_dir):
    assert IncomingUserToolOutputDataset.model_validate(_output(from_work_dir)).from_work_dir == from_work_dir


@pytest.mark.parametrize(
    "from_work_dir",
    ["../x", "a/../../x", "a/../b", "/abs", "/abs/output.txt", "..", ".", "", "x\0y"],
)
def test_rejects_unsafe_work_dir_path(from_work_dir):
    with pytest.raises(ValidationError, match="from_work_dir must be a relative path"):
        IncomingUserToolOutputDataset.model_validate(_output(from_work_dir))


def test_user_tool_source_rejects_parent_directory_from_work_dir():
    definition = {
        "class": "GalaxyUserTool",
        "id": "copy_out",
        "name": "copy_out",
        "version": "0.1",
        "container": "busybox",
        "shell_command": "echo hi > output.txt",
        "inputs": [],
        "outputs": [_output("../output.txt")],
    }
    with pytest.raises(ValidationError, match="from_work_dir must be a relative path"):
        UserToolSource.model_validate(definition)
    definition["outputs"] = [_output("output.txt")]
    UserToolSource.model_validate(definition)
