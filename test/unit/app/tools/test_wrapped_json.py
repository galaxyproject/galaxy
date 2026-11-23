from types import SimpleNamespace
from typing import (
    Any,
    cast,
)

from galaxy.job_execution.compute_environment import ComputeEnvironment
from galaxy.tools.parameters.wrapped_json import json_wrap
from galaxy.tools.wrappers import DatasetFilenameWrapper

COMPUTE_PATH = "/pulsar/staging/1/inputs/dataset_1.dat"


class _Dataset:
    def __init__(self, path, extension):
        self.path = path
        self.extension = extension
        self.ext = extension
        self.id = 1
        self.metadata = {}
        self.has_deferred_data = False

    def get_file_name(self, sync_cache=True):
        return self.path

    def to_dict(self):
        return {"file_ext": self.extension, "file_size": 0, "name": "input"}


class _ComputeEnvironment:
    def input_path_rewrite(self, dataset):
        return COMPUTE_PATH


def _wrap(tmp_path, contents, extension, load_contents):
    path = tmp_path / "dataset_1.dat"
    path.write_text(contents)
    wrapper = DatasetFilenameWrapper(
        cast(Any, _Dataset(str(path), extension)),
        compute_environment=cast(ComputeEnvironment, _ComputeEnvironment()),
    )
    assert str(wrapper) == COMPUTE_PATH
    data_input = SimpleNamespace(name="input1", type="data", multiple=False, load_contents=load_contents)
    return json_wrap({"input1": data_input}, {"input1": wrapper}, 24.0, handle_files="OBJECT")


def test_load_contents_reads_galaxy_file_before_compute_path_exists(tmp_path):
    assert _wrap(tmp_path, "a line\n", "txt", load_contents=64)["input1"]["contents"] == "a line\n"


def test_null_expression_json_read_before_compute_path_exists(tmp_path):
    assert _wrap(tmp_path, "null", "expression.json", load_contents=0)["input1"] is None
