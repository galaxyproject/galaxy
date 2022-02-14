import os.path

import pytest

from galaxy import config
from galaxy.config import BaseAppConfiguration


@pytest.fixture
def mock_config_file(monkeypatch):
    # Patch this; otherwise tempfile.tempdir will be set, which is a global variable that
    # defines the value of the default `dir` argument to the functions in Python's
    # tempfile module - which breaks multiple tests.
    monkeypatch.setattr(config.GalaxyAppConfiguration, "_override_tempdir", lambda a, b: None)


def test_object_store_store_by_set(mock_config_file, monkeypatch):
    # object_store_store_by set by admin
    appconfig = config.GalaxyAppConfiguration(object_store_store_by="id")
    assert appconfig.object_store_store_by == "id"


def test_uuid_1(mock_config_file, monkeypatch):
    # object_store_store_by not set
    # file_path set by admin to `objects` (no need for the dir to exist)
    appconfig = config.GalaxyAppConfiguration(file_path="objects")

    assert appconfig.object_store_store_by == "uuid"


def test_uuid_2(mock_config_file, monkeypatch):
    # object_store_store_by not set
    # file_path not set, `files` dir doesn't exist
    monkeypatch.setattr(BaseAppConfiguration, "_path_exists", lambda self, path: False)
    appconfig = config.GalaxyAppConfiguration()

    assert appconfig.object_store_store_by == "uuid"


def test_id_1(mock_config_file, monkeypatch):
    # object_store_store_by not set
    # file_path set by admin to `not_objects` (no need for the dir to exist)
    appconfig = config.GalaxyAppConfiguration(file_path="not_objects")

    assert appconfig.object_store_store_by == "id"


def test_id_2(mock_config_file, monkeypatch):
    # object_store_store_by not set
    # file_path not set, `files` dir exists
    monkeypatch.setattr(
        BaseAppConfiguration, "_path_exists", lambda self, path: True if os.path.basename(path) == "files" else False
    )
    appconfig = config.GalaxyAppConfiguration()

    assert appconfig.object_store_store_by == "id"
