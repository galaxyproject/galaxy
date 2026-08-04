"""Pin ``ToolIndex`` behaviours that index consumers depend on.

These unit tests run against a real ``ToolIndex`` (no mocks, no Galaxy
app) so they're cheap and pinpoint regressions. Behaviours pinned:

- per-id default selection by ``packaging.version.parse``
- ``entries_by_version`` records every indexed version
- explicit-version lookup via ``ToolIndex.get(tool_id, tool_version)``
- pydantic serialization round-trips ``entries_by_version``
"""

from galaxy.tools.source_store.index import ToolIndex


def test_add_entry_default_picks_highest_packaging_version(index_entry, tool_index):
    # ``"0.1+galaxy6"`` lex-compares between ``"0.1"`` and ``"0.2"``, so a
    # plain string sort would still pick ``"0.2"`` here — but it would pick
    # ``"0.1+galaxy6"`` for ``["0.1+galaxy6", "0.10"]``. Cover the
    # packaging-aware path explicitly.
    index = tool_index(
        index_entry("multi", version="0.1+galaxy6"),
        index_entry("multi", version="0.1"),
        index_entry("multi", version="0.2"),
    )
    assert index.entries["multi"].version == "0.2"


def test_add_entry_default_handles_post_release_above_two_digits(index_entry, tool_index):
    index = tool_index(
        index_entry("multi", version="0.10"),
        index_entry("multi", version="0.2"),
    )
    assert index.entries["multi"].version == "0.10"


def test_add_entry_records_every_version_under_entries_by_version(index_entry, tool_index):
    index = tool_index(
        index_entry("multi", version="0.1"),
        index_entry("multi", version="0.2"),
        index_entry("multi", version="0.3"),
    )
    assert set(index.entries_by_version["multi"]) == {"0.1", "0.2", "0.3"}


def test_get_with_explicit_version_returns_that_entry(index_entry, tool_index):
    e1 = index_entry("multi", version="0.1", name="V01")
    e2 = index_entry("multi", version="0.2", name="V02")
    index = tool_index(e1, e2)
    assert index.get("multi", tool_version="0.1") is e1
    assert index.get("multi", tool_version="0.2") is e2


def test_get_with_unknown_version_returns_none(index_entry, tool_index):
    # Consumers use the ``None`` return to fall back to the
    # default-version entry; pin the contract so a future refactor doesn't
    # silently start returning the default here.
    index = tool_index(index_entry("multi", version="0.1"))
    assert index.get("multi", tool_version="9.9") is None


def test_get_with_no_version_returns_default_entry(index_entry, tool_index):
    e1 = index_entry("multi", version="0.1")
    e2 = index_entry("multi", version="0.2")
    index = tool_index(e1, e2)
    assert index.get("multi") is e2


def test_serialization_round_trips_entries_by_version(index_entry, tool_index):
    index = tool_index(
        index_entry("multi", version="0.1"),
        index_entry("multi", version="0.2"),
        index_entry("solo", version="1.0"),
    )
    restored = ToolIndex.model_validate(index.model_dump(mode="json"))
    assert set(restored.entries_by_version["multi"]) == {"0.1", "0.2"}
    assert restored.entries["multi"].version == "0.2"
    multi_v01 = restored.get("multi", tool_version="0.1")
    assert multi_v01 is not None and multi_v01.version == "0.1"
    assert set(restored.entries_by_version["solo"]) == {"1.0"}


def test_add_entry_maintains_section_projection(index_entry, tool_index):
    index = tool_index(
        index_entry("one", panel_section_id="sec", panel_section_name="Section"),
        index_entry("two", panel_section_id="sec", panel_section_name="Section"),
    )
    assert index.by_section == {"sec": ["one", "two"]}


def test_remove_entry_clears_all_projections(index_entry, tool_index):
    index = tool_index(
        index_entry("remove", version="1.0", panel_section_id="one"),
        index_entry("remove", version="2.0", panel_section_id="two"),
        index_entry("keep", version="1.0", panel_section_id="one"),
    )

    assert index.remove_entry("remove") is True
    assert "remove" not in index.entries
    assert "remove" not in index.entries_by_version
    assert index.by_section == {"one": ["keep"]}
    assert all(item.tool_id != "remove" for item in index.panel_items)


def test_add_entry_invalidates_derived_metadata(index_entry, tool_index):
    index = tool_index(index_entry("one", requirements=[{"name": "one", "type": "package"}], test_count=1))
    assert [requirement["name"] for requirement in index.get_all_requirements()] == ["one"]
    assert set(index.get_tests_summary()) == {"one"}

    index.add_entry(index_entry("two", requirements=[{"name": "two", "type": "package"}], test_count=1))

    assert [requirement["name"] for requirement in index.get_all_requirements()] == ["one", "two"]
    assert set(index.get_tests_summary()) == {"one", "two"}


def test_tests_summary_excludes_datatype_converters(index_entry, tool_index):
    index = tool_index(
        index_entry("real_tool", version="1.0", test_count=2),
        index_entry("convert_fasta", version="1.0", test_count=1, is_datatype_converter=True),
    )
    assert set(index.get_tests_summary()) == {"real_tool"}
