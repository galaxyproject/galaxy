from pathlib import Path

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.managers.admin_extensions import (
    AdminExtensionsManager,
    load_extensions,
)

VALID_CONFIG = """
id: anvil
section: AnVIL
items:
  - id: monitor
    type: link
    title: Cluster Monitor
    url: /monitor
  - id: docs
    type: link
    title: AnVIL Docs
    url: https://anvilproject.org
    target: new_tab
"""


def write_extension(base: Path, dirname: str, content: str, filename: str = "config.yml") -> Path:
    extension_dir = base / dirname
    extension_dir.mkdir(parents=True)
    (extension_dir / filename).write_text(content)
    return extension_dir


def test_load_extensions_reads_valid_config(tmp_path: Path):
    write_extension(tmp_path, "anvil", VALID_CONFIG)

    extensions = load_extensions(str(tmp_path))

    assert len(extensions) == 1
    extension = extensions[0]
    assert extension.id == "anvil"
    assert extension.section == "AnVIL"
    assert [item.id for item in extension.items] == ["monitor", "docs"]
    assert extension.items[0].target == "iframe"
    assert extension.items[1].target == "new_tab"


def test_load_extensions_accepts_yaml_extension(tmp_path: Path):
    write_extension(tmp_path, "anvil", VALID_CONFIG, filename="config.yaml")

    assert [e.id for e in load_extensions(str(tmp_path))] == ["anvil"]


def test_load_extensions_searches_multiple_directories(tmp_path: Path):
    write_extension(tmp_path / "one", "a", VALID_CONFIG.replace("id: anvil", "id: a"))
    write_extension(tmp_path / "two", "b", VALID_CONFIG.replace("id: anvil", "id: b"))

    extensions = load_extensions(f"{tmp_path / 'one'},{tmp_path / 'two'}")

    assert [e.id for e in extensions] == ["a", "b"]


def test_load_extensions_empty_when_unset_or_missing(tmp_path: Path):
    assert load_extensions(None) == []
    assert load_extensions("") == []
    assert load_extensions(str(tmp_path / "does_not_exist")) == []


def test_load_extensions_skips_directory_without_config(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    write_extension(tmp_path, "anvil", VALID_CONFIG)

    assert [e.id for e in load_extensions(str(tmp_path))] == ["anvil"]


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("id: [unterminated", id="bad_yaml"),
        pytest.param("id: x\nsection: X\nitems: []\n", id="no_items"),
        pytest.param(VALID_CONFIG.replace("id: anvil", "id: 'has space'"), id="bad_id"),
        pytest.param(VALID_CONFIG.replace("type: link", "type: form"), id="bad_type"),
        pytest.param(VALID_CONFIG.replace("id: docs", "id: monitor"), id="dup_item"),
        pytest.param(VALID_CONFIG.replace("target: new_tab", "traget: new_tab"), id="unknown_key"),
        pytest.param(VALID_CONFIG.replace("url: /monitor", "url: 'javascript:alert(1)'"), id="js_url"),
        pytest.param(VALID_CONFIG.replace("url: /monitor", "url: '//example.org/x'"), id="protocol_relative"),
        pytest.param(VALID_CONFIG.replace("url: /monitor", "url: monitor"), id="bare_path"),
    ],
)
def test_load_extensions_skips_invalid_config(tmp_path: Path, content: str):
    write_extension(tmp_path, "invalid", content)

    assert load_extensions(str(tmp_path)) == []


def test_load_extensions_skips_duplicate_ids(tmp_path: Path):
    write_extension(tmp_path, "first", VALID_CONFIG)
    write_extension(tmp_path, "second", VALID_CONFIG.replace("section: AnVIL", "section: Copy"))

    extensions = load_extensions(str(tmp_path))

    assert len(extensions) == 1
    assert extensions[0].section == "AnVIL"


def test_manager_lists_extensions(tmp_path: Path):
    write_extension(tmp_path, "anvil", VALID_CONFIG)
    config = GalaxyAppConfiguration(admin_extensions_dir=str(tmp_path), override_tempdir=False)

    assert [e.id for e in AdminExtensionsManager(config).extensions] == ["anvil"]
