"""Unit tests for tool source store freshness probes."""

import logging

import pytest

from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.freshness import (
    cvmfs_revision_token,
    FreshnessProbeError,
    tool_confs_token,
)
from galaxy.tools.source_store.index import ToolIndex
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore


def _config(tmp_path, confs):
    class _Cfg:
        tool_path = str(tmp_path)
        data_manager_config_file = None
        shed_data_manager_config_file = None

        def all_tool_config_files(self):
            return [str(c) for c in confs]

    return _Cfg()


def test_tool_confs_token_stable_until_conf_content_changes(tmp_path):
    conf = tmp_path / "tool_conf.xml"
    conf.write_text('<toolbox><tool file="a.xml"/></toolbox>')
    cfg = _config(tmp_path, [conf])
    first = tool_confs_token(cfg)
    assert tool_confs_token(cfg) == first
    conf.write_text('<toolbox><tool file="a.xml"/><tool file="b.xml"/></toolbox>')
    assert tool_confs_token(cfg) != first


def test_tool_confs_token_sees_tool_dir_membership_changes(tmp_path):
    dyn = tmp_path / "dyn"
    dyn.mkdir()
    (dyn / "sub").mkdir()
    conf = tmp_path / "tool_conf.xml"
    conf.write_text('<toolbox><tool_dir dir="dyn"/></toolbox>')
    cfg = _config(tmp_path, [conf])

    before = tool_confs_token(cfg)
    (dyn / "new_tool.xml").write_text("<tool/>")
    after_top_level = tool_confs_token(cfg)
    assert after_top_level != before

    (dyn / "sub" / "nested_tool.xml").write_text("<tool/>")
    assert tool_confs_token(cfg) != after_top_level


def test_cvmfs_revision_token_ascends_to_the_mount_root():
    def fake_getxattr(path, attribute):
        if path == "/cvmfs/main.galaxyproject.org" and attribute == "user.revision":
            return b"1042"
        raise OSError(61, "no attribute")

    token = cvmfs_revision_token("/cvmfs/main.galaxyproject.org/galaxy/store.sqlite", _getxattr=fake_getxattr)
    assert token == "cvmfs:main.galaxyproject.org:1042"


def test_cvmfs_revision_token_raises_off_cvmfs():
    def fake_getxattr(path, attribute):
        raise OSError(61, "no attribute")

    with pytest.raises(FreshnessProbeError):
        cvmfs_revision_token("/plain/local/path", _getxattr=fake_getxattr)


def test_index_is_fresh_tracks_probe(tmp_path):
    current = {"token": "confs:a"}
    store = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path}/a.sqlite", freshness_probe=lambda: current["token"])
    assert store.index_is_fresh() is False
    store.store_index(ToolIndex(freshness_token="confs:a"))
    assert store.index_is_fresh() is True
    current["token"] = "confs:b"
    assert store.index_is_fresh() is False


def test_index_is_fresh_none_without_probe(tmp_path):
    store = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path}/a.sqlite")
    store.store_index(ToolIndex(freshness_token="confs:a"))
    assert store.index_is_fresh() is None


def test_index_is_fresh_false_when_probe_fails(tmp_path):
    def broken_probe():
        raise FreshnessProbeError("repo not mounted")

    store = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path}/a.sqlite", freshness_probe=broken_probe)
    store.store_index(ToolIndex(freshness_token="cvmfs:r:1"))
    assert store.index_is_fresh() is False


def _stamped_store(path, token, probe_token, read_only=False):
    SqlAlchemyToolSourceStore(url=f"sqlite:///{path}").store_index(ToolIndex(freshness_token=token))
    return SqlAlchemyToolSourceStore(url=f"sqlite:///{path}", read_only=read_only, freshness_probe=lambda: probe_token)


def test_composite_fresh_when_all_members_fresh(tmp_path):
    ro = _stamped_store(tmp_path / "ro.sqlite", "cvmfs:r:1", "cvmfs:r:1", read_only=True)
    rw = _stamped_store(tmp_path / "rw.sqlite", "confs:x", "confs:x")
    composite = CompositeToolSourceStore(members=[("ro", ro), ("rw", rw)], default="rw")
    assert composite.index_is_fresh() is True


def test_composite_stale_writable_member_wins(tmp_path):
    ro = _stamped_store(tmp_path / "ro.sqlite", "cvmfs:r:1", "cvmfs:r:1", read_only=True)
    rw = _stamped_store(tmp_path / "rw.sqlite", "confs:x", "confs:y")
    composite = CompositeToolSourceStore(members=[("ro", ro), ("rw", rw)], default="rw")
    assert composite.index_is_fresh() is False


def test_composite_stale_read_only_member_warns_but_stays_fresh(tmp_path, caplog):
    ro = _stamped_store(tmp_path / "ro.sqlite", "cvmfs:r:1", "cvmfs:r:2", read_only=True)
    rw = _stamped_store(tmp_path / "rw.sqlite", "confs:x", "confs:x")
    composite = CompositeToolSourceStore(members=[("ro", ro), ("rw", rw)], default="rw")
    with caplog.at_level(logging.WARNING):
        assert composite.index_is_fresh() is True
    assert "repopulated upstream" in caplog.text


def test_composite_member_without_probe_downgrades_to_none(tmp_path):
    ro = _stamped_store(tmp_path / "ro.sqlite", "cvmfs:r:1", "cvmfs:r:1", read_only=True)
    rw = SqlAlchemyToolSourceStore(url=f"sqlite:///{tmp_path}/rw.sqlite")
    composite = CompositeToolSourceStore(members=[("ro", ro), ("rw", rw)], default="rw")
    assert composite.index_is_fresh() is None
