from galaxy import config
from galaxy.config import reload_config_options


R1, R2, N1, N2 = 'reloadable1', 'reloadable2', 'nonrelodable1', 'nonreloadable2'  # config options


class MockGalaxyAppConfiguration():

    class MockSchema():
        reloadable_options = {R1, R2}

    def __init__(self, properties):
        self.config_file = None
        self.schema = self.MockSchema
        self._raw_config = {}
        for key, value in properties.items():
            setattr(self, key, value)
            self._raw_config[key] = value

    def update_reloadable_property(self, key, value):
        setattr(self, key, value)


def test_update_property(monkeypatch):
    # This also covers adding a property. When a config file does not set a property,
    # that property is set to its default value. Thus, if we add a reloadable property
    # to the config file, it's the same as modifying that property's value.
    appconfig = MockGalaxyAppConfiguration({R1: 1, R2: 2, N1: 3})

    def mock_read_properties_from_file(values):
        return {R1: 1, R2: 42, N1: 99}  # edits: R2, N1 modified

    monkeypatch.setattr(config, 'read_properties_from_file', mock_read_properties_from_file)

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2
    assert getattr(appconfig, N1) == 3

    reload_config_options(appconfig)

    assert getattr(appconfig, R1) == 1  # no change
    assert getattr(appconfig, R2) == 42  # change: reloadable option modified
    assert getattr(appconfig, N1) == 3  # no change: option modified but is non-relodable


def test_overwrite_reloadable_attribute(monkeypatch):
    # This is similar to test_update_property, but here we overwrite the attribute before reloading.
    # This can happen if a config property is modified AFTER it has been loaded from schema or kwargs.
    # For example: load `foo` (from schema or kwargs), but then, in a # subsequent step while initializing
    # GalaxyAppConfiguration, do something like this: `foo = resove_path(foo, bar)`. Now the value of `foo`
    # is not what was initially loaded, and if `foo` is reloadable, it will be reset to its default as soon
    # as the config file is modified. To prevent this, we compare the values read from the modified file
    # to the `_raw_config` dict. This test ensures this works correctly.
    appconfig = MockGalaxyAppConfiguration({R1: 1, R2: 2, N1: 3})

    def mock_read_properties_from_file(values):
        return {R1: 1, R2: 42}  # edits: R2 modified

    monkeypatch.setattr(config, 'read_properties_from_file', mock_read_properties_from_file)

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2

    # overwrite R1
    setattr(appconfig, R1, 99)
    assert getattr(appconfig, R1) == 99
    # then reload
    reload_config_options(appconfig)
    assert getattr(appconfig, R1) == 99  # no change; should remain overwritten
    assert getattr(appconfig, R2) == 42  # change: reloadable option modified


def test_cant_delete_property(monkeypatch):
    # A property should not be deleted: we don't know whether it was initially
    # set to a default, loaded from a config file, env var, etc. Therefore, if a property
    # is removed from the config file, it will not be modified or deleted.
    appconfig = MockGalaxyAppConfiguration({R1: 1, R2: 2, N1: 3, N2: 4})

    def mock_read_properties_from_file(values):
        return {R1: 1, N1: 3}  # edits: R2, N2 deleted

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
