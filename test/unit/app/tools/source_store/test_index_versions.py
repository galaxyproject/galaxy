"""Pin ``ToolIndex`` behaviours that index consumers depend on.

These unit tests run against a real ``ToolIndex`` (no mocks, no Galaxy
app) so they're cheap and pinpoint regressions. Behaviours pinned:

- per-id default selection by ``packaging.version.parse``
- ``entries_by_version`` records every indexed version
- explicit-version lookup via ``ToolIndex.get(tool_id, tool_version)``
- pydantic serialization round-trips ``entries_by_version``
"""

from galaxy.tools.source_store.index import (
    INDEX_SCHEMA_HASH,
    ToolIndex,
)


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


def test_validation_shares_default_entries_with_version_map(index_entry, tool_index):
    index = tool_index(
        index_entry("multi", version="0.1"),
        index_entry("multi", version="0.2"),
        index_entry("solo", version="1.0"),
    )
    dumped = index.model_dump(mode="json")
    # The stored format keeps every version, defaults included.
    assert {tool_id: set(versions) for tool_id, versions in dumped["entries_by_version"].items()} == {
        "multi": {"0.1", "0.2"},
        "solo": {"1.0"},
    }

    loaded = ToolIndex.model_validate(dumped)

    assert loaded.entries_by_version["multi"]["0.2"] is loaded.entries["multi"]
    assert loaded.entries_by_version["solo"]["1.0"] is loaded.entries["solo"]
    assert loaded.entries_by_version["multi"]["0.1"].version == "0.1"


def test_iter_entries_yields_each_entry_once(index_entry, tool_index):
    index = tool_index(index_entry("multi", version="0.1"), index_entry("multi", version="0.2"))
    legacy = ToolIndex(entries={"old": index_entry("old", version="1.0")})

    assert sorted(entry.version for entry in index.iter_entries()) == ["0.1", "0.2"]
    assert [entry.id for entry in legacy.iter_entries()] == ["old"]


def test_index_schema_hash_is_pinned():
    # Published tool source store bundles are matched on this hash; a change
    # discards every deployed index until the bundles are republished.
    assert INDEX_SCHEMA_HASH == "c90ca5455dfe48a0179a2e1ea5ae7fe8"


def test_configured_entry_stays_default_over_newer_storage_only_version(index_entry, tool_index):
    # An unconfigured bundled file (indexed storage-only) must not replace
    # the version the tool conf names, whichever order discovery yields.
    configured = index_entry("jupyter", version="0.3")
    bundled = index_entry("jupyter", version="1.0.3", in_panel=False)
    assert tool_index(configured, bundled).entries["jupyter"] is configured
    assert tool_index(bundled, configured).entries["jupyter"] is configured


def test_load_repairs_storage_only_default_shadowing_configured_version(index_entry):
    configured = index_entry("jupyter", version="0.3")
    bundled = index_entry("jupyter", version="1.0.3", in_panel=False)
    persisted = {
        "entries": {"jupyter": bundled.model_dump(mode="json")},
        "entries_by_version": {
            "jupyter": {"0.3": configured.model_dump(mode="json"), "1.0.3": bundled.model_dump(mode="json")}
        },
    }
    restored = ToolIndex.model_validate(persisted)
    assert restored.entries["jupyter"].version == "0.3"


def test_configured_versions_hide_storage_only_siblings(index_entry, tool_index):
    index = tool_index(
        index_entry("jupyter", version="0.3"),
        index_entry("jupyter", version="1.0.3", in_panel=False),
        index_entry("converter", version="1.0", in_panel=False),
        index_entry("converter", version="1.1", in_panel=False),
    )
    assert set(index.configured_versions("jupyter")) == {"0.3"}
    assert set(index.configured_versions("converter")) == {"1.0", "1.1"}
    # Storage-only versions stay addressable by explicit version.
    assert index.get("jupyter", "1.0.3") is not None


def test_remove_version_reselects_default(index_entry, tool_index):
    index = tool_index(index_entry("multi", version="0.1"), index_entry("multi", version="0.2"))
    assert index.remove_version("multi", "0.2")
    assert index.entries["multi"].version == "0.1"
    assert set(index.entries_by_version["multi"]) == {"0.1"}
    assert index.remove_version("multi", "0.1")
    assert "multi" not in index.entries
    assert "multi" not in index.entries_by_version


def test_storage_only_twin_does_not_displace_configured_version_slot(index_entry, tool_index):
    # Same id and version at two paths: a configured copy and a bundled one.
    configured = index_entry("x", version="1.0", source_path="/local/x.xml")
    bundled = index_entry("x", version="1.0", source_path="/bundled/x.xml", in_panel=False)
    index = tool_index(configured, bundled)
    assert index.entries["x"] is configured
    assert index.get("x", "1.0") is configured


def test_superseding_entry_replaces_configured_version_slot(index_entry, tool_index):
    # A rescan of the same id and version at a new path replaces the slot.
    configured = index_entry("x", version="1.0", source_path="/old/x.xml")
    index = tool_index(configured, index_entry("x", version="0.9"))
    rescanned = index_entry("x", version="1.0", source_path="/new/x.xml", in_panel=False)
    index.add_entry(rescanned, supersede=True)
    assert index.get("x", "1.0") is rescanned
    assert index.entries["x"].version == "0.9"


def test_remove_version_keeps_placement_order_for_readded_id(index_entry, tool_index):
    index = tool_index(*(index_entry(f"t{i}", version="1.0", panel_section_id="s") for i in (1, 2, 3)))
    index.remove_version("t1", "1.0", keep_placements=True)
    index.add_entry(index_entry("t1", version="1.1", panel_section_id="s"), new_placements_first=True)
    assert [item.tool_id for item in index.panel_items] == ["t1", "t2", "t3"]
    assert index.entries["t1"].version == "1.1"


def test_remove_last_configured_version_drops_placement(index_entry, tool_index):
    index = tool_index(index_entry("j", version="0.3"), index_entry("j", version="1.0.3", in_panel=False))
    index.remove_version("j", "0.3")
    assert index.entries["j"].version == "1.0.3"
    assert [item.tool_id for item in index.panel_items] == []


def test_load_keeps_default_of_ids_without_configured_version(index_entry):
    newest = index_entry("conv", version="2.0", in_panel=False)
    chosen = index_entry("conv", version="1.0", in_panel=False)
    persisted = {
        "entries": {"conv": chosen.model_dump(mode="json")},
        "entries_by_version": {"conv": {"1.0": chosen.model_dump(mode="json"), "2.0": newest.model_dump(mode="json")}},
    }
    assert ToolIndex.model_validate(persisted).entries["conv"].version == "1.0"
