import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.config.schema import AppSchema
from galaxy.util.yaml_util import (
    ordered_load,
    OrderedLoader,
)


MOCK_YAML = '''
    type: map
    desc: mocked schema
    mapping:
      mockgalaxy:
        type: map
        mapping:
          property1:
            default: a
            type: str
          property2:
            default: 1
            type: int
            reloadable: true
          property3:
            default: 1.0
            type: float
            reloadable: true
          property4:
            default: true
            type: bool
          property5:
            something_else: b
            type: invalid
          property6:
            something_else: b
    '''


@pytest.fixture
def mock_init(monkeypatch):

    def mock_read_schema(self, path):
        return ordered_load(MOCK_YAML)

    def mock_init(self, stream):
        super(OrderedLoader, self).__init__(stream)

    def mock_load_schema(self):
        return AppSchema('no path', 'mockgalaxy')

    def mock_process_config(self, kwargs):
        pass

    monkeypatch.setattr(AppSchema, '_read_schema', mock_read_schema)
    monkeypatch.setattr(OrderedLoader, '__init__', mock_init)
    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)


def test_load_config_from_schema(mock_init):
    config = GalaxyAppConfiguration()

    assert len(config._raw_config) == 6
    assert config._raw_config['property1'] == 'a'
    assert config._raw_config['property2'] == 1
    assert config._raw_config['property3'] == 1.0
    assert config._raw_config['property4'] is True
    assert config._raw_config['property5'] is None
    assert config._raw_config['property6'] is None

    assert type(config._raw_config['property1']) is str
    assert type(config._raw_config['property2']) is int
    assert type(config._raw_config['property3']) is float
    assert type(config._raw_config['property4']) is bool


def test_update_raw_config_from_kwargs(mock_init):
    config = GalaxyAppConfiguration(property2=2, property3=2.0, another_key=66)

    assert len(config._raw_config) == 6   # no change: another_key NOT added
    assert config._raw_config['property1'] == 'a'  # no change
    assert config._raw_config['property2'] == 2  # updated
    assert config._raw_config['property3'] == 2.0  # updated
    assert config._raw_config['property4'] is True  # no change
    assert config._raw_config['property5'] is None  # no change
    assert config._raw_config['property6'] is None  # no change

    assert type(config._raw_config['property1']) is str
    assert type(config._raw_config['property2']) is int
    assert type(config._raw_config['property3']) is float
    assert type(config._raw_config['property4']) is bool


def test_update_raw_config_from_string_kwargs(mock_init):
    # kwargs may be passed as strings: property data types should not be affected
    config = GalaxyAppConfiguration(property1='b', property2='2', property3='2.0', property4='false')

    assert len(config._raw_config) == 6  # no change
    assert config._raw_config['property1'] == 'b'  # updated
    assert config._raw_config['property2'] == 2  # updated
    assert config._raw_config['property3'] == 2.0  # updated
    assert config._raw_config['property4'] is False  # updated

    assert type(config._raw_config['property1']) is str
    assert type(config._raw_config['property2']) is int
    assert type(config._raw_config['property3']) is float
    assert type(config._raw_config['property4']) is bool


def test_update_raw_config_from_kwargs_with_none(mock_init):
    # should be able to set to null regardless of property's datatype
    config = GalaxyAppConfiguration(
        property1=None, property2=None, property3=None, property4=None, property5=None, property6=None,
    )

    assert config._raw_config['property1'] is None
    assert config._raw_config['property2'] is None
    assert config._raw_config['property3'] is None
    assert config._raw_config['property4'] is None
    assert config._raw_config['property5'] is None
    assert config._raw_config['property6'] is None


def test_update_raw_config_from_kwargs_falsy_not_none(mock_init):
    # if kwargs supplies a falsy value, it should not evaluate to null
    # (ensures code is 'if value is not None' vs. 'if value')
    config = GalaxyAppConfiguration(property1=0)

    assert config._raw_config['property1'] == '0'  # updated
    assert type(config._raw_config['property1']) is str  # and converted to str
