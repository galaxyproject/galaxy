import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
)

galaxy_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tool_source_store.discover import DiscoveredTool
from galaxy.tool_source_store.populator import build_index_entry_from_source


@dataclass
class _StoredStub:
    hash: str = "abc123"
    tool_source_class: str = "XmlToolSource"
    tool_id: str = "bowtie2"


class _ToolSourceStub:
    def __init__(
        self,
        tool_id: str = "bowtie2",
        version: str = "2.5.0",
        name: str = "Bowtie2",
        description: str = "Fast aligner",
        hidden: bool = False,
        require_login: bool = False,
        tool_type: str = "default",
        edam_operations: list[str] | None = None,
        edam_topics: list[str] | None = None,
    ):
        self._id = tool_id
        self._version = version
        self._name = name
        self._description = description
        self._hidden = hidden
        self._require_login = require_login
        self._tool_type = tool_type
        self._edam_operations = edam_operations or []
        self._edam_topics = edam_topics or []

    def parse_id(self) -> str:
        return self._id

    def parse_version(self) -> str:
        return self._version

    def parse_name(self) -> str:
        return self._name

    def parse_description(self) -> str:
        return self._description

    def parse_hidden(self) -> bool:
        return self._hidden

    def parse_require_login(self, default: bool) -> bool:
        return self._require_login

    def parse_tool_type(self) -> str:
        return self._tool_type

    def parse_edam_operations(self) -> list[str]:
        return self._edam_operations

    def parse_edam_topics(self) -> list[str]:
        return self._edam_topics


def _discovered(**overrides: Any) -> DiscoveredTool:
    base: dict[str, Any] = dict(path="/tools/bowtie2.xml", tool_conf="tool_conf.xml", tool_path="/tools")
    base.update(overrides)
    return DiscoveredTool(**base)


def test_basic_fields_threaded_through():
    entry = build_index_entry_from_source(_discovered(), _StoredStub(), _ToolSourceStub())
    assert entry is not None
    assert entry.id == "bowtie2"
    assert entry.version == "2.5.0"
    assert entry.name == "Bowtie2"
    assert entry.description == "Fast aligner"
    assert entry.source_hash == "abc123"
    assert entry.source_class == "XmlToolSource"
    assert entry.tool_type == "default"


def test_section_metadata_from_discovered():
    entry = build_index_entry_from_source(
        _discovered(section_id="ngs", section_name="NGS Tools"),
        _StoredStub(),
        _ToolSourceStub(),
    )
    assert entry.panel_section_id == "ngs"
    assert entry.panel_section_name == "NGS Tools"


def test_labels_from_discovered():
    entry = build_index_entry_from_source(
        _discovered(labels=["beta", "experimental"]),
        _StoredStub(),
        _ToolSourceStub(),
    )
    assert entry.labels == ["beta", "experimental"]


def test_conf_level_hidden_forces_entry_hidden():
    # Body says not hidden; conf says hidden — entry honors the conf.
    entry = build_index_entry_from_source(
        _discovered(hidden=True),
        _StoredStub(),
        _ToolSourceStub(hidden=False),
    )
    assert entry.hidden is True


def test_body_hidden_alone_also_forces_hidden():
    entry = build_index_entry_from_source(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(hidden=True),
    )
    assert entry.hidden is True


def test_neither_hidden_means_false():
    entry = build_index_entry_from_source(_discovered(), _StoredStub(), _ToolSourceStub(hidden=False))
    assert entry.hidden is False


def test_edam_lists_threaded_through():
    entry = build_index_entry_from_source(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(edam_operations=["operation_0292"], edam_topics=["topic_0102"]),
    )
    assert entry.edam_operations == ["operation_0292"]
    assert entry.edam_topics == ["topic_0102"]


def test_require_login_threaded_through():
    entry = build_index_entry_from_source(_discovered(), _StoredStub(), _ToolSourceStub(require_login=True))
    assert entry.require_login is True


def test_tool_source_class_taken_from_stored():
    entry = build_index_entry_from_source(
        _discovered(),
        _StoredStub(tool_source_class="YamlToolSource"),
        _ToolSourceStub(),
    )
    assert entry.source_class == "YamlToolSource"


def test_no_id_yields_none():
    entry = build_index_entry_from_source(_discovered(), _StoredStub(tool_id=""), _ToolSourceStub(tool_id=""))
    assert entry is None


def test_fallback_id_from_stored_when_source_has_none():
    entry = build_index_entry_from_source(
        _discovered(),
        _StoredStub(tool_id="from_stored"),
        _ToolSourceStub(tool_id=""),
    )
    assert entry is not None
    assert entry.id == "from_stored"


def test_data_manager_tool_type_preserved():
    entry = build_index_entry_from_source(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(tool_type="data_manager"),
    )
    assert entry.tool_type == "data_manager"
