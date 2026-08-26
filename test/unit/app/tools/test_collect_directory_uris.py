from galaxy.tools.parameters import collect_directory_uris
from galaxy.tools.parameters.basic import (
    DirectoryUriToolParameter,
    TextToolParameter,
)
from galaxy.util import XML


def _directory_uri_param(name):
    return DirectoryUriToolParameter(None, XML(f'<param name="{name}" type="directory_uri"/>'))


def _text_param(name):
    return TextToolParameter(None, XML(f'<param name="{name}" type="text"/>'))


def test_collect_directory_uris_selects_only_directory_uri_params():
    inputs = {"dest": _directory_uri_param("dest"), "other": _text_param("other")}
    values = {"dest": "gxfiles://target/out", "other": "gxfiles://not-a-destination/x"}
    assert collect_directory_uris(inputs, values) == {"gxfiles://target/out"}


def test_collect_directory_uris_empty_when_no_directory_uri_params():
    inputs = {"other": _text_param("other")}
    assert collect_directory_uris(inputs, {"other": "text"}) == set()


def test_collect_directory_uris_skips_empty_values():
    inputs = {"dest": _directory_uri_param("dest")}
    assert collect_directory_uris(inputs, {"dest": ""}) == set()
