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
