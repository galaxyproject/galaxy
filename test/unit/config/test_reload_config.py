from pathlib import Path

import pytest

from galaxy import config
from galaxy.config import (
    BaseAppConfiguration,
    reload_config_options,
)
from galaxy.config.schema import AppSchema

R1, R2, N1, N2 = "reloadable1", "reloadable2", "nonrelodable1", "nonreloadable2"  # config options

MOCK_SCHEMA = {
    R1: {"reloadable": True, "default": 1},
    R2: {"reloadable": True, "default": 2},
    N1: {"default": 3},
    N2: {"default": 4},
}


def get_schema(app_mapping):
    return {"mapping": {"_": {"mapping": app_mapping}}}


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(BaseAppConfiguration, "_load_schema", lambda a: AppSchema(Path("no path"), "_"))
    monkeypatch.setattr(AppSchema, "_read_schema", lambda a, b: get_schema(MOCK_SCHEMA))


def test_update_property(mock_init, monkeypatch):
    # This also covers adding a property. When a config file does not set a property,
    # that property is set to its default value. Thus, if we add a reloadable property
    # to the config file, it's the same as modifying that property's value.

    # edits to config file: R2, N1 modified
    monkeypatch.setattr(config, "read_properties_from_file", lambda _: {R1: 1, R2: 42, N1: 99})

    appconfig = BaseAppConfiguration()

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2
    assert getattr(appconfig, N1) == 3

    reload_config_options(appconfig)

    assert getattr(appconfig, R1) == 1  # no change
    assert getattr(appconfig, R2) == 42  # change: reloadable option modified
    assert getattr(appconfig, N1) == 3  # no change: option modified but is non-relodable


def test_overwrite_reloadable_attribute(mock_init, monkeypatch):
    # This is similar to test_update_property, but here we overwrite the attribute before reloading.
    # This can happen if a config property is modified AFTER it has been loaded from schema or kwargs.
    # For example: load `foo` (from schema or kwargs), but then, in a # subsequent step while initializing
    # GalaxyAppConfiguration, do something like this: `foo = resove_path(foo, bar)`. Now the value of `foo`
    # is not what was initially loaded, and if `foo` is reloadable, it will be reset to its default as soon
    # as the config file is modified. To prevent this, we compare the values read from the modified file
    # to the `_raw_config` dict. This test ensures this works correctly.

    # edits to config file: R2 modified
    monkeypatch.setattr(config, "read_properties_from_file", lambda _: {R1: 1, R2: 42})

    appconfig = BaseAppConfiguration()

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2

    # overwrite R1
    setattr(appconfig, R1, 99)
    assert getattr(appconfig, R1) == 99
    # then reload
    reload_config_options(appconfig)
    assert getattr(appconfig, R1) == 99  # no change; should remain overwritten
    assert getattr(appconfig, R2) == 42  # change: reloadable option modified


def test_cant_delete_property(mock_init, monkeypatch):
    # A property should not be deleted: we don't know whether it was initially
    # set to a default, loaded from a config file, env var, etc. Therefore, if a property
    # is removed from the config file, it will not be modified or deleted.

    # edits to config file: R2, N2 deleted
    monkeypatch.setattr(config, "read_properties_from_file", lambda _: {R1: 1, N1: 3})

    appconfig = BaseAppConfiguration()

    assert getattr(appconfig, R1) == 1
    assert getattr(appconfig, R2) == 2
    assert getattr(appconfig, N1) == 3
    assert getattr(appconfig, N2) == 4

    reload_config_options(appconfig)

    assert getattr(appconfig, R1) == 1  # no change
    assert getattr(appconfig, R2) == 2  # no change: option cannot be deleted
    assert getattr(appconfig, N1) == 3  # no change
    assert getattr(appconfig, N2) == 4  # no change: option cannot be deleted
