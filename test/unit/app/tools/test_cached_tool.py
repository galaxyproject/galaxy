import logging
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from typing import (
    Any,
    cast,
)
from unittest.mock import MagicMock

import pytest
from cachetools import LRUCache

import galaxy.queue_worker as queue_worker_mod
import galaxy.tools.cached_toolbox as mod
from galaxy.app_unittest_utils.tool_source_support import populate_config
from galaxy.exceptions import ConfigurationError
from galaxy.tool_util.toolbox.base import NullToolTagManager
from galaxy.tool_util.toolbox.lineages.factory import CachedLineageMap
from galaxy.tool_util.toolbox.panel import (
    ToolPanelElements,
    ToolSection,
)
from galaxy.tools.cached_toolbox import (
    CachedTool,
    CachedToolBox,
    edited_tool_files,
    MaterializationReason,
    ToolMaterializationError,
)
from galaxy.tools.source_store import (
    populator,
    StoredToolSource,
    ToolSourceStore,
)
from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.factory import _build_default_store
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore
from galaxy.tools.source_store.unavailable import UnavailableToolSourceStore
from galaxy.util.hash_util import md5_hash_file


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


def _stub(entry=None, materialize=None, is_admin=None, url_prefix="/"):
    if materialize is None:

        def materialize(_e, _reason):  # noqa: E306
            raise AssertionError(f"unexpected materialise for {_e.id!r}")

    return CachedTool(
        entry or _entry(),
        materialize_callback=materialize,
        is_admin_user=is_admin or (lambda u: False),
        url_prefix=url_prefix,
    )


def test_forwarded_reads_off_entry():
    e = _entry(
        uuid="891d4dcb-727a-4710-9d18-0fd4791a85c9",
        tags=["mapping"],
        icon="map",
        xrefs=[{"reftype": "bio.tools", "value": "bowtie2"}],
        is_workflow_compatible=False,
        is_datatype_converter=True,
        produces_real_jobs=False,
    )
    t = _stub(e)
    assert t.id == e.id
    assert t.uuid == e.uuid
    assert t.version == e.version
    assert t.name == e.name
    assert t.description == e.description
    assert t.hidden is False
    assert t.require_login is False
    assert t.tool_type == "default"
    assert t.tags == ["mapping"]
    assert t.labels == ["align"]
    assert t.edam_operations == ["operation_0292"]
    assert t.edam_topics == ["topic_0102"]
    assert t.icon == "map"
    assert t.xrefs == [{"reftype": "bio.tools", "value": "bowtie2"}]
    assert t.is_workflow_compatible is False
    assert t.is_datatype_converter is True
    assert t.produces_real_jobs is False


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


def test_mutable_metadata_overrides_round_trip():
    t = _stub(
        _entry(
            changeset_revision="original",
            repository_name="old-name",
            repository_owner="old-owner",
        )
    )
    repository = MagicMock()
    t.name = "Updated"
    t.version = None
    t.hidden = True
    t.labels = ["new"]
    t.tool_shed = "toolshed.example.com"
    t.repository_name = "new-name"
    t.repository_owner = "new-owner"
    t.installed_changeset_revision = "updated"
    t.guid = "shed/repos/owner/repo/tool/1.0"
    t.old_id = "tool"
    t.tool_tags = ["curated"]
    t.tool_shed_repository = repository
    t.tool_errors = "broken"

    assert t.name == "Updated"
    assert t.version is None
    assert t.hidden is True
    assert t.labels == ["new"]
    assert t.tool_shed == "toolshed.example.com"
    assert t.repository_name == "new-name"
    assert t.repository_owner == "new-owner"
    assert t.installed_changeset_revision == "updated"
    assert t.guid == "shed/repos/owner/repo/tool/1.0"
    assert t.old_id == "tool"
    assert t.tool_tags == ["curated"]
    assert t.tool_shed_repository is repository
    assert t.tool_errors == "broken"


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


@pytest.mark.parametrize(
    ("url_prefix", "expected_prefix"),
    [("/", ""), ("/galaxy", "/galaxy"), ("/galaxy/", "/galaxy"), ("/nested/galaxy", "/nested/galaxy")],
)
@pytest.mark.parametrize("tool_id", ["bowtie2", "toolshed.example.com/repos/owner/repo/tool/1.0+galaxy0"])
def test_to_panel_entry_link_respects_prefix_and_encodes_tool_id(url_prefix, expected_prefix, tool_id):
    tool = _stub(_entry(id=tool_id), url_prefix=url_prefix)
    encoded_id = tool_id.replace("/", "%2F").replace("+", "%2B")

    # _stub raises if URL generation tries to materialize the tool.
    assert tool.to_panel_entry()["link"] == f"{expected_prefix}/tool_runner?tool_id={encoded_id}"


@pytest.mark.parametrize("tool_type", ["data_source", "data_source_async"])
def test_to_panel_entry_data_source_link_uses_redirect(tool_type):
    tool = _stub(_entry(id="ucsc_table", tool_type=tool_type), url_prefix="/galaxy")

    assert tool.to_panel_entry()["link"] == "/galaxy/tool_runner/data_source_redirect?tool_id=ucsc_table"


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


def test_to_panel_entry_includes_config_file_for_admin():
    trans = MagicMock()
    trans.user_is_admin = True
    tool = _stub(_entry(source_path="/galaxy/tools/bowtie2.xml"))

    assert tool.to_panel_entry(trans)["config_file"] == "/galaxy/tools/bowtie2.xml"


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
    box._tool_object_cache = LRUCache(maxsize=8)
    box._cache_lock = threading.RLock()
    box._tool_index = ToolIndex()
    box._store = MagicMock()
    box._store.get_by_source_path.return_value = None
    box._shed_short_id_to_guids = {}
    box._deferred_index_entries = None
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
        return {"indexes_written": 1}

    monkeypatch.setattr(mod, "populate_for_paths", fake_populate)
    tool = box.create_tool(config_file=str(tool_file), guid=guid)
    assert isinstance(tool, CachedTool)
    assert tool.id == guid
    import os as _os

    expected_path = _os.path.abspath(str(tool_file))
    assert calls["paths"] == [expected_path]
    assert calls["path_guids"] == {expected_path: guid}
    box._store.invalidate_index_cache.assert_called()


@pytest.mark.parametrize("indexes_written", [0, 1])
def test_index_tool_files_parses_indexed_files_and_reloads_after_a_write(tmp_path, monkeypatch, indexes_written):
    # A repository update rewrites indexed tool files in place, possibly only
    # in the macros they import, so every file is parsed again.
    guid = "toolshed.example.com/repos/owner/repo/updated/1.0"
    tool_file = tmp_path / "updated.xml"
    tool_file.write_text("<tool id='updated' version='1.0'/>")
    box = _seam_box()
    box._tool_index.add_entry(_entry(id=guid))
    calls = []

    def fake_populate(config, paths, path_guids=None, incremental=True, **kwargs):
        calls.append((paths, incremental))
        return {"indexes_written": indexes_written}

    monkeypatch.setattr(mod, "populate_for_paths", fake_populate)
    box.index_tool_files({str(tool_file): guid})
    assert calls == [([str(tool_file)], False)]
    assert box._store.invalidate_index_cache.called is bool(indexes_written)


def test_index_tool_files_reloads_a_stale_index_another_populate_already_wrote(tmp_path, monkeypatch):
    # A toolbox reload during a repository update indexed the file mid-update,
    # and the install's own populate has since stored and indexed the new
    # content, so this populate writes nothing.
    guid = "toolshed.example.com/repos/owner/repo/updated/1.0"
    tool_file = tmp_path / "updated.xml"
    tool_file.write_text("<tool id='updated' version='1.0'/>")
    box = _seam_box()
    box._tool_index.add_entry(_entry(id=guid, version="1.0", source_hash="before-update", source_path=str(tool_file)))
    box._store.get_by_source_path.return_value = StoredToolSource(
        hash="after-update",
        tool_source_class="XmlToolSource",
        raw_source="<tool/>",
        tool_id=guid,
        tool_version="1.0",
        tool_dir=None,
        source_path=str(tool_file),
        stored_at=datetime.now(timezone.utc),
    )
    current = ToolIndex()
    current.add_entry(_entry(id=guid, version="1.0", source_hash="after-update"))
    box._store.load_index.return_value = current
    monkeypatch.setattr(mod, "populate_for_paths", lambda *args, **kwargs: {"indexes_written": 0})

    box.index_tool_files({str(tool_file): guid})

    entry = box._tool_index.get(guid, "1.0")
    assert entry is not None
    assert entry.source_hash == "after-update"


GUID = "toolshed.example.com/repos/owner/repo/updated/1.0"


def _shed_tool_xml(command, version_attr='version="1.0"'):
    return f'<tool id="updated" name="updated" {version_attr} profile="21.09"><command>{command}</command></tool>'


def _indexed_shed_tool_box(tmp_path, monkeypatch, tool_xml):
    # Converter discovery needs a datatypes registry; these populates cover one shed tool.
    monkeypatch.setattr(populator, "_ensure_datatypes_registry", lambda config: None)
    tools_dir = tmp_path / "shed_tools"
    tools_dir.mkdir()
    tool_file = tools_dir / "updated.xml"
    tool_file.write_text(tool_xml)
    path = str(tool_file)
    conf = tmp_path / "shed_tool_conf.xml"
    conf.write_text(f'<toolbox tool_path="{tools_dir}"></toolbox>')
    config = populate_config(tmp_path, conf)
    populator.populate_store_inline(config, paths=[path], path_guids={path: GUID})
    box = _seam_box()
    box.app.config = config
    box._store = _build_default_store(config)
    box._tool_index = box._store.load_index()
    return box, tool_file


def test_index_tool_files_catches_up_with_a_peer_populate_of_the_same_update(tmp_path, monkeypatch):
    box, tool_file = _indexed_shed_tool_box(tmp_path, monkeypatch, _shed_tool_xml("echo before"))
    path = str(tool_file)
    stale = box._tool_index.get(GUID, "1.0")

    # The install's own populate indexes the update first, so the box's populate writes nothing.
    tool_file.write_text(_shed_tool_xml("echo after"))
    populator.populate_store_inline(box.app.config, paths=[path], path_guids={path: GUID}, incremental=False)
    box.index_tool_files({path: GUID})

    entry = box._tool_index.get(GUID, "1.0")
    stored = box._store.get_by_source_path(path)
    assert stale is not None and entry is not None and stored is not None
    assert entry.source_hash == stored.hash
    assert entry.source_hash != stale.source_hash


def test_materializing_a_stale_entry_after_a_peer_populate_heals(tmp_path, monkeypatch):
    box, tool_file = _indexed_shed_tool_box(tmp_path, monkeypatch, _shed_tool_xml("echo before"))
    path = str(tool_file)
    stale = box._tool_index.get(GUID, "1.0")
    assert stale is not None
    tool_file.write_text(_shed_tool_xml("echo after"))
    populator.populate_store_inline(box.app.config, paths=[path], path_guids={path: GUID}, incremental=False)
    box._materialization_locks = (threading.Lock(),)
    box._create_tool_from_stored_source = lambda stored, entry=None: stored

    materialized = box._load_tool_on_demand(stale, MaterializationReason.EXECUTION)

    assert "echo after" in materialized.raw_source


@pytest.mark.parametrize(
    "version_attr", ['version="1.0"', 'version=""', ""], ids=["version", "empty-version", "no-version"]
)
def test_index_tool_files_keeps_an_index_that_matches_the_store(tmp_path, monkeypatch, version_attr):
    box, tool_file = _indexed_shed_tool_box(tmp_path, monkeypatch, _shed_tool_xml("echo", version_attr))
    index = box._tool_index

    box.index_tool_files({str(tool_file): GUID})

    assert box._tool_index is index


def test_index_tool_files_reloads_once_after_an_in_place_version_bump(tmp_path, monkeypatch):
    # The old version's entry outlives a partial populate under the same path.
    box, tool_file = _indexed_shed_tool_box(tmp_path, monkeypatch, _shed_tool_xml("echo before"))
    path = str(tool_file)
    new_guid = "toolshed.example.com/repos/owner/repo/updated/2.0"
    tool_file.write_text(_shed_tool_xml("echo after", 'version="2.0"'))
    populator.populate_store_inline(box.app.config, paths=[path], path_guids={path: new_guid}, incremental=False)

    box.index_tool_files({path: new_guid})
    caught_up = box._tool_index
    box.index_tool_files({path: new_guid})

    assert caught_up.get(new_guid, "2.0") is not None
    assert box._tool_index is caught_up


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


def test_create_tool_replaces_indexed_data_manager_id_with_registry_id():
    box = _seam_box()
    guid = "toolshed.g2.bx.psu.edu/repos/iuc/data_manager_repeatmasker/repeatmasker_download/0.0.1"
    e = _entry(id="dm_tool", tool_type="manage_data", data_manager_id="repeatmasker_download")
    box._tool_index.entries["dm_tool"] = e
    box.create_tool(config_file=None, guid="dm_tool", data_manager_id=guid)
    assert e.data_manager_id == guid
    box._store.update_index_entry.assert_called_once_with(e)


def test_batch_index_writes_persists_stamped_entries_once():
    box = _seam_box()
    first = _entry(id="dm_one", tool_type="manage_data")
    second = _entry(id="dm_two", tool_type="manage_data")
    box._tool_index.entries.update({"dm_one": first, "dm_two": second})
    with box.batch_index_writes():
        box.create_tool(config_file=None, guid="dm_one", data_manager_id="registry/dm_one")
        box.create_tool(config_file=None, guid="dm_two", data_manager_id="registry/dm_two")
        assert first.data_manager_id == "registry/dm_one"
        box._store.update_index_entries.assert_not_called()
    box._store.update_index_entry.assert_not_called()
    box._store.update_index_entries.assert_called_once_with([first, second])


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
    box._lineage_map = CachedLineageMap(box, versions_for=box._index_versions_for)
    box._tool_to_dict_cache = {}
    box._tool_to_dict_cache_admin = {}
    box._curated_tool_tags = None
    box._tool_edam_operations = None
    box._tool_edam_topics = None
    box._tool_tag_manager = NullToolTagManager()
    box._tool_root_dir = ""
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


def test_invalidate_index_cache_rereads_read_only_member_only_when_republished(tmp_path):
    published_url = f"sqlite:///{tmp_path / 'published.sqlite'}"
    publisher = SqlAlchemyToolSourceStore(published_url)
    published_index = ToolIndex()
    published_index.add_entry(_entry(id="published_tool"))
    publisher.store_index(published_index)
    published = SqlAlchemyToolSourceStore(published_url, read_only=True)
    local = SqlAlchemyToolSourceStore(f"sqlite:///{tmp_path / 'local.sqlite'}")
    local.store_index(ToolIndex())
    store = CompositeToolSourceStore(members=[("published", published), ("local", local)], default="local")
    box = _registry_box()
    box._store = store
    box._tool_index = store.load_index()
    loaded_published = published.load_index()

    peer_index = ToolIndex()
    peer_index.add_entry(_entry(id="peer_tool"))
    SqlAlchemyToolSourceStore(f"sqlite:///{tmp_path / 'local.sqlite'}").store_index(peer_index)
    box.invalidate_index_cache()

    assert published.load_index() is loaded_published
    assert {"published_tool", "peer_tool"} <= set(box._tool_index.entries)

    published_index.add_entry(_entry(id="republished_tool"))
    publisher.store_index(published_index)
    box.invalidate_index_cache()

    assert "republished_tool" in box._tool_index.entries
    assert "republished_tool" in box._tools_by_id


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


def test_remove_tool_by_id_persists_shared_cached_index_before_mutating(monkeypatch, tmp_path):
    """A cache invalidation must not resurrect a locally removed tool."""
    store = SqlAlchemyToolSourceStore(f"sqlite:///{tmp_path / 'tool-source.sqlite'}")
    index = ToolIndex()
    entry = _entry(id="doomed")
    index.add_entry(entry)
    store.store_index(index)

    box = _registry_box()
    box._store = store
    box._tool_index = store.load_index()
    assert box._tool_index is index
    box._register_cached_entry(entry)
    monkeypatch.setattr(queue_worker_mod, "send_control_task", lambda app, task, **kwargs: None)

    box.remove_tool_by_id("doomed")
    store.invalidate_index_cache()

    reloaded = store.load_index()
    assert reloaded is not None
    assert "doomed" not in reloaded.entries


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
    parses: Counter[str] = Counter()

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


def test_fast_path_replays_labels_in_panel_order(tmp_path):
    tool_conf = tmp_path / "tool_conf.xml"
    tool_conf.write_text("""<toolbox>
        <label id="top_label" text="Top label" />
        <tool file="top.xml" />
        <section id="sec1" name="Section 1">
            <label id="section_label" text="Section label" />
            <tool file="section.xml" />
        </section>
        <label id="last_label" text="Last label" />
        </toolbox>""")
    box = _registry_box()
    box._index = 0
    box.can_load_config_file = lambda _path: True
    positioned_panel_keys = set(box._integrated_tool_panel)
    top = _entry(id="top_tool")
    section = _entry(id="section_tool", panel_section_id="sec1", panel_section_name="Section 1")
    for entry in (top, section):
        box._tool_index.add_entry(entry)
        stub = box._register_cached_entry(entry, place_in_panel=False)
        box._place_stub_in_integrated_panel(stub, entry.panel_section_id, entry.panel_section_name)
    box._integrated_tool_panel.stub_tool("section_tool")

    box._load_indexed_panel_structure([str(tool_conf)], positioned_panel_keys)
    super(CachedToolBox, box)._load_tool_panel()

    assert list(box._integrated_tool_panel) == ["label_top_label", "tool_top_tool", "sec1", "label_last_label"]
    assert list(box._integrated_tool_panel["sec1"].elems) == ["label_section_label", "tool_section_tool"]
    assert list(box._tool_panel) == ["label_top_label", "tool_top_tool", "sec1", "label_last_label"]
    assert box._tool_panel["label_top_label"].text == "Top label"
    assert box._tool_panel["sec1"].elems["label_section_label"].text == "Section label"


def test_storage_only_entry_is_not_placed_in_panel():
    box = _registry_box()
    entry = _entry(id="storage_only", in_panel=False)

    box._register_cached_entry(entry)

    assert "storage_only" in box._tools_by_id
    assert "tool_storage_only" not in box._tool_panel
    assert "tool_storage_only" not in box._integrated_tool_panel


def test_fast_path_positions_new_section_at_config_index(tmp_path):
    tool_conf = tmp_path / "tool_conf.xml"
    tool_conf.write_text(
        '<toolbox><section id="local" name="Local"><tool file="local.xml" /></section>'
        '<section id="existing" name="Configured Existing" /></toolbox>'
    )
    box = _registry_box()
    box._index = 0
    box.can_load_config_file = lambda _path: True
    box._integrated_tool_panel["existing"] = ToolSection({"id": "existing", "name": "Existing"})
    entry = _entry(id="local_tool", panel_section_id="local", panel_section_name="Local")
    box._tool_index.add_entry(entry)
    stub = box._register_cached_entry(entry, place_in_panel=False)
    positioned_panel_keys = set(box._integrated_tool_panel)
    box._place_stub_in_integrated_panel(stub, entry.panel_section_id, entry.panel_section_name)

    box._load_indexed_panel_structure([str(tool_conf)], positioned_panel_keys)

    assert list(box._integrated_tool_panel) == ["local", "existing"]
    assert box._integrated_tool_panel["existing"].name == "Existing"


def test_fast_path_watches_tool_dir_without_loading_existing_tools(tmp_path):
    tool_dir = tmp_path / "tools"
    tool_dir.mkdir()
    (tool_dir / "existing.xml").write_text("<tool />")
    tool_conf = tmp_path / "tool_conf.xml"
    tool_conf.write_text('<toolbox tool_path="${tool_conf_dir}"><tool_dir dir="tools" /></toolbox>')
    box = _registry_box()
    box._index = 0
    box.can_load_config_file = lambda _path: True
    box._tool_watcher = MagicMock()
    box._looks_like_a_tool = lambda _path: True
    box.load_tool = MagicMock(side_effect=AssertionError("indexed replay loaded a tool"))

    box._load_indexed_panel_structure([str(tool_conf)], set())

    box.load_tool.assert_not_called()
    box._tool_watcher.watch_directory.assert_called_once()


def test_unconfigured_bundled_version_does_not_replace_configured_tool():
    # A tool conf names jupyter 0.3; newer bundled files are indexed
    # storage-only. The default lookup and the lineage must stay on the
    # configured version, as in the eager toolbox.
    box = _registry_box()
    configured = _entry(id="jupyter", version="0.3", panel_section_id="it", panel_section_name="Interactive")
    box._tool_index.add_entry(configured)
    for version in ("1.0.0", "1.0.3"):
        box._tool_index.add_entry(_entry(id="jupyter", version=version, in_panel=False))
    box._register_cached_entry(configured)

    tool = box.get_tool("jupyter")
    assert tool.version == "0.3"
    assert box._index_versions_for("jupyter") == ["0.3"]
    assert [t.version for t in box.get_tool("jupyter", get_all_versions=True)] == ["0.3"]
    # An explicit unconfigured version is a miss, as in the eager toolbox;
    # direct loads still resolve the bundled file by path.
    assert box.get_tool("jupyter", tool_version="1.0.3").version == "0.3"
    assert not box.has_tool("jupyter", tool_version="1.0.3", exact=True)
    # Materialising the configured version must not register the bundled
    # siblings either, or an exact lookup would serve them from the registry.
    box._load_tool_on_demand = lambda entry, reason: MagicMock()
    box.materialize_tool(tool, reason="execution")
    assert set(box._tool_versions_by_id["jupyter"]) == {"0.3"}
    assert box.get_tool("jupyter", tool_version="1.0.3", exact=True).version == "0.3"


def test_invalidate_index_cache_drops_versions_a_reindex_removed():
    # A peer re-indexed an in-place edit of probe from 1.1 to 1.2 and
    # dropped 1.1 from the index.
    box = _registry_box()
    box._guid_sibling_versions_cache = None
    old = _entry(id="probe", version="1.1", source_hash="h1", source_path="/t/probe.xml")
    box._tool_index.add_entry(old)
    box._register_cached_entry(old)
    assert list(box._lineage_map.get("probe").tool_versions) == ["1.1"]

    reloaded = ToolIndex()
    reloaded.add_entry(_entry(id="probe", version="1.2", source_hash="h2", source_path="/t/probe.xml"))
    box._store.load_index.return_value = reloaded
    box.invalidate_index_cache()

    assert "1.1" not in box._tool_versions_by_id["probe"]
    assert ("probe", "1.1") not in box._cached_tools
    assert list(box._lineage_map.get("probe").tool_versions) == ["1.2"]
    assert not box.has_tool("probe", tool_version="1.1", exact=True)
    # The panel's proxy stays the one served for the surviving version.
    assert box.get_tool("probe", tool_version="1.2") is box._tools_by_id["probe"]
    assert box.get_tool("probe", tool_version="1.1", exact=True).version == "1.2"


@dataclass
class _IndexStore:
    read_only: bool
    index: ToolIndex | None

    def load_index(self) -> ToolIndex | None:
        return self.index


def _indexed(tmp_path, name, tool_id, **overrides):
    path = tmp_path / name
    path.write_text(f"<tool id='{tool_id}' version='1.0'/>")
    return path, _entry(id=tool_id, source_path=str(path), file_hash=md5_hash_file(str(path)), **overrides)


def test_edited_tool_files_selects_only_changed_files(tmp_path):
    shed_guid = "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/1.0"
    edited, edited_entry = _indexed(tmp_path, "edited.xml", "edited")
    shed, shed_entry = _indexed(tmp_path, "shed.xml", shed_guid)
    _, untouched_entry = _indexed(tmp_path, "untouched.xml", "untouched")
    unmodified, _ = _indexed(tmp_path, "unmodified.xml", "unmodified")
    # Not modified since indexing: skipped without hashing, as the eager ToolCache does.
    indexed_at = datetime.fromtimestamp(unmodified.stat().st_mtime + 60, tz=timezone.utc)
    unmodified_entry = _entry(id="unmodified", source_path=str(unmodified), file_hash="stale", indexed_at=indexed_at)
    writable = ToolIndex()
    for entry in (edited_entry, shed_entry, untouched_entry, unmodified_entry):
        writable.add_entry(entry)
    published, published_entry = _indexed(tmp_path, "published.xml", "published")
    read_only = ToolIndex()
    read_only.add_entry(published_entry)
    for path in (edited, shed, published):
        path.write_text(path.read_text().replace("1.0", "1.1"))

    stores = cast(
        list[ToolSourceStore],
        [_IndexStore(read_only=True, index=read_only), _IndexStore(read_only=False, index=writable)],
    )
    assert edited_tool_files(stores) == {str(edited): None, str(shed): shed_guid}


def test_reindex_edited_tool_files_reindexes_selected_files(monkeypatch):
    box = _seam_box()
    box._store.load_index.return_value = ToolIndex()
    monkeypatch.setattr(mod, "edited_tool_files", lambda stores: {"/t/edited.xml": None})
    calls: list[dict[str, str | None]] = []
    monkeypatch.setattr(box, "index_tool_files", calls.append)

    box._reindex_edited_tool_files()

    assert calls == [{"/t/edited.xml": None}]
    box._store.invalidate_index_cache.assert_called_once()


@pytest.mark.parametrize(
    "read_only_member, message",
    [
        (UnavailableToolSourceStore("no compatible external tool source store for 'cloud'"), "no compatible"),
        (_IndexStore(read_only=True, index=None), "'cloud' has no loadable index"),
    ],
)
def test_toolbox_refuses_to_build_without_read_only_store_index(monkeypatch, read_only_member, message):
    # Its tools would otherwise be parsed and held in memory, or self-heal
    # one populate and one whole-index write per tool.
    box = _seam_box()
    default = MagicMock(read_only=False)
    box._store = CompositeToolSourceStore(
        members=[("cloud", read_only_member), ("__default__", default)], default="__default__"
    )
    monkeypatch.setattr(box, "_run_inline_populator", MagicMock(side_effect=AssertionError("populated")))

    with pytest.raises(ConfigurationError, match=message):
        box._init_tools_from_configs([])
    default.load_index.assert_not_called()
