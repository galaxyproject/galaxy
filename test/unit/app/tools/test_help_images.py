import os

import pytest

from galaxy.tools.help_images import (
    find_help_image,
    find_tool_asset,
    find_tool_file,
    help_image_media_type,
)


@pytest.fixture
def repo_dir(tmp_path):
    images = tmp_path / "repo" / "static" / "images"
    images.mkdir(parents=True)
    (images / "in_repo.png").write_bytes(b"repo")
    (images / "both.png").write_bytes(b"repo")
    (tmp_path / "outside.png").write_bytes(b"outside")
    return str(tmp_path / "repo")


@pytest.fixture
def tool_dir(repo_dir):
    tool = os.path.join(repo_dir, "tool")
    os.makedirs(os.path.join(tool, "static", "images"))
    for path in [os.path.join(tool, "static", "images", "both.png"), os.path.join(tool, "both.png")]:
        with open(path, "wb") as fh:
            fh.write(b"tool")
    return tool


@pytest.fixture
def outside_png(repo_dir):
    return os.path.join(os.path.dirname(repo_dir), "outside.png")


def test_static_images_preferred(tool_dir):
    assert find_tool_asset(tool_dir, "both.png") == os.path.join(tool_dir, "static", "images", "both.png")


def test_escaping_paths_and_directories_not_found(tool_dir, outside_png):
    assert find_tool_asset(tool_dir, outside_png) is None
    assert find_tool_asset(tool_dir, "static") is None


def test_symlink_out_of_tool_dir_not_found(tool_dir, outside_png):
    os.symlink(outside_png, os.path.join(tool_dir, "link.png"))
    assert find_tool_asset(tool_dir, "link.png") is None


def test_tool_dir_reached_through_symlink(tool_dir, tmp_path_factory):
    linked_dir = os.path.join(tmp_path_factory.mktemp("links"), "tool")
    os.symlink(tool_dir, linked_dir)
    found = find_tool_asset(linked_dir, "both.png")
    assert found == os.path.realpath(os.path.join(tool_dir, "static", "images", "both.png"))


def test_tool_file_exact_path_only(tool_dir):
    assert find_tool_file(tool_dir, "both.png") == os.path.join(tool_dir, "both.png")
    assert find_tool_file(tool_dir, "missing.png") is None


def test_help_image_falls_back_to_repository_root(tool_dir, repo_dir):
    expected = os.path.join(repo_dir, "static", "images", "in_repo.png")
    assert find_help_image((tool_dir, repo_dir), "in_repo.png") == expected
    assert find_help_image((tool_dir, None), "in_repo.png") is None


def test_help_image_prefers_tool_dir(tool_dir, repo_dir):
    expected = os.path.join(tool_dir, "static", "images", "both.png")
    assert find_help_image((tool_dir, repo_dir), "both.png") == expected


@pytest.mark.parametrize(
    "path,expected",
    [
        ("a.JPG", "image/jpeg"),
        ("noextension", None),
    ],
)
def test_help_image_media_type(path, expected):
    assert help_image_media_type(path) == expected
