import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ConfigurationError


# When a config property 'foo' has an attribute 'path_resolves_to', that attribute is a reference to
# another property 'bar'. Together, these two properties form a graph where 'foo' and 'bar are
# vertices and the reference from 'foo' to 'bar' is a directed edge.
#
# A schema may have any number of such implicit graphs, each having one or more edges. All together,
# they should form a DAG (directed acyclic graph).
#
# These tests ensure that the graph is loaded correctly for a variety of valid configurations,
# whereas an invalid configuration raises an error.


@pytest.fixture
def mock_config(monkeypatch):
    def mock_process_config(self, kwargs):
        pass
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)


def test_basecase(mock_config, monkeypatch):
    # Check that a valid graph is loaded correctly (this graph has 2 components)
    mock_schema = {
        'component1_path0': {
            'type': 'str',
            'default': 'value0',
        },
        'component1_path1': {
            'type': 'str',
            'default': 'value1',
            'path_resolves_to': 'component1_path0',
        },
        'component1_path2': {
            'type': 'str',
            'default': 'value2',
            'path_resolves_to': 'component1_path1',
        },
        'component2_path0': {
            'type': 'str',
            'default': 'value3',
        },
        'component2_path1': {
            'type': 'str',
            'default': 'value4',
            'path_resolves_to': 'component2_path0',
        },

    }

    def mock_load_schema(self):
        self.appschema = mock_schema
    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    config = GalaxyAppConfiguration()
    assert config.component1_path0 == 'value0'
    assert config.component1_path1 == 'value0/value1'
    assert config.component1_path2 == 'value0/value1/value2'
    assert config.component2_path0 == 'value3'
    assert config.component2_path1 == 'value3/value4'


def test_resolves_to_invalid_property(mock_config, monkeypatch):
    # 'path_resolves_to' should point to an existing property in the schema
    mock_schema = {
        'path0': {
            'type': 'str',
            'default': 'value0',
        },
        'path1': {
            'type': 'str',
            'default': 'value1',
            'path_resolves_to': 'invalid',  # invalid
        },
    }

    def mock_load_schema(self):
        self.appschema = mock_schema

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    with pytest.raises(ConfigurationError):
        GalaxyAppConfiguration()


def test_path_resolution_cycle(mock_config, monkeypatch):
    # Must be a DAG, but this one has a cycle
    mock_schema = {
        'path0': {
            'type': 'str',
            'default': 'value0',
            'path_resolves_to': 'path2',
        },
        'path1': {
            'type': 'str',
            'default': 'value1',
            'path_resolves_to': 'path0',
        },
        'path2': {
            'type': 'str',
            'default': 'value2',
            'path_resolves_to': 'path1',
        },
    }

    def mock_load_schema(self):
        self.appschema = mock_schema

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    with pytest.raises(ConfigurationError):
        GalaxyAppConfiguration()


def test_path_invalid_type(mock_config, monkeypatch):
    # Paths should be strings
    mock_schema = {
        'path0': {
            'type': 'str',
            'default': 'value0',
        },
        'path1': {
            'type': 'float',  # invalid
            'default': 'value1',
            'path_resolves_to': 'path0',
        },
    }

    def mock_load_schema(self):
        self.appschema = mock_schema

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    with pytest.raises(ConfigurationError):
        GalaxyAppConfiguration()


def test_resolves_to_invalid_type(mock_config, monkeypatch):
    # Paths should be strings
    mock_schema = {
        'path0': {
            'type': 'int',  # invalid
            'default': 'value0',
        },
        'path1': {
            'type': 'str',
            'default': 'value1',
            'path_resolves_to': 'path0',
        },
    }

    def mock_load_schema(self):
        self.appschema = mock_schema

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    with pytest.raises(ConfigurationError):
        GalaxyAppConfiguration()


def test_resolves_with_empty_component(mock_config, monkeypatch):
    # A path can be None (root path is never None; may be asigned elsewhere)
    mock_schema = {
        'path0': {
            'type': 'str',
            'default': 'value0',
        },
        'path1': {
            'type': 'str',
            'path_resolves_to': 'path0',
        },
        'path2': {
            'type': 'str',
            'default': 'value2',
            'path_resolves_to': 'path1',
        },
    }

    def mock_load_schema(self):
        self.appschema = mock_schema

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)

    config = GalaxyAppConfiguration()
    assert config.path0 == 'value0'
    assert config.path1 == 'value0'
    assert config.path2 == 'value0/value2'
