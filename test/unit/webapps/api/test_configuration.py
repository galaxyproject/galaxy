from galaxy.webapps.galaxy.api.common import parse_serialization_params


def test_parse_serialization_params():
    view, default_view = "a", "b"
    keys = "foo"
    serialized = parse_serialization_params(view, keys, default_view)
    assert serialized.view == view
    assert serialized.default_view == default_view
    assert serialized.keys == [keys]

    keys = "foo,bar,baz"
    serialized = parse_serialization_params(view, keys, default_view)
    assert serialized.keys == ["foo", "bar", "baz"]

    serialized = parse_serialization_params(default_view=default_view)
    assert serialized.view is None
    assert serialized.keys is None
    assert serialized.default_view == default_view
