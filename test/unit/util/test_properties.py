import os

import pytest

from galaxy.exceptions import InvalidFileFormatError
from galaxy.util import properties
from galaxy.util.properties import (
    get_from_env,
    nice_config_parser,
    read_properties_from_file,
)

KEY1, KEY2, KEY3, KEY4, KEY5, KEY6 = "k1", "k2", "k3", "k4", "k5", "k6"
VAL1, VAL2, VAL3, VAL4, VAL5, VAL6 = 1, 2, 3, 4, 5, 6
OTHER_SECTION = "other"


def test_get_from_env(monkeypatch):
    prefixes = ["pre1_", "pre2_", "pre3_"]

    monkeypatch.setenv("pre1_a", "a-is-set")
    monkeypatch.setenv("pre2_b", "b-is-set")

    assert get_from_env("a", prefixes, "a-default") == "a-is-set"  # selected from first prefix
    assert get_from_env("b", prefixes, "b-default") == "b-is-set"  # selected from second prefix
    assert get_from_env("c", prefixes, "c-default") == "c-default"  # default


def test_get_from_env__no_default(monkeypatch):
    assert get_from_env("a", ["some", "random", "prefixes"]) is None


def test_get_from_env__empty_prefix_ignored(monkeypatch):
    monkeypatch.setenv("a", "a-without-prefix-is-set")
    assert os.getenv("a") == "a-without-prefix-is-set"

    assert get_from_env("a", ["", None], "a-default") == "a-default"  # type: ignore[list-item]


@pytest.fixture
def mock_properties(monkeypatch):
    # Keys in defaults dict and other dicts should not intersect. The tests assume
    # that len(dict1.update(dict2)) == len(dict1) + len(dict2). So, for example, if
    # defaults = {foo: 1, bar:2} and other_section = {foo:3}, the final dict will have len=2.
    def mock_default_properties(path):
        return {KEY1: VAL1, KEY2: VAL2}

    def mock_read_from_yaml(path):
        return {"galaxy": {KEY3: VAL3, KEY4: VAL4}, OTHER_SECTION: {KEY5: VAL5, KEY6: VAL6}}

    class MockConfigParser:
        def __init__(self):
            self._items = {"app:main": [(KEY3, VAL3), (KEY4, VAL4)], OTHER_SECTION: [(KEY5, VAL5), (KEY6, VAL6)]}

        def has_section(self, section):
            return section in self._items.keys()

        def items(self, section):
            return self._items[section] + self.defaults()

        def defaults(self):
            return [(KEY1, VAL1), (KEY2, VAL2)]

    def mock_nice_config_parser(path):
        return MockConfigParser()

    monkeypatch.setattr(properties, "_read_from_yaml_file", mock_read_from_yaml)
    monkeypatch.setattr(properties, "nice_config_parser", mock_nice_config_parser)
    monkeypatch.setattr(properties, "__default_properties", mock_default_properties)


def test_read_galaxy_properties_from_yaml(mock_properties):
    file = "foo.yaml"
    result = read_properties_from_file(file)

    assert len(result) == 4
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2
    assert result[KEY3] == VAL3
    assert result[KEY4] == VAL4


def test_read_other_properties_from_yaml(mock_properties):
    file = "foo.yaml"
    result = read_properties_from_file(file, config_section=OTHER_SECTION)

    assert len(result) == 4
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2
    assert result[KEY5] == VAL5
    assert result[KEY6] == VAL6


def test_get_default_properties_from_yaml(mock_properties):
    file = "foo.yaml"
    result = read_properties_from_file(file, config_section="section's not here, man")

    assert len(result) == 2
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2


def test_read_galaxy_properties_from_ini(mock_properties):
    file = "foo.ini"
    result = read_properties_from_file(file)

    assert len(result) == 4
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2
    assert result[KEY3] == VAL3
    assert result[KEY4] == VAL4


def test_read_other_properties_from_ini(mock_properties):
    file = "foo.ini"
    result = read_properties_from_file(file, config_section=OTHER_SECTION)

    assert len(result) == 4
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2
    assert result[KEY5] == VAL5
    assert result[KEY6] == VAL6


def test_get_default_properties_from_ini(mock_properties):
    file = "foo.ini"
    result = read_properties_from_file(file, config_section="section's not here, man")

    assert len(result) == 2
    assert result[KEY1] == VAL1
    assert result[KEY2] == VAL2


def test_dont_read_properties_from_other_format(mock_properties):
    file = "invalid"
    with pytest.raises(InvalidFileFormatError):
        read_properties_from_file(file)


def test_nice_config_parser(tmp_path):
    conf_path = tmp_path / "config.ini"
    conf_path.write_text(
        """
[main]
foo_path = %(here)s/cow
FOO_PATH123 = hackedtonotchangecase
config_file = %(__file__)s
"""
    )
    config_parser = nice_config_parser(conf_path)
    foo_path = config_parser.get("main", "foo_path")
    assert foo_path == str(tmp_path / "cow")
    assert config_parser.get("main", "FOO_PATH123") == "hackedtonotchangecase"
    assert config_parser.get("main", "config_file") == str(conf_path)


def test_nice_config_parser_custom_exceptions(tmp_path):
    conf_path = tmp_path / "config.ini"
    conf_path.write_text(
        """
[main]
foo_var = %(foobar)s/cow
"""
    )
    config_parser = nice_config_parser(conf_path)
    exc = None
    try:
        config_parser.get("main", "foo_var")
    except Exception as e:
        exc = e
    assert exc is not None
    assert f"Error in file {conf_path}" in str(exc)
    assert "Bad value substitution: option 'foo_var' in section 'main' contains an interpolation key" in str(exc)
