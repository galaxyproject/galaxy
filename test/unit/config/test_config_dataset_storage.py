import pytest

from galaxy import config
from galaxy.config import BaseAppConfiguration


@pytest.fixture
def mock_config_file(monkeypatch):
    # Patch this; otherwise tempfile.tempdir will be set, which is a global variable that
    # defines the value of the default `dir` argument to the functions in Python's
    # tempfile module - which breaks multiple tests.
    monkeypatch.setattr(config.GalaxyAppConfiguration, '_override_tempdir', lambda a, b: None)


def test_uuid_1(mock_config_file, monkeypatch):
    # file_path dir name = `objects`, set by user
    appconfig = config.GalaxyAppConfiguration(file_path='objects')

    assert appconfig.object_store_store_by == 'uuid'


def test_uuid_2(mock_config_file, monkeypatch):
    # file_path dir name = `objects`, not set: default value is used
    monkeypatch.setattr(BaseAppConfiguration, 'is_set', lambda a, b: False)
    appconfig = config.GalaxyAppConfiguration(file_path='objects')

    assert appconfig.object_store_store_by == 'uuid'


def test_id_1(mock_config_file, monkeypatch):
    # file_path dir name = `not_objects`, set by user
    appconfig = config.GalaxyAppConfiguration(file_path='not_objects')

    assert appconfig.object_store_store_by == 'id'


def test_id_2(mock_config_file, monkeypatch):
    # file_path dir name = `files`, not set: default value is used
    monkeypatch.setattr(BaseAppConfiguration, 'is_set', lambda a, b: False)
    appconfig = config.GalaxyAppConfiguration(file_path='files')

    assert appconfig.object_store_store_by == 'id'
