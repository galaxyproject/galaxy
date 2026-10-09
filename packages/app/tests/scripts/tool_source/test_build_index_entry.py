import sys
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    cast,
)

galaxy_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tool_util.deps.requirements import (
    ContainerDescription,
    ToolRequirement,
    ToolRequirements,
)
from galaxy.tool_util.parser.interface import ToolSource
from galaxy.tools.source_store.discover import DiscoveredTool
from galaxy.tools.source_store.index import ToolIndexEntry
from galaxy.tools.source_store.interface import StoredToolSource
from galaxy.tools.source_store.populator import build_index_entry_from_source


@dataclass
class _StoredStub:
    hash: str = "abc123"
    tool_source_class: str = "XmlToolSource"
    tool_id: str = "bowtie2"
    source_path: str | None = "/tools/bowtie2.xml"
    metadata: dict | None = None


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
        requirements: list[ToolRequirement | dict[str, Any]] | None = None,
        containers: list[ContainerDescription] | None = None,
        test_count: int = 0,
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
        self._requirements = ToolRequirements(requirements)
        self._containers = containers or []
        self._test_count = test_count

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

    def parse_xrefs(self) -> list[dict[str, str]]:
        return []

    def parse_icon(self) -> str | None:
        return None

    def parse_input_pages(self):
        return None

    def parse_profile(self) -> str:
        return "21.09"

    def parse_requirements(self):
        return self._requirements, self._containers, [], [], []

    def parse_action_module(self):
        return None

    def parse_tests_to_dict(self):
        return {"tests": [{} for _ in range(self._test_count)]}


def _discovered(**overrides: Any) -> DiscoveredTool:
    base: dict[str, Any] = dict(path="/tools/bowtie2.xml", tool_conf="tool_conf.xml", tool_path="/tools")
    base.update(overrides)
    return DiscoveredTool(**base)


def _entry(discovered: DiscoveredTool, stored: Any, source: Any) -> ToolIndexEntry:
    """Build an entry from stubs, casting them to the real interfaces and
    asserting the common non-None result."""
    entry = build_index_entry_from_source(discovered, cast(StoredToolSource, stored), cast(ToolSource, source))
    assert entry is not None
    return entry


def _entry_optional(discovered: DiscoveredTool, stored: Any, source: Any) -> ToolIndexEntry | None:
    return build_index_entry_from_source(discovered, cast(StoredToolSource, stored), cast(ToolSource, source))


def test_basic_fields_threaded_through():
    entry = _entry(_discovered(), _StoredStub(), _ToolSourceStub())
    assert entry is not None
    assert entry.id == "bowtie2"
    assert entry.version == "2.5.0"
    assert entry.name == "Bowtie2"
    assert entry.description == "Fast aligner"
    assert entry.source_hash == "abc123"
    assert entry.source_class == "XmlToolSource"
    assert entry.tool_type == "default"


def test_shed_conf_guid_keys_entry_and_stamps_repository():
    guid = "toolshed.g2.bx.psu.edu/repos/iuc/bowtie2/bowtie2/2.5.0"
    entry = _entry(
        _discovered(
            guid=guid,
            is_shed_tool=True,
            tool_shed="toolshed.g2.bx.psu.edu",
            repository_name="bowtie2",
            repository_owner="iuc",
            installed_changeset_revision="abc123def",
        ),
        _StoredStub(),
        _ToolSourceStub(),
    )
    assert entry.id == guid
    assert entry.tool_shed == "toolshed.g2.bx.psu.edu"
    assert entry.repository_name == "bowtie2"
    assert entry.repository_owner == "iuc"
    assert entry.changeset_revision == "abc123def"
    assert entry.is_local is False


def test_section_metadata_from_discovered():
    entry = _entry(
        _discovered(section_id="ngs", section_name="NGS Tools"),
        _StoredStub(),
        _ToolSourceStub(),
    )
    assert entry.panel_section_id == "ngs"
    assert entry.panel_section_name == "NGS Tools"


def test_labels_from_discovered():
    entry = _entry(
        _discovered(labels=["beta", "experimental"]),
        _StoredStub(),
        _ToolSourceStub(),
    )
    assert entry.labels == ["beta", "experimental"]


def test_conf_level_hidden_forces_entry_hidden():
    # Body says not hidden; conf says hidden — entry honors the conf.
    entry = _entry(
        _discovered(hidden=True),
        _StoredStub(),
        _ToolSourceStub(hidden=False),
    )
    assert entry.hidden is True


def test_body_hidden_alone_also_forces_hidden():
    entry = _entry(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(hidden=True),
    )
    assert entry.hidden is True


def test_neither_hidden_means_false():
    entry = _entry(_discovered(), _StoredStub(), _ToolSourceStub(hidden=False))
    assert entry.hidden is False


def test_edam_lists_threaded_through():
    entry = _entry(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(edam_operations=["operation_0292"], edam_topics=["topic_0102"]),
    )
    assert entry.edam_operations == ["operation_0292"]
    assert entry.edam_topics == ["topic_0102"]


def test_require_login_threaded_through():
    entry = _entry(_discovered(), _StoredStub(), _ToolSourceStub(require_login=True))
    assert entry.require_login is True


def test_tests_requirements_and_containers_threaded_through():
    requirement = ToolRequirement(name="samtools", type="package", version="1.19")
    container = ContainerDescription(identifier="quay.io/biocontainers/samtools:1.19--h50ea8bc_0")
    entry = _entry(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(requirements=[requirement], containers=[container], test_count=2),
    )
    assert entry.test_count == 2
    assert entry.requirements == [requirement.to_dict()]
    assert entry.container_requirements == [container.to_dict()]


def test_tool_source_class_taken_from_stored():
    entry = _entry(
        _discovered(),
        _StoredStub(tool_source_class="YamlToolSource"),
        _ToolSourceStub(),
    )
    assert entry.source_class == "YamlToolSource"


def test_no_id_yields_none():
    entry = _entry_optional(_discovered(), _StoredStub(tool_id=""), _ToolSourceStub(tool_id=""))
    assert entry is None


def test_fallback_id_from_stored_when_source_has_none():
    entry = _entry(
        _discovered(),
        _StoredStub(tool_id="from_stored"),
        _ToolSourceStub(tool_id=""),
    )
    assert entry is not None
    assert entry.id == "from_stored"


def test_data_manager_tool_type_preserved():
    entry = _entry(
        _discovered(),
        _StoredStub(),
        _ToolSourceStub(tool_type="data_manager"),
    )
    assert entry.tool_type == "data_manager"


def test_model_operation_action_policy_is_indexed():
    entry = _entry(_discovered(), _StoredStub(), _ToolSourceStub(tool_type="unzip_collection"))
    assert entry.produces_real_jobs is False
