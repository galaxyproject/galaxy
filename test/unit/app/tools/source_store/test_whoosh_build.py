"""Pin ``ToolWhooshIndex.build`` rebuild/skip semantics."""

from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.search import (
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


def test_changed_corpus_rebuilds_and_drops_stale_docs(tmp_path):
    index_dir = str(tmp_path / "ix")
    ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "caller"))

    written = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING).build(_index("mapper", "trimmer"))
    assert written == 2
    searcher = ToolWhooshIndex(index_dir=index_dir, tuning=_TUNING)
    assert searcher.search("trimmer") == ["trimmer"]
    # "caller" left the corpus; the CLEAR rebuild must not serve it anymore.
    assert searcher.search("caller") == []


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
