from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy.tool_shed.util.shed_util_common import (
    make_image_paths_relative,
    set_image_paths,
)

if TYPE_CHECKING:
    from galaxy.structured_app import BasicSharedApp


def test_set_image_paths_does_not_modify_http_urls():
    text = ".. image:: https://example.com/image.png"
    result = set_image_paths(app=cast("BasicSharedApp", None), text=text, encoded_repository_id="abc")
    assert result == text


def test_set_image_paths_pins_tool_shed_images_to_changeset_revision():
    text = ".. image:: images/logo.png\n.. image:: images/badge.svg?raw=true\n"
    result = set_image_paths(
        app=cast("BasicSharedApp", None),
        text=text,
        encoded_repository_id="abc",
        changeset_revision="0123456789ab",
    )
    assert ".. image:: /repository/static/images/abc/images%2Flogo.png?changeset_revision=0123456789ab\n" in result
    assert (
        ".. image:: /repository/static/images/abc/images%2Fbadge.svg?raw=true&changeset_revision=0123456789ab\n"
        in result
    )


def test_make_image_paths_relative():
    text = "\n".join(
        [
            ".. image:: $PATH_TO_IMAGES/a.png",
            ".. image:: ${static_path}/images/b.png",
            ".. image:: /static/images/c.gif",
            ".. image:: /deep/d.png",
            ".. image:: e.png",
            ".. image:: https://example.com/f.png",
            ".. figure:: $PATH_TO_IMAGES/g.png",
        ]
    )
    assert make_image_paths_relative(text).splitlines() == [
        ".. image:: a.png",
        ".. image:: images/b.png",
        ".. image:: static/images/c.gif",
        ".. image:: deep/d.png",
        ".. image:: e.png",
        ".. image:: https://example.com/f.png",
        ".. figure:: g.png",
    ]
