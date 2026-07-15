import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import (
    datetime,
    timezone,
)
from typing import Any
from unittest.mock import MagicMock

import pytest
from cachetools import LRUCache

import galaxy.queue_worker as queue_worker_mod
import galaxy.tools.cached_toolbox as mod
from galaxy.tool_util.toolbox.lineages.factory import CachedLineageMap
from galaxy.tool_util.toolbox.panel import ToolPanelElements
from galaxy.tools.cached_toolbox import (
    CachedTool,
    CachedToolBox,
    MaterializationReason,
    ToolMaterializationError,
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

        def materialize(_e, _reason):  # noqa: E306
            raise AssertionError(f"unexpected materialise for {_e.id!r}")

    return CachedTool(
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

    def materialise(_e, _reason):
        materialised.append(_e.id)
        return _Real()

    t = CachedTool(_entry(), materialize_callback=materialise, is_admin_user=lambda u: False)
    t.hidden = True
    t.labels = ["a", "b"]
    t.tool_shed = "toolshed.example.com"
    assert t.hidden is True
    assert t.labels == ["a", "b"]

    real = t.materialize(MaterializationReason.DETAIL)
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
    def boom(_e, _reason):
        raise AssertionError(f"unexpected materialise for {_e.id!r}")

    t = CachedTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
    d = t.to_panel_entry(trans=None)
    assert d["id"] == "bowtie2"
    assert d["model_class"] == "Tool"
    assert d["link"] == "/tool_runner?tool_id=bowtie2"


def test_tool_tags_answered_without_materialise():
    def boom(_e, _reason):
        raise AssertionError(f"unexpected materialise for {_e.id!r}")

    t = CachedTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
    assert isinstance(t.tool_tags, list)
    t.tool_tags = ["curated"]
    assert t.tool_tags == ["curated"]


def test_dependency_metadata_does_not_materialise():
    entry = _entry(
        requirements=[
            {"name": "samtools", "version": "1.20", "type": "package"},
            {"name": "REF_PATH", "type": "set_environment"},
        ],
        container_requirements=[{"identifier": "quay.io/biocontainers/samtools:1.20", "type": "docker"}],
        profile=21.09,
        produces_real_jobs=False,
    )
    tool = _stub(entry)

    assert [requirement.name for requirement in tool.tool_requirements] == ["samtools"]
    assert [requirement.name for requirement in tool.requirements] == ["samtools", "REF_PATH"]
    assert tool.containers[0].identifier == "quay.io/biocontainers/samtools:1.20"
    assert tool.requires_galaxy_python_environment is False
    assert tool.produces_real_jobs is False


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

    real = _Real()

    def mat(_e, reason):
        assert reason is MaterializationReason.DETAIL
        calls.append("mat")
        return real

    t = CachedTool(_entry(), materialize_callback=mat, is_admin_user=lambda u: False)
    assert t.to_dict(trans=None, io_details=True) == {"id": "real"}
    assert t.to_dict(trans=None, io_details=True) == {"id": "real"}
    assert calls == ["mat", ("real-to_dict", True), "mat", ("real-to_dict", True)]


def test_to_dict_falls_back_to_entry_when_materialise_fails():
    # If a tool can't materialise (e.g. ``upload_dataset`` parameter factory
    # failure) the show endpoint still gets the entry-shape dict.
    def boom(_e, _reason):
        raise ToolMaterializationError(_e.id, "materialise failed")

    t = CachedTool(_entry(), materialize_callback=boom, is_admin_user=lambda u: False)
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


def test_parsed_attributes_are_not_on_cached_tool():
    t = _stub()
    parsed_attribute = "inputs"
    with pytest.raises(AttributeError):
        getattr(t, parsed_attribute)


def test_underscore_attrs_surface_as_attribute_error():
    t = _stub()
    with pytest.raises(AttributeError):
        _ = t.__some_dunder_thing__


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


# --- CachedToolBox.create_tool seam ---


def _seam_box():
    box = CachedToolBox.__new__(CachedToolBox)
    box._cached_tools = {}
    box._tool_index = ToolIndex()
    box._store = MagicMock()
    box._store.get_by_source_path.return_value = None
    box._shed_short_id_to_guids = {}
    box.app = MagicMock()
    box.app.config.is_admin_user = lambda u: False
    box.app.config.preserve_python_environment = "legacy_only"
    return box


def test_create_tool_returns_cachedtool_on_guid_hit():
    box = _seam_box()
    box._tool_index.entries["bowtie2"] = _entry()
    tool = box.create_tool(config_file=None, guid="bowtie2")
    assert isinstance(tool, CachedTool)
    assert tool.id == "bowtie2"


def test_create_tool_returns_cachedtool_on_source_path_hit():
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
    assert isinstance(tool, CachedTool)
    assert tool.id == "bowtie2"


def test_resolve_index_entry_returns_none_when_nothing_matches():
    box = _seam_box()
    assert box._resolve_index_entry(None, None) is None


def test_stored_source_for_entry_uses_source_path_for_identical_content():
    box = _seam_box()
    entry = _entry(source_path="/tools/b/upload.xml", source_hash="same_hash")
    expected = StoredToolSource(
        hash="same_hash",
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        tool_id="upload1",
        tool_dir="/tools/b",
        source_path=entry.source_path,
    )
    box._store.get_by_source_path.return_value = expected

    assert box._stored_source_for_entry(entry) is expected
    box._store.get.assert_not_called()


def test_stored_source_for_entry_rejects_stale_path_row():
    box = _seam_box()
    entry = _entry(source_path="/tools/b/upload.xml", source_hash="current_hash")
    box._store.get_by_source_path.return_value = StoredToolSource(
        hash="stale_hash",
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        source_path=entry.source_path,
    )

    assert box._stored_source_for_entry(entry) is None
    box._store.get.assert_not_called()


def _reconcile_box(index_hashes, store_hashes):
    box = _seam_box()
    box._store.read_only = False
    box._store.list_all.return_value = list(store_hashes)
    index = ToolIndex()
    for position, source_hash in enumerate(index_hashes):
        index.add_entry(_entry(id=f"tool_{position}", source_hash=source_hash))
    box._store.load_index.return_value = index
    return box


def test_index_reconcile_ignores_orphaned_store_rows():
    box = _reconcile_box(index_hashes=["a", "b"], store_hashes=["a", "b", "orphaned"])
    assert box._writable_store_index_needs_population() is False


def test_index_reconcile_repopulates_on_dangling_index_reference():
    box = _reconcile_box(index_hashes=["a", "b"], store_hashes=["a"])
    assert box._writable_store_index_needs_population() is True


def test_create_tool_populates_adhoc_for_existing_file(tmp_path, monkeypatch):
    # Shed installs load cloned tools during metadata generation, before
    # any conf is persisted — a miss for an on-disk file populates that
    # path instead of raising.
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
    assert isinstance(tool, CachedTool)
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
    assert isinstance(tool, CachedTool)
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
    box = _seam_box()
    box._tools_by_id = {}
    box._tool_versions_by_id = {}
    box._tools_by_old_id = {}
    box._tools_by_uuid = {}
    box._tool_panel = ToolPanelElements()
    box._integrated_tool_panel = ToolPanelElements()
    box._lineage_map = CachedLineageMap(box.app, versions_for=box._index_versions_for)
    box._tool_to_dict_cache = {}
    box._tool_to_dict_cache_admin = {}
    box._curated_tool_tags = None
    box._tool_edam_operations = None
    box._tool_edam_topics = None
    box.data_manager_tools = {}
    box._cache_lock = threading.RLock()
    box._materialization_locks = tuple(threading.Lock() for _ in range(4))
    box._tool_object_cache = LRUCache(maxsize=10)
    return box


def test_invalidate_index_cache_reconciles_peer_removed_entries():
    box = _registry_box()
    box._tool_index = ToolIndex()
    for tool_id in ("keep_tool", "gone_tool"):
        entry = _entry(id=tool_id)
        box._tool_index.add_entry(entry)
        box._register_cached_entry(entry)
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
    box = _registry_box()
    box._tool_index = ToolIndex()
    entry = _entry(id="doomed")
    box._tool_index.add_entry(entry)
    box._register_cached_entry(entry)
    calls = []
    monkeypatch.setattr(queue_worker_mod, "send_control_task", lambda app, task, **kwargs: calls.append((task, kwargs)))
    box.remove_tool_by_id("doomed")
    box._store.remove_index_entry.assert_called_once_with("doomed")
    assert calls == [("reload_tool_source_cache", {"noop_self": True})]
    assert "doomed" not in box._tools_by_id


def test_remove_tool_by_id_also_cleans_swapped_in_toolbox(monkeypatch):
    # A reload queued before the removal can swap a new toolbox into
    # app.toolbox, rebuilt from the pre-removal index — cleaning only
    # ``self`` would leave the new box serving the uninstalled tool.
    old_box = _registry_box()
    new_box = _registry_box()
    entry = _entry(id="doomed")
    for box in (old_box, new_box):
        box._tool_index = ToolIndex()
        box._tool_index.add_entry(entry)
        box._register_cached_entry(entry)
    old_box.app.toolbox = new_box
    monkeypatch.setattr(queue_worker_mod, "send_control_task", lambda app, task, **kwargs: None)
    old_box.remove_tool_by_id("doomed")
    assert "doomed" not in old_box._tools_by_id
    assert "doomed" not in new_box._tools_by_id
    assert "tool_doomed" not in new_box._tool_panel


def test_tool_file_on_disk_answers_from_index(tmp_path):
    box = _seam_box()
    box._index_source_paths_cache = None
    indexed_path = "/cvmfs/nowhere.example.org/shed_tools/repos/o/n/rev/t1.xml"
    box._tool_index.add_entry(_entry(id="t1", source_path=indexed_path))
    assert box._tool_file_on_disk(indexed_path) is True
    assert box._tool_file_on_disk(str(tmp_path / "missing.xml")) is False
    on_disk = tmp_path / "real.xml"
    on_disk.write_text("<tool/>")
    assert box._tool_file_on_disk(str(on_disk)) is True


def test_missing_repository_log_level_downgrades_indexed_paths():
    box = _seam_box()
    box._index_source_paths_cache = None
    indexed_path = "/cvmfs/nowhere.example.org/shed_tools/repos/o/n/rev/t1.xml"
    box._tool_index.add_entry(_entry(id="t1", source_path=indexed_path))
    assert box._missing_repository_log_level(indexed_path) == logging.DEBUG
    assert box._missing_repository_log_level("/elsewhere/t2.xml") == logging.WARNING


def test_index_source_paths_refresh_on_index_swap():
    box = _seam_box()
    box._index_source_paths_cache = None
    box._tool_index.add_entry(_entry(id="t1", source_path="/a/t1.xml"))
    assert "/a/t1.xml" in box._index_source_paths()
    swapped = ToolIndex()
    swapped.add_entry(_entry(id="t2", source_path="/b/t2.xml"))
    box._tool_index = swapped
    assert box._index_source_paths() == {"/b/t2.xml"}


def test_index_versions_for_collects_guid_sibling_versions():
    box = _seam_box()
    box._guid_sibling_versions_cache = None
    prefix = "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp"
    for version in ("0.20.1", "0.23.2"):
        box._tool_index.add_entry(_entry(id=f"{prefix}/{version}", version=version))
    box._tool_index.add_entry(_entry(id="unrelated", version="1.0"))
    versions = box._index_versions_for(f"{prefix}/0.20.1")
    assert set(versions) == {"0.20.1", "0.23.2"}
    assert box._index_versions_for("unrelated") == ["1.0"]


def test_guid_sibling_versions_reset_on_in_place_removal():
    box = _registry_box()
    box._guid_sibling_versions_cache = None
    prefix = "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp"
    for version in ("0.20.1", "0.23.2"):
        entry = _entry(id=f"{prefix}/{version}", version=version)
        box._tool_index.add_entry(entry)
        box._register_cached_entry(entry)
    assert set(box._index_versions_for(f"{prefix}/0.20.1")) == {"0.20.1", "0.23.2"}
    box._remove_tool_in_memory(f"{prefix}/0.23.2")
    assert box._index_versions_for(f"{prefix}/0.20.1") == ["0.20.1"]


def test_get_tool_short_id_missing_version_honors_exact():
    box = _registry_box()
    guid = "toolshed.example.com/repos/owner/repo/cat/1.0"
    box._tool_index.add_entry(_entry(id=guid, version="1.0"))
    box._shed_short_id_to_guids = {"cat": {guid}}
    assert box.get_tool("cat", tool_version="9.9", exact=True) is None
    default_tool = box.get_tool("cat", tool_version="9.9", exact=False)
    assert isinstance(default_tool, CachedTool)
    assert default_tool.id == guid


def _materialising_box(source_hash):
    box = _registry_box()
    box._guid_sibling_versions_cache = None
    entry = _entry(id="tool1", version="1.0", source_hash=source_hash, source_path="/t/tool1.xml")
    box._tool_index.add_entry(entry)
    box._register_cached_entry(entry)
    holder = {"hash": source_hash}
    box._store.get_by_source_path.side_effect = lambda path: StoredToolSource(
        hash=holder["hash"],
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        tool_id="tool1",
        tool_dir=None,
        source_path="/t/tool1.xml",
    )

    def fake_create(stored, entry=None):
        tool = MagicMock()
        tool.id = entry.id
        tool.version = entry.version
        tool.old_id = entry.id
        tool.guid = None
        tool.uuid = None
        tool.hidden = False
        return tool

    box._create_tool_from_stored_source = fake_create
    return box, holder


def test_invalidate_index_cache_refreshes_materialised_tool_on_content_change():
    box, holder = _materialising_box("hash_v1")
    proxy = box.get_tool("tool1")
    assert box._tools_by_id["tool1"] is proxy
    original = box.materialize_tool(proxy, reason="execution")

    holder["hash"] = "hash_v2"
    reloaded = ToolIndex()
    reloaded.add_entry(_entry(id="tool1", version="1.0", source_hash="hash_v2", source_path="/t/tool1.xml"))
    box._store.load_index.return_value = reloaded
    box.invalidate_index_cache()

    refreshed = box.get_tool("tool1")
    assert refreshed is proxy
    assert refreshed._entry.source_hash == "hash_v2"
    assert not any(cached is original for cached in box._tool_object_cache.values())
    assert box.materialize_tool(refreshed, reason="execution") is not original


def test_invalidate_index_cache_keeps_materialised_tool_when_content_unchanged():
    box, _holder = _materialising_box("hash_v1")
    proxy = box.get_tool("tool1")
    original = box.materialize_tool(proxy, reason="execution")

    reloaded = ToolIndex()
    reloaded.add_entry(_entry(id="tool1", version="1.0", source_hash="hash_v1", source_path="/t/tool1.xml"))
    box._store.load_index.return_value = reloaded
    box.invalidate_index_cache()

    assert box.get_tool("tool1") is proxy
    assert box.materialize_tool(proxy, reason="execution") is original


def test_materialized_tools_are_owned_only_by_bounded_lru():
    box = _registry_box()
    box._tool_object_cache = LRUCache(maxsize=1)
    entries = {
        tool_id: _entry(id=tool_id, version="1.0", source_hash=f"hash_{tool_id}", source_path=f"/t/{tool_id}.xml")
        for tool_id in ("one", "two")
    }
    for entry in entries.values():
        box._tool_index.add_entry(entry)
        box._register_cached_entry(entry)

    box._store.get_by_source_path.side_effect = lambda path: StoredToolSource(
        hash=f"hash_{path.removeprefix('/t/').removesuffix('.xml')}",
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        source_path=path,
    )
    parses = Counter()

    class RealTool:
        pass

    def create(_stored, entry=None):
        parses[entry.id] += 1
        return RealTool()

    box._create_tool_from_stored_source = create
    proxies = {tool_id: box.get_tool(tool_id) for tool_id in entries}
    box.materialize_tool(proxies["one"], reason="execution")
    box.materialize_tool(proxies["two"], reason="execution")

    assert len(box._tool_object_cache) == 1
    assert box.get_tool("one") is proxies["one"]
    box.materialize_tool(proxies["one"], reason="execution")
    assert parses == Counter(one=2, two=1)


def test_materialization_is_single_flight_per_tool():
    box, _holder = _materialising_box("hash_v1")
    proxy = box.get_tool("tool1")
    workers = 8
    ready = threading.Barrier(workers + 1)
    parses = 0

    class RealTool:
        pass

    def create(_stored, entry=None):
        nonlocal parses
        parses += 1
        return RealTool()

    box._create_tool_from_stored_source = create

    def materialize():
        ready.wait()
        return box.materialize_tool(proxy, reason="execution")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(materialize) for _ in range(workers)]
        ready.wait()
        results = [future.result() for future in futures]

    assert parses == 1
    assert all(result is results[0] for result in results)


def test_fast_path_places_hidden_entry_in_integrated_panel_only():
    box = _registry_box()
    visible = _entry(
        id="visible_tool", version="1.0", hidden=False, panel_section_id="sec1", panel_section_name="Section 1"
    )
    hidden = _entry(
        id="hidden_tool", version="1.0", hidden=True, panel_section_id="sec1", panel_section_name="Section 1"
    )
    box._tool_index.add_entry(visible)
    box._tool_index.add_entry(hidden)

    placements = box._index_panel_items()
    assert {p.tool_id for p in placements} == {"visible_tool", "hidden_tool"}
    for placement in placements:
        stub = box._register_cached_entry(box._tool_index.entries[placement.tool_id], place_in_panel=False)
        box._place_stub(stub, placement.section_id, placement.section_name, hidden=placement.hidden)

    integrated = box._integrated_tool_panel["sec1"].elems
    assert integrated.has_tool_with_id("hidden_tool")
    assert integrated.has_tool_with_id("visible_tool")
    live = box._tool_panel["sec1"].elems
    assert live.has_tool_with_id("visible_tool")
    assert not live.has_tool_with_id("hidden_tool")
