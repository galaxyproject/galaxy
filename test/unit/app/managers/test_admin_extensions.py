from pathlib import Path

import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.exceptions import ObjectNotFound
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


def test_load_extensions_skips_invalid_config(tmp_path: Path):
    write_extension(tmp_path, "bad_yaml", "id: [unterminated")
    write_extension(tmp_path, "no_items", "id: x\nsection: X\nitems: []\n")
    write_extension(tmp_path, "bad_id", VALID_CONFIG.replace("id: anvil", "id: 'has space'"))
    write_extension(tmp_path, "bad_type", VALID_CONFIG.replace("type: link", "type: form"))
    write_extension(tmp_path, "good", VALID_CONFIG)

    assert [e.id for e in load_extensions(str(tmp_path))] == ["anvil"]


def test_load_extensions_skips_duplicate_ids(tmp_path: Path):
    write_extension(tmp_path, "first", VALID_CONFIG)
    write_extension(tmp_path, "second", VALID_CONFIG.replace("section: AnVIL", "section: Copy"))

    extensions = load_extensions(str(tmp_path))

    assert len(extensions) == 1
    assert extensions[0].section == "AnVIL"


@pytest.fixture
def manager(tmp_path: Path) -> AdminExtensionsManager:
    write_extension(tmp_path, "anvil", VALID_CONFIG)
    config = GalaxyAppConfiguration(admin_extensions_dir=str(tmp_path), override_tempdir=False)
    return AdminExtensionsManager(config)


def test_manager_lists_extensions(manager: AdminExtensionsManager):
    assert [e.id for e in manager.extensions] == ["anvil"]


def test_manager_get_extension(manager: AdminExtensionsManager):
    assert manager.get_extension("anvil").section == "AnVIL"
    with pytest.raises(ObjectNotFound):
        manager.get_extension("missing")


def test_manager_get_item(manager: AdminExtensionsManager):
    item = manager.get_item("anvil", "monitor")
    assert item.url == "/monitor"
    with pytest.raises(ObjectNotFound):
        manager.get_item("anvil", "missing")
    with pytest.raises(ObjectNotFound):
        manager.get_item("missing", "monitor")


FORM_CONFIG = """
id: forms
section: Forms
items:
  - id: settings
    type: form
    title: Settings
    inputs:
      - name: ttl
        key: shared.ttl
        type: integer
        label: TTL
        default: 5
"""


def test_load_extensions_reads_form_items(tmp_path: Path):
    write_extension(tmp_path, "forms", FORM_CONFIG)
    extension = load_extensions(str(tmp_path))[0]
    item = extension.items[0]
    assert item.type == "form"
    assert item.inputs[0].key == "shared.ttl"


def test_load_extensions_builds_default_keys_from_ids(tmp_path: Path):
    write_extension(
        tmp_path, "forms", FORM_CONFIG.replace("        key: shared.ttl\n", "").replace("id: forms", "id: my-ext")
    )
    extension = load_extensions(str(tmp_path))[0]
    assert extension.items[0].inputs[0].key == "my_ext.settings.ttl"


def test_load_extensions_skips_extension_redeclaring_key_with_other_type(tmp_path: Path):
    write_extension(tmp_path, "a_first", FORM_CONFIG.replace("id: forms", "id: a"))
    write_extension(
        tmp_path,
        "b_conflict",
        FORM_CONFIG.replace("id: forms", "id: b")
        .replace("type: integer", "type: text")
        .replace("default: 5", "default: five"),
    )
    write_extension(tmp_path, "c_same", FORM_CONFIG.replace("id: forms", "id: c"))

    assert [e.id for e in load_extensions(str(tmp_path))] == ["a", "c"]


def test_load_extensions_rejects_invalid_form_items(tmp_path: Path):
    write_extension(
        tmp_path,
        "dup_inputs",
        FORM_CONFIG.replace("id: forms", "id: d") + "      - name: ttl\n        type: text\n        label: Again\n",
    )
    write_extension(
        tmp_path, "bad_default", FORM_CONFIG.replace("id: forms", "id: e").replace("default: 5", "default: five")
    )
    write_extension(tmp_path, "dup_items", VALID_CONFIG.replace("id: docs", "id: monitor"))
    assert load_extensions(str(tmp_path)) == []
