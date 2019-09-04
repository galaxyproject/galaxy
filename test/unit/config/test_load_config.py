from galaxy.config import GalaxyAppConfiguration


MOCK_PROPERTIES = {
    'property1': {'default': 'a'},
    'property2': {'default': 'b'},
    'property3': {'something_else': 'c'},
}


class MockSchema():
    @property
    def app_schema(self):
        return MOCK_PROPERTIES


def test_load_raw_config_from_schema(monkeypatch):

    def mock_load_schema(self):
        self.schema = MockSchema()

    def mock_process_config(self, kwargs):
        pass

    monkeypatch.setattr(GalaxyAppConfiguration, '_load_schema', mock_load_schema)
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)

    config = GalaxyAppConfiguration()

    assert len(config._raw_config) == 3
    assert config._raw_config['property1'] == 'a'
    assert config._raw_config['property2'] == 'b'
    assert config._raw_config['property3'] is None
