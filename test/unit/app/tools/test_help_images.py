import os

import pytest

from galaxy.tools.help_images import (
    find_tool_asset,
    find_tool_file,
    help_image_media_type,
)


@pytest.fixture
def tool_dir(tmp_path):
    images = tmp_path / "static" / "images"
    images.mkdir(parents=True)
    (images / "in_static.png").write_bytes(b"static")
    (tmp_path / "beside_tool.png").write_bytes(b"beside")
    (tmp_path / "both.png").write_bytes(b"beside")
    (images / "both.png").write_bytes(b"static")
    (tmp_path / "tool.xml").write_text("<tool/>")
    (tmp_path.parent / "outside.png").write_bytes(b"outside")
    return str(tmp_path)


def test_bare_name_found_in_static_images(tool_dir):
    assert find_tool_asset(tool_dir, "in_static.png") == os.path.join(tool_dir, "static", "images", "in_static.png")


def test_path_relative_to_tool(tool_dir):
    assert find_tool_asset(tool_dir, "beside_tool.png") == os.path.join(tool_dir, "beside_tool.png")
    expected = os.path.join(tool_dir, "static", "images", "in_static.png")
    assert find_tool_asset(tool_dir, "static/images/in_static.png") == expected


def test_static_images_preferred(tool_dir):
    assert find_tool_asset(tool_dir, "both.png") == os.path.join(tool_dir, "static", "images", "both.png")


def test_missing_and_escaping_paths_not_found(tool_dir):
    assert find_tool_asset(tool_dir, "missing.png") is None
    assert find_tool_asset(tool_dir, "../outside.png") is None
    assert find_tool_asset(tool_dir, "../../outside.png") is None
    assert find_tool_asset(tool_dir, os.path.join(os.path.dirname(tool_dir), "outside.png")) is None
    assert find_tool_asset(tool_dir, "static") is None


def test_symlink_out_of_tool_dir_not_found(tool_dir):
    os.symlink(os.path.join(os.path.dirname(tool_dir), "outside.png"), os.path.join(tool_dir, "link.png"))
    assert find_tool_asset(tool_dir, "link.png") is None


def test_tool_dir_reached_through_symlink(tool_dir, tmp_path_factory):
    linked_dir = os.path.join(tmp_path_factory.mktemp("links"), "tool")
    os.symlink(tool_dir, linked_dir)
    found = find_tool_asset(linked_dir, "in_static.png")
    assert found == os.path.realpath(os.path.join(tool_dir, "static", "images", "in_static.png"))


def test_tool_file_exact_path_only(tool_dir, tmp_path_factory):
    assert find_tool_file(tool_dir, "both.png") == os.path.join(tool_dir, "both.png")
    assert find_tool_file(tool_dir, "missing.png") is None
    assert find_tool_file(tool_dir, "../outside.png") is None
    linked_dir = os.path.join(tmp_path_factory.mktemp("links"), "tool")
    os.symlink(tool_dir, linked_dir)
    assert find_tool_file(linked_dir, "both.png") == os.path.join(tool_dir, "both.png")


@pytest.mark.parametrize(
    "path,expected",
    [
        ("a.png", "image/png"),
        ("a.JPG", "image/jpeg"),
        ("a.gif", "image/gif"),
        ("a.svg", None),
        ("tool.xml", None),
        ("script.py", None),
        ("noextension", None),
    ],
)
def test_help_image_media_type(path, expected):
    assert help_image_media_type(path) == expected
