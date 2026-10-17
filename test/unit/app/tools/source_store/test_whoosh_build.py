"""Pin ``ToolWhooshIndex.build`` rebuild/skip semantics."""

from whoosh import index

from galaxy.tools import DataManagerTool
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import (
    build_search_schema,
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
)


def _index(*names: str) -> ToolIndex:
    idx = ToolIndex()
    for name in names:
        idx.add_entry(ToolIndexEntry(id=name, version="1.0", name=name.replace("_", " ").title()))
    return idx


def test_unchanged_corpus_skips_rebuild(tmp_path):
    index_dir = str(tmp_path / "ix")
    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller")) == 2

    # Same corpus again: nothing written, existing index still serves queries.
    written = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller"))
    assert written == 0
    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("mapper") == ["mapper"]


def test_changed_corpus_writes_only_new_docs_and_drops_stale_docs(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller"))

    written = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "trimmer"))
    assert written == 1
    searcher = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING)
    assert searcher.search("trimmer") == ["trimmer"]
    assert searcher.search("mapper") == ["mapper"]
    assert searcher.search("caller") == []


def test_changed_doc_is_rewritten(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_help_index("mytool", "Wraps the quaxifier."))

    written = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(
        _help_index("mytool", "Wraps the blorbinator.")
    )
    assert written == 1
    searcher = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING)
    assert searcher.search("blorbinator") == ["mytool"]
    assert searcher.search("quaxifier") == []


def test_doc_removed_by_another_writer_is_restored(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller"))
    with index.open_dir(index_dir).writer() as writer:
        writer.delete_by_term("id", "caller")

    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller")) == 1
    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("caller") == ["caller"]


def test_index_without_doc_hashes_is_upgraded_by_a_commit(tmp_path):
    index_dir = tmp_path / "ix"
    index_dir.mkdir()
    legacy = index.create_in(str(index_dir), schema=build_search_schema(_TUNING, help_boost=_TUNING.help_boost))
    with legacy.writer() as writer:
        writer.add_document(id="mapper", id_exact="mapper", name="Mapper", name_exact="Mapper")
    legacy_generation = index.open_dir(str(index_dir)).latest_generation()

    searcher = ToolWhooshIndex(index_dir=str(index_dir), tuning=_TUNING)
    assert searcher.build(_index("mapper")) == 1
    # One more commit on the existing index; recreating the directory would
    # restart its generations.
    assert index.open_dir(str(index_dir)).latest_generation() == legacy_generation + 1
    assert searcher.search("mapper") == ["mapper"]


def test_build_skips_when_another_writer_holds_the_lock(tmp_path, monkeypatch):
    monkeypatch.setattr("galaxy.tools.source_store.search.INDEX_WRITE_LOCK_TIMEOUT", 0.1)
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper"))

    other_writer = index.open_dir(index_dir).writer()
    try:
        assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("trimmer")) == 0
    finally:
        other_writer.cancel()

    searcher = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING)
    assert searcher.search("mapper") == ["mapper"]
    # The skipped build wrote nothing, so the next build still runs.
    assert searcher.build(_index("trimmer")) == 1


def test_build_scopes_corpus_to_panel_membership(tmp_path):
    searcher = ToolWhooshIndex(index_dir=str(tmp_path / "ix"), tuning=_TUNING)

    assert searcher.build(_index("mapper", "caller"), {"mapper"}) == 1
    assert searcher.search("mapper") == ["mapper"]
    assert searcher.search("caller") == []


def test_data_managers_are_excluded_from_search(tmp_path):
    tool_index = ToolIndex()
    tool_index.add_entry(
        ToolIndexEntry(id="data_manager", name="Data manager", version="1.0", tool_type=DataManagerTool.tool_type)
    )

    searcher = ToolWhooshIndex(index_dir=str(tmp_path / "ix"), tuning=_TUNING)
    assert searcher.build(tool_index) == 0
    assert searcher.search("manager") == []


def test_tuning_change_rebuilds_despite_same_docs(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper"))

    retuned = ToolSearchTuning(
        id_boost=99.0,
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
    )
    assert ToolWhooshIndex(index_dir=index_dir, tuning=retuned).build(_index("mapper")) == 1


def _help_index(entry_id, help_text):
    idx = ToolIndex()
    idx.add_entry(ToolIndexEntry(id=entry_id, version="1.0", name="Some Tool", help_text=help_text))
    return idx


def test_help_only_phrase_matches_when_help_indexed(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(
        _help_index("mytool", "This wraps the quaxifier subroutine.")
    )
    # "quaxifier" appears only in help, never in id/name — a hit proves help
    # made it into the corpus and is searchable.
    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("quaxifier") == ["mytool"]


def test_help_after_shared_limit_is_not_indexed(tmp_path):
    index_dir = str(tmp_path / "ix")
    bounded_prefix = "a" * MAX_TOOL_SEARCH_HELP_CHARS
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_help_index("mytool", f"{bounded_prefix} quaxifier"))

    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("quaxifier") == []


def test_plain_id_field_is_searchable(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("exact_tool_id"))

    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("exact_tool_id") == ["exact_tool_id"]


def test_help_omitted_when_index_tool_help_disabled(tmp_path):
    index_dir = str(tmp_path / "ix")
    help_off = ToolSearchTuning(
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
        index_tool_help=False,
    )
    ToolWhooshIndex(index_dir=index_dir, tuning=help_off).build(
        _help_index("mytool", "This wraps the quaxifier subroutine.")
    )
    assert ToolWhooshIndex(index_dir=index_dir, tuning=help_off).search("quaxifier") == []


def test_toggling_help_indexing_rebuilds_existing_index(tmp_path):
    index_dir = str(tmp_path / "ix")
    # Built once with help off; the same docs with help on must not skip the
    # rebuild — the schema gained a field and the corpus gained help tokens.
    help_off = ToolSearchTuning(
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
        index_tool_help=False,
    )
    ToolWhooshIndex(index_dir=index_dir, tuning=help_off).build(
        _help_index("mytool", "This wraps the quaxifier subroutine.")
    )
    written = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(
        _help_index("mytool", "This wraps the quaxifier subroutine.")
    )
    assert written == 1
    assert ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).search("quaxifier") == ["mytool"]
