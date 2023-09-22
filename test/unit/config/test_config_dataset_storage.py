import os.path

from galaxy import config
from galaxy.config import BaseAppConfiguration


def test_object_store_store_by_set():
    # object_store_store_by set by admin
    appconfig = config.GalaxyAppConfiguration(object_store_store_by="id", override_tempdir=False)
    assert appconfig.object_store_store_by == "id"


def test_uuid_1():
    # object_store_store_by not set
    # file_path set by admin to `objects` (no need for the dir to exist)
    appconfig = config.GalaxyAppConfiguration(file_path="objects", override_tempdir=False)

    assert appconfig.object_store_store_by == "uuid"


def test_uuid_2(monkeypatch):
    # object_store_store_by not set
    # file_path not set, `files` dir doesn't exist
    monkeypatch.setattr(BaseAppConfiguration, "_path_exists", lambda self, path: False)
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)

    assert appconfig.object_store_store_by == "uuid"


def test_id_1():
    # object_store_store_by not set
    # file_path set by admin to `not_objects` (no need for the dir to exist)
    appconfig = config.GalaxyAppConfiguration(file_path="not_objects", override_tempdir=False)

    assert appconfig.object_store_store_by == "id"


def test_id_2(monkeypatch):
    # object_store_store_by not set
    # file_path not set, `files` dir exists
    monkeypatch.setattr(
        BaseAppConfiguration, "_path_exists", lambda self, path: True if os.path.basename(path) == "files" else False
    )
    appconfig = config.GalaxyAppConfiguration(override_tempdir=False)

    assert appconfig.object_store_store_by == "id"
