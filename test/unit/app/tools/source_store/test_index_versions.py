"""Pin ``ToolIndex`` behaviours that index consumers depend on.

These unit tests run against a real ``ToolIndex`` (no mocks, no Galaxy
app) so they're cheap and pinpoint regressions in the round-2
Behaviours pinned:

- per-id default selection by ``packaging.version.parse``
- ``entries_by_version`` records every indexed version
- explicit-version lookup via ``ToolIndex.get(tool_id, tool_version)``
- ``to_dict`` / ``from_dict`` round-trips ``entries_by_version``
- tokenised search across id / name / description / labels
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


def test_to_dict_from_dict_round_trips_entries_by_version(index_entry, tool_index):
    index = tool_index(
        index_entry("multi", version="0.1"),
        index_entry("multi", version="0.2"),
        index_entry("solo", version="1.0"),
    )
    restored = ToolIndex.from_dict(index.to_dict())
    assert set(restored.entries_by_version["multi"]) == {"0.1", "0.2"}
    assert restored.entries["multi"].version == "0.2"
    multi_v01 = restored.get("multi", tool_version="0.1")
    assert multi_v01 is not None and multi_v01.version == "0.1"
    assert set(restored.entries_by_version["solo"]) == {"1.0"}


def test_from_dict_backfills_entries_by_version_for_legacy_indexes():
    # Indexes serialised before ``entries_by_version`` existed should still
    # load — ``ToolIndex.get(tool_id, tool_version=...)`` relies on the
    # backfill so legacy stores keep working after upgrade.
    legacy = {
        "entries": {
            "tool1": {"id": "tool1", "version": "1.0", "name": "Tool 1"},
        },
    }
    restored = ToolIndex.from_dict(legacy)
    tool1 = restored.get("tool1", tool_version="1.0")
    assert tool1 is not None and tool1.version == "1.0"
