import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.config.schema import AppSchema


MOCK_DEPRECATED_DIRS = {
    'my_config_dir': 'old-config',
    'my_data_dir': 'old-database',
}

# Mock properties loaded from schema (all options represent paths)
MOCK_SCHEMA = {
    'my_config_dir': {
        'type': 'str',
        'default': 'my-config',
    },
    'my_data_dir': {
        'type': 'str',
        'default': 'my-data',
    },
    'path1': {
        'type': 'str',
        'default': 'my-config-files',
        'path_resolves_to': 'my_config_dir',
    },
    'path2': {
        'type': 'str',
        'default': 'my-data-files',
        'path_resolves_to': 'my_data_dir',
    },
    'path3': {
        'type': 'str',
        'default': 'my-other-files',
    }
}


def get_schema(app_mapping):
    return {'mapping': {'galaxy': {'mapping': app_mapping}}}


def test_deprecated_prefixes_set_correctly(monkeypatch):
    # Before we mock them, check that correct values are assigned
    monkeypatch.setattr(AppSchema, '_read_schema', lambda a, b: get_schema(MOCK_SCHEMA))
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', lambda a, b: None)

    config = GalaxyAppConfiguration()
    assert config.deprecated_dirs == {'config_dir': 'config', 'data_dir': 'database'}


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(AppSchema, '_read_schema', lambda a, b: get_schema(MOCK_SCHEMA))
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', lambda a, b: None)
    monkeypatch.setattr(GalaxyAppConfiguration, 'deprecated_dirs', MOCK_DEPRECATED_DIRS)


def test_mock_schema_is_loaded(mock_init):
    # Check that mock is loaded as expected
    config = GalaxyAppConfiguration()
    assert len(config._raw_config) == 5
    assert config._raw_config['my_config_dir'] == 'my-config'
    assert config._raw_config['my_data_dir'] == 'my-data'
    assert config._raw_config['path1'] == 'my-config-files'
    assert config._raw_config['path2'] == 'my-data-files'
    assert config._raw_config['path3'] == 'my-other-files'


def test_no_kwargs(mock_init):
    # Expected: use default from schema, then resolve
    config = GalaxyAppConfiguration()
    assert config.path1 == 'my-config/my-config-files'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path(mock_init):
    # Expected: use value from kwargs, then resolve
    new_path1 = 'foo1/bar'
    new_path2 = 'foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_ablsolute_path(mock_init):
    # Expected: use value from kwargs, do NOT resolve
    new_path1 = '/foo1/bar'
    new_path2 = '/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == new_path1  # NOT resolved
    assert config.path2 == new_path2  # NOT resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config/foo1/bar'
    new_path2 = 'old-database/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/foo1/bar'  # stripped of old prefix, resolved
    assert config.path2 == 'my-data/foo2/bar'  # stripped of old prefix, resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_for_other_option(mock_init):
    # Expect: use value from kwargs, do NOT strip old prefix, then resolve
    # Reason: deprecated dirs are option-specific: we don't want to strip 'old-config'
    # (deprecated for the config_dir option) if it's used for another option
    new_path1 = 'old-database/foo1/bar'
    new_path2 = 'old-config/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_empty_after_strip(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config'
    config = GalaxyAppConfiguration(path1=new_path1)

    assert config.path1 == 'my-config/'  # stripped of old prefix, then resolved
    assert config.path2 == 'my-data/my-data-files'  # stripped of old prefix, then resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_set_to_null(mock_init):
    # Expected: allow overriding with null, then resolve
    # This is not a common scenario, but it does happen: one example is
    # `job_config` set to `None` when testing
    config = GalaxyAppConfiguration(path1=None)

    assert config.path1 == 'my-config'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change
