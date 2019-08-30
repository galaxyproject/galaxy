from galaxy import config
from galaxy.config import reload_config_options


R1, R2, N1, N2 = 'reloadable1', 'reloadable2', 'nonrelodable1', 'nonreloadable2'  # config options


class MockGalaxyAppConfiguration():
    def __init__(self, properties):
        self.config_file = None
        for key, value in properties.items():
            setattr(self, key, value)

    def update_reloadable_property(self, key, value):
        setattr(self, key, value)


def test_update_property(monkeypatch):
    # This also covers adding a property. When a config file does not set a property,
    # that property is set to its default value. Thus, if we add a reloadable property
    # to the config file, it's the same as modifying that property's value.
    appconfig = MockGalaxyAppConfiguration({R1: 1, R2: 2, N1: 3})

    def mock_read_properties_from_file(values):
        return {R1: 1, R2: 42, N1: 99}  # edits: R2, N1 modified

    def mock_get_reloadable_config_options():
        return {R1: None, R2: None}

    monkeypatch.setattr(config, 'get_reloadable_config_options', mock_get_reloadable_config_options)
    monkeypatch.setattr(config, 'read_properties_from_file', mock_read_properties_from_file)

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2
    assert getattr(appconfig, N1) == 3

    reload_config_options(appconfig)

    assert getattr(appconfig, R1) == 1  # no change
    assert getattr(appconfig, R2) == 42  # change: reloadable option modified
    assert getattr(appconfig, N1) == 3  # no change: option modified but is non-relodable


def test_cant_delete_property(monkeypatch):
    # A property should not be deleted: we don't know whether it was initially
    # set to a default, loaded from a config file, env var, etc. Therefore, if a property
    # is removed from the config file, it will not be modified or deleted.
    appconfig = MockGalaxyAppConfiguration({R1: 1, R2: 2, N1: 3, N2: 4})

    def mock_read_properties_from_file(values):
        return {R1: 1, N1: 3}  # edits: R2, N2 deleted

    def mock_get_reloadable_config_options():
        return {R1: None, R2: None}

    monkeypatch.setattr(config, 'get_reloadable_config_options', mock_get_reloadable_config_options)
    monkeypatch.setattr(config, 'read_properties_from_file', mock_read_properties_from_file)

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2
    assert getattr(appconfig, N1) == 3
    assert getattr(appconfig, N2) == 4

    reload_config_options(appconfig)

    assert getattr(appconfig, R1) == 1  # no change
    assert getattr(appconfig, R2) == 2  # no change: option cannot be deleted
    assert getattr(appconfig, N1) == 3  # no change
    assert getattr(appconfig, N2) == 4  # no change: option cannot be deleted
