from types import SimpleNamespace

from galaxy.tool_shed.util.shed_util_common import set_image_paths


def test_set_image_paths_encodes_special_characters_in_tool_id():
    tool_shed_repository = SimpleNamespace(
        tool_shed="toolshed.g2.bx.psu.edu",
        owner="devteam",
        name="emboss_5",
    )
    text = ".. image:: static/images/isochore.png"
    result = set_image_paths(
        app=None,
        text=text,
        tool_shed_repository=tool_shed_repository,
        tool_id="EMBOSS: isochore47",
        tool_version="5.0.0.1",
    )
    assert "EMBOSS%3A%20isochore47" in result
    assert "EMBOSS: isochore47" not in result


def test_set_image_paths_preserves_slashes_in_route():
    tool_shed_repository = SimpleNamespace(
        tool_shed="toolshed.g2.bx.psu.edu",
        owner="devteam",
        name="emboss_5",
    )
    text = ".. image:: isochore.png"
    result = set_image_paths(
        app=None,
        text=text,
        tool_shed_repository=tool_shed_repository,
        tool_id="isochore",
        tool_version="5.0.0",
    )
    assert "shed_tool_static/toolshed.g2.bx.psu.edu/devteam/emboss_5/isochore/5.0.0/" in result


def test_set_image_paths_does_not_modify_http_urls():
    tool_shed_repository = SimpleNamespace(
        tool_shed="toolshed.g2.bx.psu.edu",
        owner="devteam",
        name="emboss_5",
    )
    text = ".. image:: https://example.com/image.png"
    result = set_image_paths(
        app=None,
        text=text,
        tool_shed_repository=tool_shed_repository,
        tool_id="mytool",
        tool_version="1.0",
    )
    assert ".. image:: https://example.com/image.png" in result
    assert "shed_tool_static" not in result
