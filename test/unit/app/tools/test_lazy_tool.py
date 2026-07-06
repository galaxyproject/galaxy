import logging
from datetime import (
    datetime,
    timezone,
)
from typing import Any
from unittest.mock import MagicMock

import pytest

from galaxy.tools.lazy_toolbox import (
    LazyTool,
    LazyToolBox,
)
from galaxy.tools.source_store import StoredToolSource
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)


def _entry(**overrides):
    base: dict[str, Any] = dict(
        id="bowtie2",
        version="2.5.0",
        name="Bowtie2",
        description="Fast aligner",
        hidden=False,
        require_login=False,
        tool_type="default",
        tags=[],
        labels=["align"],
        edam_operations=["operation_0292"],
        edam_topics=["topic_0102"],
        source_hash="abc",
    )
    base.update(overrides)
    return ToolIndexEntry(**base)


def _stub(entry=None, materialize=None, is_admin=None):
    if materialize is None:

        def materialize(_e):  # noqa: E306
            raise AssertionError(f"unexpected materialise for {_e.id!r}")

    return LazyTool(
        entry or _entry(),
        materialize_callback=materialize,
        is_admin_user=is_admin or (lambda u: False),
    )


def test_forwarded_reads_off_entry():
    e = _entry()
    t = _stub(e)
    assert t.id == e.id
    assert t.version == e.version
    assert t.name == e.name
    assert t.description == e.description
    assert t.hidden is False
    assert t.require_login is False
    assert t.tool_type == "default"
    assert t.labels == ["align"]
    assert t.edam_operations == ["operation_0292"]
    assert t.edam_topics == ["topic_0102"]


def test_overrides_shadow_entry_and_survive_materialise():
    materialised = []

    class _Real:
        hidden = False
        labels = ()
        tool_shed = None

    def materialise(_e):
        materialised.append(_e.id)
        return _Real()

    t = LazyTool(_entry(), materialize_callback=materialise, is_admin_user=lambda u: False)
    t.hidden = True
    t.labels = ["a", "b"]
    t.tool_shed = "toolshed.example.com"
    assert t.hidden is True
    assert t.labels == ["a", "b"]

    real = t._materialize()
    assert materialised == [_entry().id]
    assert real.hidden is True
    assert real.labels == ["a", "b"]
    assert real.tool_shed == "toolshed.example.com"


def test_shed_metadata_derives_guid_and_installed_changeset_revision():
    e = _entry(
        id="toolshed.example.com/repos/owner/repo/tool/1.0",
        changeset_revision="abc123",
        tool_shed="toolshed.example.com",
        repository_name="repo",
        repository_owner="owner",
    )
    t = _stub(e)
    assert t.guid == "toolshed.example.com/repos/owner/repo/tool/1.0"
    assert t.installed_changeset_revision == "abc123"
    assert t.tool_shed == "toolshed.example.com"


def test_old_id_short_circuits_for_shed_ids():
    e = _entry(id="toolshed.example.com/repos/owner/repo/cat_tool/1.0")
    assert _stub(e).old_id == "cat_tool"
    assert _stub(_entry(id="local_tool")).old_id == "local_tool"


def test_to_panel_entry_does_not_materialise():
    def boom(_e):
        raise AssertionError(f"unexpected materialise for {_e.id!r}")

    t = LazyTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
    d = t.to_panel_entry(trans=None)
    assert d["id"] == "bowtie2"
    assert d["model_class"] == "Tool"
    assert d["link"] == "/tool_runner?tool_id=bowtie2"


def test_tool_tags_answered_without_materialise():
    def boom(_e):
        raise AssertionError(f"unexpected materialise for {_e.id!r}")

    t = LazyTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
    assert isinstance(t.tool_tags, list)
    t.tool_tags = ["curated"]
    assert t.tool_tags == ["curated"]


def test_to_panel_entry_carries_client_contract_fields():
    e = _entry(
        id="toolshed.example.com/repos/owner/repo/tool/1.0",
        tool_shed="toolshed.example.com",
        repository_name="repo",
        repository_owner="owner",
        changeset_revision="abc123",
        model_class="Tool",
        form_style="regular",
        is_workflow_compatible=True,
        xrefs=[{"value": "bwa", "reftype": "bio.tools"}],
    )
    t = _stub(e)
    d = t.to_panel_entry(trans=None)
    assert d["is_workflow_compatible"] is True
    assert d["form_style"] == "regular"
    assert d["xrefs"] == [{"value": "bwa", "reftype": "bio.tools"}]
    assert d["versions"] == ["2.5.0"]
    assert d["tool_shed_repository"]["changeset_revision"] == "abc123"
    assert "config_file" not in d


def test_get_panel_section_answered_off_entry_without_materialise():
    # AgentTools.get_tool_categories sweeps the whole toolbox and reads
    # get_panel_section()[1] per tool; forwarding off the entry keeps that
    # walk from parsing every tool. _stub's default materialize raises.
    e = _entry(panel_section_id="ngs", panel_section_name="NGS: Mapping")
    assert _stub(e).get_panel_section() == ("ngs", "NGS: Mapping")
    # No section stamped -> (None, None), matching Tool.get_panel_section.
    assert _stub(_entry()).get_panel_section() == (None, None)


def test_to_dict_materialises():
    calls: list[Any] = []

    class _Real:
        def to_dict(self, trans, link_details, tool_help, **kw):
            calls.append(("real-to_dict", kw.get("io_details")))
            return {"id": "real"}

    def mat(_e):
        calls.append("mat")
        return _Real()

    t = LazyTool(_entry(), materialize_callback=mat, is_admin_user=lambda u: False)
    assert t.to_dict(trans=None, io_details=True) == {"id": "real"}
    # Second call reuses cached ``_real``.
    assert t.to_dict(trans=None, io_details=True) == {"id": "real"}
    assert calls == ["mat", ("real-to_dict", True), ("real-to_dict", True)]


def test_to_dict_falls_back_to_entry_when_materialise_fails():
    # If a tool can't materialise (e.g. ``upload_dataset`` parameter factory
    # failure) the show endpoint still gets the entry-shape dict.
    def boom(_e):
        raise RuntimeError("materialise failed")

    t = LazyTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
    d = t.to_dict(trans=None, io_details=True)
    assert d["id"] == "bowtie2"
    assert d["model_class"] == "Tool"


def test_allow_user_access_uses_index_data_without_materialise():
    t = _stub(_entry(require_login=True))
    assert t.allow_user_access(user=None) is False

    class _U:
        id = 1

    assert t.allow_user_access(user=_U()) is True


def test_allow_user_access_blocks_non_admin_for_data_manager():
    e = _entry(tool_type="manage_data", require_login=False)
    t = _stub(e, is_admin=lambda u: False)

    class _U:
        id = 5

    assert t.allow_user_access(user=_U(), attempting_access=False) is False


def test_allow_user_access_allows_admin_for_data_manager():
    e = _entry(tool_type="manage_data", require_login=False)
    t = _stub(e, is_admin=lambda u: True)

    class _U:
        id = 5

    assert t.allow_user_access(user=_U()) is True


def test_strict_getattr_raises_with_clear_message(monkeypatch):
    # Strict mode is opt-in via LAZY_TOOL_STRICT=1; permissive (materialise
    # on unknown attr with WARN) is the default. Flip the module-level flag
    # for this test so the strict path fires.
    import galaxy.tools.lazy_toolbox as mod

    monkeypatch.setattr(mod, "_LAZY_TOOL_PERMISSIVE", False)
    t = _stub()
    with pytest.raises(NotImplementedError) as ei:
        _ = t.totally_not_a_tool_attr
    assert "totally_not_a_tool_attr" in str(ei.value)
    assert "bowtie2" in str(ei.value)


def test_underscore_attrs_surface_as_attribute_error():
    t = _stub()
    with pytest.raises(AttributeError):
        _ = t.__some_dunder_thing__


def test_materialize_ok_set_forwards_to_real_tool(caplog):
    class _Real:
        to_archive = "archive-payload"

    t = LazyTool(_entry(), materialize_callback=lambda _e: _Real(), is_admin_user=lambda u: False)
    assert t.to_archive == "archive-payload"


def test_permissive_flag_warns_and_materialises(monkeypatch, caplog):
    import galaxy.tools.lazy_toolbox as mod

    monkeypatch.setattr(mod, "_LAZY_TOOL_PERMISSIVE", True)

    class _Real:
        weird_attr = "warm"

    t = _stub(materialize=lambda _e: _Real())
    caplog.set_level(logging.WARNING, logger="galaxy.tools.lazy_toolbox")
    assert t.weird_attr == "warm"
    assert any("LAZY_TOOL_PERMISSIVE" in rec.getMessage() for rec in caplog.records)


def test_lineage_slot_settable_and_readable():
    t = _stub()
    assert t.lineage is None
    t._lineage = object()
    assert t.lineage is t._lineage


def test_macro_paths_returns_empty_class_default():
    t = _stub()
    assert tuple(t._macro_paths) == ()
    with pytest.raises(AttributeError):
        t._macro_paths = ["x"]


def test_config_file_reflects_entry_source_path():
    e = _entry()
    e.source_path = "/galaxy/tools/foo.xml"
    assert _stub(e).config_file == "/galaxy/tools/foo.xml"
    assert _stub(_entry()).config_file is None


# --- LazyToolBox.create_tool seam ---


def _seam_box():
    box = LazyToolBox.__new__(LazyToolBox)
    box._tool_index = ToolIndex()
    box._store = MagicMock()
    box._store.get_by_source_path.return_value = None
    box._shed_short_id_to_guids = {}
    box.app = MagicMock()
    box.app.config.is_admin_user = lambda u: False
    return box


def test_create_tool_returns_lazytool_on_guid_hit():
    box = _seam_box()
    box._tool_index.entries["bowtie2"] = _entry()
    tool = box.create_tool(config_file=None, guid="bowtie2")
    assert isinstance(tool, LazyTool)
    assert tool.id == "bowtie2"


def test_create_tool_returns_lazytool_on_source_path_hit():
    box = _seam_box()
    box._tool_index.entries["bowtie2"] = _entry()
    box._store.get_by_source_path.return_value = StoredToolSource(
        hash="abc",
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        tool_id="bowtie2",
        tool_dir=None,
        source_path="/tools/bowtie2.xml",
        stored_at=datetime.now(timezone.utc),
    )
    tool = box.create_tool(config_file="/tools/bowtie2.xml")
    assert isinstance(tool, LazyTool)
    assert tool.id == "bowtie2"


def test_resolve_index_entry_returns_none_when_nothing_matches():
    box = _seam_box()
    assert box._resolve_index_entry(None, None) is None


def test_create_tool_populates_adhoc_for_existing_file(tmp_path, monkeypatch):
    # Shed installs load cloned tools during metadata generation, before
    # any conf is persisted — a miss for an on-disk file populates that
    # path instead of raising.
    import galaxy.tools.lazy_toolbox as mod

    guid = "toolshed.example.com/repos/owner/repo/cloned/1.0"
    tool_file = tmp_path / "cloned.xml"
    tool_file.write_text("<tool id='cloned' version='1.0'/>")

    box = _seam_box()
    healed = ToolIndex()
    healed.add_entry(_entry(id=guid))
    box._store.load_index.return_value = healed

    calls = {}

    def fake_populate(config, paths, path_guids=None, **kwargs):
        calls["paths"] = paths
        calls["path_guids"] = path_guids

    monkeypatch.setattr(mod, "populate_for_paths", fake_populate)
    tool = box.create_tool(config_file=str(tool_file), guid=guid)
    assert isinstance(tool, LazyTool)
    assert tool.id == guid
    import os as _os

    expected_path = _os.path.abspath(str(tool_file))
    assert calls["paths"] == [expected_path]
    assert calls["path_guids"] == {expected_path: guid}
    box._store.invalidate_index_cache.assert_called()


def test_create_tool_stamps_data_manager_conf_id_on_entry():
    box = _seam_box()
    e = _entry(id="dm_tool", tool_type="manage_data")
    box._tool_index.entries["dm_tool"] = e
    # After a from_dict reload the per-version map holds a distinct object —
    # the one job-time versioned lookups resolve. It must get the stamp too.
    twin = _entry(id="dm_tool", tool_type="manage_data")
    box._tool_index.entries_by_version["dm_tool"] = {twin.version or "": twin}
    tool = box.create_tool(config_file=None, guid="dm_tool", data_manager_id="test_data_manager")
    assert isinstance(tool, LazyTool)
    assert e.data_manager_id == "test_data_manager"
    assert twin.data_manager_id == "test_data_manager"
    box._store.update_index_entry.assert_called_once_with(e)


def test_index_reload_refreshes_existing_stub_entries():
    box = _seam_box()
    stale = _entry(id="fastp_guid")
    stub = _stub(stale)
    box._tools_by_id = {"fastp_guid": stub}
    enriched = _entry(id="fastp_guid", tool_shed="toolshed.example.com", repository_name="fastp")
    box._tool_index.entries["fastp_guid"] = enriched
    box._register_new_index_entries_as_stubs()
    assert stub._entry is enriched
    assert stub.to_panel_entry()["tool_shed_repository"]["name"] == "fastp"


def test_create_tool_raises_on_index_miss():
    # The populator owns the index — including the Galaxy-internal lib
    # tools listed in ``galaxy.tools.special_tools.hidden_lib_tool_paths``.
    # A miss in ``create_tool`` is a contract failure (operator forgot
    # to repopulate, new ad-hoc tool load not added to the lib list);
    # raise loudly with a pointer to the fix.
    box = _seam_box()
    with pytest.raises(RuntimeError, match="no index entry"):
        box.create_tool(config_file="/tools/unknown.xml", guid=None)


def test_resolve_search_hit_returns_stub_without_materialise():
    box = _seam_box()
    # _stub's default materialize callback raises, so returning it proves
    # resolve_search_hit never parsed anything.
    stub = _stub(_entry(id="cat1"))
    box._tools_by_id = {"cat1": stub}
    assert box.resolve_search_hit("cat1") is stub


def test_resolve_search_hit_skips_indexed_but_unloaded_tool():
    # A whoosh hit that's in the index but was never loaded into this
    # toolbox (tool_conf.xml.sample's legacy tools) must resolve to None so
    # search skips it — the eager path skips these too — rather than
    # materialising it.
    box = _seam_box()
    box._tools_by_id = {}
    box._tool_index.entries["Cut1"] = _entry(id="Cut1")
    assert box.resolve_search_hit("Cut1") is None


def test_resolve_search_hit_follows_shed_short_id():
    box = _seam_box()
    guid = "toolshed.example.com/repos/owner/repo/cat/1.0"
    guid_stub = _stub(_entry(id=guid))
    box._tools_by_id = {guid: guid_stub}
    box._shed_short_id_to_guids = {"cat": {guid}}
    assert box.resolve_search_hit("cat") is guid_stub


def test_load_tool_from_cache_returns_none():
    box = _seam_box()
    assert box.load_tool_from_cache("any/path.xml") is None


def test_add_tool_to_cache_is_noop():
    box = _seam_box()
    assert box.add_tool_to_cache(object(), "any/path.xml") is None


# --- peer invalidation reconciliation ---


def _registry_box():
    """A ``_seam_box`` with real registries + panel so the registration and
    removal bookkeeping paths run against genuine data structures."""
    import threading

    from galaxy.tool_util.toolbox.lineages.factory import LazyLineageMap
    from galaxy.tool_util.toolbox.panel import ToolPanelElements

    box = _seam_box()
    box._tools_by_id = {}
    box._tool_versions_by_id = {}
    box._tools_by_old_id = {}
    box._tools_by_uuid = {}
    box._tool_panel = ToolPanelElements()
    box._lineage_map = LazyLineageMap(box.app, versions_for=box._index_versions_for)
    box._tool_to_dict_cache = {}
    box._tool_to_dict_cache_admin = {}
    box._curated_tool_tags = None
    box._tool_edam_operations = None
    box._tool_edam_topics = None
    box.data_manager_tools = {}
    box._cache_lock = threading.RLock()
    box._tool_object_cache = {}
    return box


def test_invalidate_index_cache_reconciles_peer_removed_entries():
    box = _registry_box()
    box._tool_index = ToolIndex()
    for tool_id in ("keep_tool", "gone_tool"):
        entry = _entry(id=tool_id)
        box._tool_index.add_entry(entry)
        box._register_lazy_entry(entry)
    reloaded = ToolIndex()
    reloaded.add_entry(_entry(id="keep_tool"))
    box._store.load_index.return_value = reloaded
    box.invalidate_index_cache()
    assert "gone_tool" not in box._tools_by_id
    assert "gone_tool" not in box._tool_versions_by_id
    assert "tool_gone_tool" not in box._tool_panel
    assert "keep_tool" in box._tools_by_id
    assert "tool_keep_tool" in box._tool_panel


def test_invalidate_index_cache_keeps_unindexed_tools():
    # Internal/dynamic tools never enter the persisted index — the removal
    # diff must not touch them.
    box = _registry_box()
    box._tool_index = ToolIndex()
    internal = _stub(_entry(id="__SET_METADATA__"))
    box._tools_by_id["__SET_METADATA__"] = internal
    box._store.load_index.return_value = ToolIndex()
    box.invalidate_index_cache()
    assert box._tools_by_id["__SET_METADATA__"] is internal


def test_remove_tool_by_id_broadcasts_reload_to_peers(monkeypatch):
    import galaxy.queue_worker as queue_worker_mod

    box = _registry_box()
    box._tool_index = ToolIndex()
    entry = _entry(id="doomed")
    box._tool_index.add_entry(entry)
    box._register_lazy_entry(entry)
    calls = []
    monkeypatch.setattr(queue_worker_mod, "send_control_task", lambda app, task, **kwargs: calls.append((task, kwargs)))
    box.remove_tool_by_id("doomed")
    box._store.remove_index_entry.assert_called_once_with("doomed")
    assert calls == [("reload_tool_source_cache", {"noop_self": True})]
    assert "doomed" not in box._tools_by_id
