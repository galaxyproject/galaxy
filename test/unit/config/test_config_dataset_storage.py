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
    # file_path not set, default = objects
    monkeypatch.setattr(BaseAppConfiguration, 'is_set', lambda a, b: False)
    appconfig = config.GalaxyAppConfiguration(file_path='objects')

    assert appconfig.object_store_store_by == 'uuid'


def test_id_1(mock_config_file, monkeypatch):
    # file_path not set, default = files
    monkeypatch.setattr(BaseAppConfiguration, 'is_set', lambda a, b: False)
    appconfig = config.GalaxyAppConfiguration(file_path='files')

    assert appconfig.object_store_store_by == 'id'


def test_uuid_2(mock_config_file, monkeypatch):
    # file_path set, no dataset found
    monkeypatch.setattr(config, 'find_dataset', lambda a: None)
    appconfig = config.GalaxyAppConfiguration(file_path='foo')

    assert appconfig.object_store_store_by == 'uuid'


def test_uuid_3(mock_config_file, monkeypatch):
    # file_path set, dataset is uuid
    monkeypatch.setattr(config, 'find_dataset', lambda a: '123e4567-e89b-12d3-a456-426614174000.dat')
    appconfig = config.GalaxyAppConfiguration(file_path='foo')

    assert appconfig.object_store_store_by == 'uuid'


def test_id_2(mock_config_file, monkeypatch):
    # file_path set, dataset is not uuid
    monkeypatch.setattr(config, 'find_dataset', lambda a: '1.dat')
    appconfig = config.GalaxyAppConfiguration(file_path='foo')

    assert appconfig.object_store_store_by == 'id'
