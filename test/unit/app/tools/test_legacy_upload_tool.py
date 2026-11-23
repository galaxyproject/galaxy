import importlib.util
import os

import pytest

from galaxy.datatypes import sniff
from galaxy.datatypes.upload_util import UploadProblemException
from galaxy.util.bunch import Bunch

# Resolve symlinks: the packages test harness reaches this file through a symlink.
GALAXY_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir, os.pardir, os.pardir)
)
UPLOAD_TOOL_PATH = os.path.join(GALAXY_ROOT, "tools", "data_source", "upload.py")

URL = "https://user:sec ret@example.org/missing.bed"


@pytest.fixture
def upload_tool(monkeypatch):
    if not os.path.exists(UPLOAD_TOOL_PATH):
        pytest.skip("legacy upload tool not in this checkout")
    spec = importlib.util.spec_from_file_location("legacy_upload_tool", UPLOAD_TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def failing_stream_url_to_file(path, **kwargs):
        raise OSError(f"404 Client Error: Not Found for url: {path.strip()}")

    monkeypatch.setattr(sniff, "stream_url_to_file", failing_stream_url_to_file)
    monkeypatch.setattr(module, "get_file_sources", lambda: None)
    return module


def test_url_fetch_error_hides_userinfo(upload_tool, tmp_path):
    dataset = Bunch(type="url", path=URL, file_type="auto", dataset_id=1)
    with pytest.raises(UploadProblemException) as exc_info:
        upload_tool.add_file(dataset, None, str(tmp_path / "out.dat"))
    message = str(exc_info.value)
    assert "sec ret" not in message
    assert "https://example.org/missing.bed" in message


def test_composite_url_fetch_error_hides_userinfo(upload_tool, tmp_path):
    dataset = Bunch(file_type=None, composite_files={}, composite_file_paths={}, primary_file=URL, dataset_id=1)
    with pytest.raises(UploadProblemException) as exc_info:
        upload_tool.add_composite_file(dataset, None, str(tmp_path / "out.dat"), str(tmp_path / "files"))
    message = str(exc_info.value)
    assert "sec ret" not in message
    assert "https://example.org/missing.bed" in message
