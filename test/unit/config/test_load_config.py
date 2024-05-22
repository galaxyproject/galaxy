from pathlib import Path

import pytest

from galaxy.config import BaseAppConfiguration
from galaxy.config.schema import AppSchema

MOCK_SCHEMA = {
    "property1": {"default": "a", "type": "str"},  # str
    "property2": {"default": 1, "type": "int"},  # int
    "property3": {"default": 1.0, "type": "float"},  # float
    "property4": {"default": True, "type": "bool"},  # bool
    "property5": {"something_else": "b", "type": "invalid"},
    "property6": {"something_else": "b"},  # no type
}


MOCK_SCHEMA_DBURL = {
    "database_connection": {"type": "str"},
    "install_database_connection": {"type": "str"},
}


def get_schema(app_mapping):
    return {"mapping": {"_": {"mapping": app_mapping}}}


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(BaseAppConfiguration, "_load_schema", lambda a: AppSchema(Path("no path"), "_"))
    monkeypatch.setattr(AppSchema, "_read_schema", lambda a, b: get_schema(MOCK_SCHEMA))


@pytest.fixture
def mock_init_dburl(mock_init, monkeypatch):
    monkeypatch.setattr(AppSchema, "_read_schema", lambda a, b: get_schema(MOCK_SCHEMA_DBURL))


def test_load_config_from_schema(mock_init):
    # If the schema has a default value for a property foo, that value will be
    # assigned to config.foo. Otherwise, the value of config.foo will be None.
    config = BaseAppConfiguration()

    assert len(config._raw_config) == 6
    assert config.property1 == "a"
    assert config.property2 == 1
    assert config.property3 == 1.0
    assert config.property4 is True
    assert config.property5 is None
    assert config.property6 is None

    assert isinstance(config.property1, str)
    assert isinstance(config.property2, int)
    assert isinstance(config.property3, float)
    assert isinstance(config.property4, bool)


def test_update_raw_config_from_kwargs(mock_init):
    config = BaseAppConfiguration(property2=2, property3=2.0, another_key=66)

    assert len(config._raw_config) == 6  # no change: another_key NOT added
    assert config._raw_config["property1"] == "a"  # no change
    assert config._raw_config["property2"] == 2  # updated
    assert config._raw_config["property3"] == 2.0  # updated
    assert config._raw_config["property4"] is True  # no change
    assert config._raw_config["property5"] is None  # no change
    assert config._raw_config["property6"] is None  # no change

    assert isinstance(config._raw_config["property1"], str)
    assert isinstance(config._raw_config["property2"], int)
    assert isinstance(config._raw_config["property3"], float)
    assert isinstance(config._raw_config["property4"], bool)


def test_update_raw_config_from_string_kwargs(mock_init):
    # kwargs may be passed as strings: property data types should not be affected
    config = BaseAppConfiguration(property1="b", property2="2", property3="2.0", property4="false")

    assert len(config._raw_config) == 6  # no change
    assert config._raw_config["property1"] == "b"  # updated
    assert config._raw_config["property2"] == 2  # updated
    assert config._raw_config["property3"] == 2.0  # updated
    assert config._raw_config["property4"] is False  # updated

    assert isinstance(config._raw_config["property1"], str)
    assert isinstance(config._raw_config["property2"], int)
    assert isinstance(config._raw_config["property3"], float)
    assert isinstance(config._raw_config["property4"], bool)


def test_update_raw_config_from_kwargs_with_none(mock_init):
    # should be able to set to null regardless of property's datatype
    config = BaseAppConfiguration(
        property1=None,
        property2=None,
        property3=None,
        property4=None,
        property5=None,
        property6=None,
    )

    assert config._raw_config["property1"] is None
    assert config._raw_config["property2"] is None
    assert config._raw_config["property3"] is None
    assert config._raw_config["property4"] is None
    assert config._raw_config["property5"] is None
    assert config._raw_config["property6"] is None


def test_update_raw_config_from_kwargs_falsy_not_none(mock_init):
    # if kwargs supplies a falsy value, it should not evaluate to null
    # (ensures code is 'if value is not None' vs. 'if value')
    config = BaseAppConfiguration(property1=0)

    assert config._raw_config["property1"] == "0"  # updated
    assert isinstance(config._raw_config["property1"], str)  # and converted to str


def test_unset_renamed_option_set_by_old_option(mock_init, monkeypatch):
    monkeypatch.setattr(BaseAppConfiguration, "renamed_options", {"old_property1": "property1"})
    config = BaseAppConfiguration(old_property1="b")

    assert config._raw_config["property1"] == "b"


def test_set_renamed_option_not_overridden_by_old_option(mock_init):
    config = BaseAppConfiguration(old_property1="b", property1="c")

    assert config._raw_config["property1"] == "c"


def test_is_set(mock_init):
    # if an option is set from kwargs, is_set() returns True, otherwise False
    # Note: is_set() here means 'value is set by user', which includes setting
    # to None or setting to the same value as the schema default.

    # First, test that none are set
    config = BaseAppConfiguration()
    assert not config.is_set("property1")
    assert not config.is_set("property2")
    assert not config.is_set("property3")
    assert not config.is_set("property4")
    assert not config.is_set("property5")
    assert not config.is_set("property6")

    # Now set all values, including setting to None and setting to the schema default
    config = BaseAppConfiguration(
        property1="b",  # default = 'a'  (overwrites default w/'a')
        property2=None,  # default = 1    (overwrites default w/None)
        property3=1.0,  # default = 1.0  (same as default: 1.0)
        property4=True,  # default = True (same as default: True)
        property5=None,  # default = None (same as default: None)
        property6=1,
    )  # default = None (overwrites default w/None)

    assert config.is_set("property1")
    assert config.is_set("property2")
    assert config.is_set("property3")
    assert config.is_set("property4")
    assert config.is_set("property4")
    assert config.is_set("property6")


def test_deprecated_postgres_urls_are_fixed(mock_init_dburl):
    error_message = '"postgres" prefix should become "postgresql"'

    config = BaseAppConfiguration(
        database_connection="postgres://foo", install_database_connection="postgresql://foo"  # incorrect
    )  # correct

    assert config.database_connection == "postgresql://foo", error_message
    assert config.install_database_connection == "postgresql://foo"

    config = BaseAppConfiguration(
        database_connection="postgresql+psycopg2://foo",  # correct
        install_database_connection="postgres+psycopg2://foo",
    )  # incorrect

    assert config.database_connection == "postgresql+psycopg2://foo", error_message
    assert config.install_database_connection == "postgresql+psycopg2://foo"
