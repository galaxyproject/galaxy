from galaxy.config.schema import AppSchema
from galaxy.util.yaml_util import (
    ordered_load,
    OrderedLoader,
)

MOCK_YAML = """
    type: map
    desc: mocked schema
    foo: bar
    mapping:
      mockgalaxy:
        type: map
        mapping:
          property1:
            default: a
            type: str
            path_resolves_to: foo
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
            path_resolves_to: foo
          property5:
            something_else: b
            type: invalid
          property6:
            something_else: b
    """


def test_schema_is_loaded(monkeypatch):
    def mock_read_schema(self, path):
        return ordered_load(MOCK_YAML)

    def mock_init(self, stream):
        super(OrderedLoader, self).__init__(stream)

    monkeypatch.setattr(AppSchema, "_read_schema", mock_read_schema)
    monkeypatch.setattr(OrderedLoader, "__init__", mock_init)

    schema = AppSchema("no path", "mockgalaxy")
    data = ordered_load(MOCK_YAML)

    assert schema.description == data["desc"]
    assert schema.raw_schema["foo"] == "bar"

    assert len(schema.defaults) == 6
    assert schema.defaults["property1"] == "a"
    assert schema.defaults["property2"] == 1
    assert schema.defaults["property3"] == 1.0
    assert schema.defaults["property4"] is True
    assert schema.defaults["property5"] is None
    assert schema.defaults["property6"] is None

    assert type(schema.defaults["property1"]) is str
    assert type(schema.defaults["property2"]) is int
    assert type(schema.defaults["property3"]) is float
    assert type(schema.defaults["property4"]) is bool

    assert len(schema.reloadable_options) == 2
    assert "property2" in schema.reloadable_options
    assert "property3" in schema.reloadable_options

    assert len(schema.paths_to_resolve) == 2
    assert "property1" in schema.paths_to_resolve
    assert "property4" in schema.paths_to_resolve
