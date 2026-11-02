from typing import Any

import pytest

from galaxy.util import parse_xml_string
from galaxy.util.plugin_config import (
    load_plugins,
    PluginConfigSource,
)


class KnownPlugin:
    def __init__(self, **kwds: Any) -> None:
        self.kwds = kwds


PLUGINS = {"known": KnownPlugin}


def test_load_plugins_from_dicts() -> None:
    source = PluginConfigSource("dict", [{"type": "known", "foo": "bar"}])
    (plugin,) = load_plugins(PLUGINS, source, {"extra": 1})
    assert isinstance(plugin, KnownPlugin)
    assert plugin.kwds == {"type": "known", "foo": "bar", "extra": 1}


def test_load_plugins_from_dicts_unknown_type() -> None:
    source = PluginConfigSource("dict", [{"type": "homebrew"}])
    with pytest.raises(Exception, match=r"Failed to find plugin of type \[homebrew\] in available plugin types"):
        load_plugins(PLUGINS, source)


def test_load_plugins_from_element_unknown_type() -> None:
    source = PluginConfigSource("xml", parse_xml_string("<plugins><homebrew /></plugins>"))
    with pytest.raises(Exception, match=r"Failed to find plugin of type \[homebrew\] in available plugin types"):
        load_plugins(PLUGINS, source)
