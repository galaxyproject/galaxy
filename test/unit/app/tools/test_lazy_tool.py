import logging
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from galaxy.tool_source_store import StoredToolSource
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.lazy_toolbox import (
    LazyTool,
    LazyToolBox,
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


def test_to_dict_fast_path_does_not_materialise():
    t = _stub()
    d = t.to_dict(trans=None, link_details=False)
    assert d["id"] == "bowtie2"
    assert d["model_class"] == "Tool"
    assert d["link"] == "/api/tools/bowtie2"


def test_to_dict_link_details_materialises_exactly_once():
    calls = []

    class _Real:
        def to_dict(self, trans, link_details, tool_help, **kw):
            calls.append("real-to_dict")
            return {"id": "real"}

    def mat(_e):
        calls.append("mat")
        return _Real()

    t = LazyTool(_entry(), materialize_callback=mat, is_admin_user=lambda u: False)
    assert t.to_dict(trans=None, link_details=True) == {"id": "real"}
    assert t.to_dict(trans=None, link_details=True) == {"id": "real"}
    assert calls == ["mat", "real-to_dict", "real-to_dict"]


def test_allow_user_access_uses_index_data_without_materialise():
    t = _stub(_entry(require_login=True))
    assert t.allow_user_access(user=None) is False

    class _U:
        id = 1

    assert t.allow_user_access(user=_U()) is True


def test_allow_user_access_blocks_non_admin_for_data_manager():
    e = _entry(tool_type="data_manager", require_login=False)
    t = _stub(e, is_admin=lambda u: False)

    class _U:
        id = 5

    assert t.allow_user_access(user=_U(), attempting_access=False) is False


def test_allow_user_access_allows_admin_for_data_manager():
    e = _entry(tool_type="data_manager", require_login=False)
    t = _stub(e, is_admin=lambda u: True)

    class _U:
        id = 5

    assert t.allow_user_access(user=_U()) is True


def test_strict_getattr_raises_with_clear_message():
    t = _stub()
    with pytest.raises(NotImplementedError) as ei:
        _ = t.tool_action
    assert "tool_action" in str(ei.value)
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
        stored_at=datetime.utcnow(),
    )
    tool = box.create_tool(config_file="/tools/bowtie2.xml")
    assert isinstance(tool, LazyTool)
    assert tool.id == "bowtie2"


def test_resolve_index_entry_returns_none_when_nothing_matches():
    box = _seam_box()
    assert box._resolve_index_entry(None, None) is None


def test_create_tool_raises_on_index_miss():
    # The populator owns the index — including the Galaxy-internal lib
    # tools listed in ``galaxy.tools.special_tools.hidden_lib_tool_paths``.
    # A miss in ``create_tool`` is a contract failure (operator forgot
    # to repopulate, new ad-hoc tool load not added to the lib list);
    # raise loudly with a pointer to the fix.
    box = _seam_box()
    with pytest.raises(RuntimeError, match="no index entry"):
        box.create_tool(config_file="/tools/unknown.xml", guid=None)


def test_load_tool_from_cache_returns_none():
    box = _seam_box()
    assert box.load_tool_from_cache("any/path.xml") is None


def test_add_tool_to_cache_is_noop():
    box = _seam_box()
    assert box.add_tool_to_cache(object(), "any/path.xml") is None
