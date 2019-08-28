from galaxy.config.schema import AppSchema
from galaxy.util.yaml_util import (
    ordered_load,
    OrderedLoader,
)

MOCK_YAML = '''
    type: map
    desc: mocked schema
    foo: bar
    mapping:
      mockgalaxy:
        type: map
        mapping:
          option:
            attr1: a
            attr2: b
    '''


def test_schema_is_loaded(monkeypatch):

    def mock_read_schema(self, path):
        return ordered_load(MOCK_YAML)

    def mock_init(self, stream):
        super(OrderedLoader, self).__init__(stream)

    monkeypatch.setattr(AppSchema, '_read_schema', mock_read_schema)
    monkeypatch.setattr(OrderedLoader, '__init__', mock_init)

    loaded_schema = AppSchema('no path', 'mockgalaxy')
    data = ordered_load(MOCK_YAML)

    assert loaded_schema.description == data['desc']
    assert loaded_schema.raw_schema['foo'] == 'bar'
    assert loaded_schema.app_schema['option']['attr1'] == 'a'
    assert loaded_schema.get_app_option('option')['attr2'] == 'b'
