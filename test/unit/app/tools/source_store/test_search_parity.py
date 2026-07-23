from types import SimpleNamespace
from typing import cast

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.search import ToolPanelViewSearch
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import (
    entry_to_search_document,
    MAX_TOOL_SEARCH_HELP_CHARS,
    ToolSearchTuning,
    ToolWhooshIndex,
)

_TUNING = ToolSearchTuning(
    id_boost=20.0,
    name_boost=10.0,
    name_exact_multiplier=2.0,
    stub_boost=5.0,
    section_boost=4.0,
    description_boost=3.0,
    label_boost=3.0,
    ngram_minsize=3,
    ngram_maxsize=4,
    enable_ngram_search=True,
    ngram_factor=0.5,
    help_boost=1.0,
    help_bm25f_k1=1.2,
)


def _tool(entry: ToolIndexEntry):
    return SimpleNamespace(
        id=entry.id,
        guid=None,
        name=entry.name,
        description=entry.description,
        get_panel_section=lambda: (entry.panel_section_id, entry.panel_section_name),
        edam_operations=entry.edam_operations,
        edam_topics=entry.edam_topics,
        repository_name=entry.repository_name,
        repository_owner=entry.repository_owner,
        labels=entry.labels,
        tool_tags=[],
        raw_help=entry.help_text,
        tool_type=entry.tool_type,
    )


def test_eager_and_cached_documents_share_help_bound(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    config = cast(GalaxyAppConfiguration, SimpleNamespace())
    eager = ToolPanelViewSearch("default", str(tmp_path / "eager"), config)
    entry = ToolIndexEntry(
        id="mapper",
        version="1.0",
        name="Sequence mapper",
        description="Maps sequences",
        panel_section_id="mapping",
        panel_section_name="Mapping",
        labels=["featured"],
        edam_operations=["Mapping"],
        edam_topics=["Genomics"],
        help_text=("h" * MAX_TOOL_SEARCH_HELP_CHARS) + "not-indexed",
    )

    eager_document = eager._create_doc(_tool(entry))
    cached_document = entry_to_search_document(entry, include_help=True)

    assert eager_document == cached_document
    assert len(eager_document["help"]) == MAX_TOOL_SEARCH_HELP_CHARS


def test_eager_help_content_object_is_normalized(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    config = cast(GalaxyAppConfiguration, SimpleNamespace())
    eager = ToolPanelViewSearch("default", str(tmp_path / "eager"), config)
    entry = ToolIndexEntry(id="mapper", version="1.0", name="Sequence mapper")
    tool = _tool(entry)
    tool.raw_help = SimpleNamespace(content="quaxifier help")

    assert eager._create_doc(tool)["help"] == "quaxifier help"


def test_eager_and_cached_indexes_return_same_ordered_hits(tmp_path, monkeypatch):
    monkeypatch.setattr(ToolSearchTuning, "from_config", classmethod(lambda cls, config: _TUNING))
    config = cast(GalaxyAppConfiguration, SimpleNamespace())
    entries = [
        ToolIndexEntry(
            id="mapper_a",
            version="1.0",
            name="Sequence mapper",
            description="Maps genomic reads",
            panel_section_name="Mapping",
            labels=["featured"],
            help_text="aligns reads with quaxifier",
        ),
        ToolIndexEntry(
            id="mapper_b",
            version="1.0",
            name="Mapper deluxe",
            description="Maps sequences",
            panel_section_name="Mapping",
            labels=["standard"],
            help_text="alignment helper",
        ),
    ]
    tool_index = ToolIndex()
    for entry in entries:
        tool_index.add_entry(entry)

    eager = ToolPanelViewSearch("default", str(tmp_path / "eager"), config)
    with eager.index.writer() as writer:
        for entry in entries:
            writer.add_document(**eager._create_doc(_tool(entry)))

    cached = ToolWhooshIndex(str(tmp_path / "cached"), _TUNING)
    cached.build(tool_index, set(tool_index.entries))

    for query in ("mapper", "mapper_a", "genomic", "Mapping", "featured", "quaxifier"):
        assert eager.search(query, config) == cached.search(query)
