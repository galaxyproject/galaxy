import json
import tempfile
from typing import Any

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
