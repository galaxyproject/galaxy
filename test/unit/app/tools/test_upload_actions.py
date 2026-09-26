import json
import tempfile
from typing import Any

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tools.actions.upload import UploadToolAction


class ConcreteUploadToolAction(UploadToolAction):
    def get_output_name(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError


def test_upload_action_reports_urls_from_paramfile():
    upload_params = [
        {"type": "url", "path": "https://example.org/input.txt"},
        {"type": "file", "path": "/tmp/pasted-input.txt"},
    ]
    with tempfile.NamedTemporaryFile(mode="w") as paramfile:
        json.dump(upload_params, paramfile)
        paramfile.flush()
        action = ConcreteUploadToolAction()
        assert list(action.iter_referenced_file_source_uris({"paramfile": paramfile.name})) == [
            "https://example.org/input.txt"
        ]


@pytest.mark.parametrize(
    ("upload_params", "message"),
    [
        ({"type": "url", "path": "https://example.org/input.txt"}, "must contain a list"),
        (["not an object"], "entries must be objects"),
        ([{"type": "url", "path": None}], "URL upload entry is missing its path"),
    ],
)
def test_upload_action_rejects_invalid_paramfile_shape(upload_params, message):
    with tempfile.NamedTemporaryFile(mode="w") as paramfile:
        json.dump(upload_params, paramfile)
        paramfile.flush()
        action = ConcreteUploadToolAction()
        with pytest.raises(RequestParameterInvalidException, match=message):
            list(action.iter_referenced_file_source_uris({"paramfile": paramfile.name}))


def test_upload_action_rejects_missing_paramfile_parameter():
    action = ConcreteUploadToolAction()
    with pytest.raises(RequestParameterInvalidException, match="missing its paramfile"):
        list(action.iter_referenced_file_source_uris({}))


def test_upload_action_does_not_hide_missing_paramfile(tmp_path):
    action = ConcreteUploadToolAction()
    with pytest.raises(FileNotFoundError):
        list(action.iter_referenced_file_source_uris({"paramfile": str(tmp_path / "missing.json")}))


def test_upload_action_does_not_hide_malformed_paramfile():
    with tempfile.NamedTemporaryFile(mode="w") as paramfile:
        paramfile.write("{")
        paramfile.flush()
        action = ConcreteUploadToolAction()
        with pytest.raises(json.JSONDecodeError):
            list(action.iter_referenced_file_source_uris({"paramfile": paramfile.name}))
