"""Unit tests for tool source storage backends.

Tests exercise the sqlalchemy/sqlite backend directly and the store
factory / per-conf routing on top of it.
"""

import pytest

from galaxy.tools.source_store import (
    build_named_store,
    build_tool_source_store,
    ConfigurationError,
    factory as factory_module,
    StoredToolSource,
)
from galaxy.tools.source_store.composite import CompositeToolSourceStore
from galaxy.tools.source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tools.source_store.sqlalchemy import SqlAlchemyToolSourceStore


class FakeConfig:
    """Fake config for testing store factory."""

    shed_tool_config_file: str | None = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def all_tool_config_files(self):
        # Mirror GalaxyAppConfiguration.all_tool_config_files: the tool_config
        # list plus the shed conf (store discovery must see both).
        configs = list(getattr(self, "tool_configs", None) or [])
        if self.shed_tool_config_file and self.shed_tool_config_file not in configs:
            configs.append(self.shed_tool_config_file)
        return configs


def _sqlite_url(path):
    return f"sqlite:///{path}"


class TestSqlAlchemyBackend:
    """Tests for the sqlalchemy/sqlite backend."""

    def test_sqlalchemy_store_basic_operations(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "ts.sqlite"))

        tool_source = StoredToolSource(
            hash="sa_test_hash_123",
            tool_source_class="XmlToolSource",
            raw_source='<tool id="sa_test" version="2.0"><command>cat</command></tool>',
            tool_id="sa_test_tool",
            tool_version="2.0",
        )
        store.store(tool_source)

        assert store.exists("sa_test_hash_123")
        retrieved = store.get("sa_test_hash_123")
        assert retrieved is not None
        assert retrieved.tool_id == "sa_test_tool"
        assert store.count() >= 1
        assert store.delete("sa_test_hash_123")
        assert not store.exists("sa_test_hash_123")

    def test_sqlalchemy_identical_content_keeps_row_per_source_path(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "twins.sqlite"))
        for path in ("/galaxy/tools/a/upload.xml", "/galaxy/tools/b/upload.xml"):
            store.store(
                StoredToolSource(
                    hash="twin_hash",
                    tool_source_class="XmlToolSource",
                    raw_source="<tool/>",
                    tool_id="upload1",
                    tool_version="1.1.7",
                    source_path=path,
                )
            )
        assert store.get_by_source_path("/galaxy/tools/a/upload.xml") is not None
        assert store.get_by_source_path("/galaxy/tools/b/upload.xml") is not None
        assert store.delete("twin_hash")
        assert store.get_by_source_path("/galaxy/tools/a/upload.xml") is None

    def test_count_tracks_store_and_delete(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "count.sqlite"))
        assert store.count() == 0
        store.store(
            StoredToolSource(
                hash="count_hash",
                tool_source_class="XmlToolSource",
                raw_source="<tool/>",
                tool_id="count_test",
                tool_version="1.0",
            )
        )
        assert store.count() == 1
        assert store.delete("count_hash")
        assert store.count() == 0

    def test_changed_content_updates_path_row_in_place(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "edited.sqlite"))
        path = "/galaxy/tools/edited.xml"

        def _stored(hash, raw):
            return StoredToolSource(
                hash=hash,
                tool_source_class="XmlToolSource",
                raw_source=raw,
                tool_id="upload1",
                tool_version="1.1.7",
                source_path=path,
            )

        store.store(_stored("edited_hash_v1", "<tool/>"))
        store.store(_stored("edited_hash_v2", "<tool><description/></tool>"))
        row = store.get_by_source_path(path)
        assert row is not None
        assert row.hash == "edited_hash_v2"
        assert not store.exists("edited_hash_v1")

    def test_identical_content_updates_path_metadata(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "metadata.sqlite"))
        path = "/galaxy/tools/metadata.xml"
        original = StoredToolSource(
            hash="same_hash",
            tool_source_class="XmlToolSource",
            raw_source="<tool/>",
            tool_id="old_id",
            tool_version="1.0",
            tool_dir="/old/tools",
            source_path=path,
            metadata={"file_hash": "old"},
        )
        updated = StoredToolSource(
            hash="same_hash",
            tool_source_class="XmlToolSource",
            raw_source="<tool/>",
            tool_id="new_id",
            tool_version="2.0",
            tool_dir="/new/tools",
            source_path=path,
            metadata={"file_hash": "new"},
        )

        store.store(original)
        store.store(updated)

        row = store.get_by_source_path(path)
        assert row is not None
        assert row.tool_id == "new_id"
        assert row.tool_version == "2.0"
        assert row.tool_dir == "/new/tools"
        assert row.metadata == {"file_hash": "new"}

    def test_pathless_sources_dedupe_on_hash(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "pathless.sqlite"))
        for _ in range(2):
            store.store(
                StoredToolSource(
                    hash="pathless_hash",
                    tool_source_class="XmlToolSource",
                    raw_source="<tool/>",
                    tool_id="upload1",
                    tool_version="1.1.7",
                )
            )
        assert store.count() == 1
        assert store.delete("pathless_hash")
        assert not store.exists("pathless_hash")

    def test_remove_index_entry_persists_removal(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "ridx.sqlite"))
        index = ToolIndex()
        index.add_entry(ToolIndexEntry(id="removable", version="1.0", name="Removable", panel_section_id="sec1"))
        store.store_index(index)

        store.remove_index_entry("removable")
        store.invalidate_index_cache()

        reloaded = store.load_index()
        assert reloaded is not None
        assert reloaded.get("removable") is None
        assert "removable" not in reloaded.by_section.get("sec1", [])
        assert all(item.tool_id != "removable" for item in reloaded.panel_items)

    def test_update_index_entry_reaches_versioned_lookups(self, tmp_path):
        store = SqlAlchemyToolSourceStore(url=_sqlite_url(tmp_path / "uidx.sqlite"))
        index = ToolIndex()
        index.add_entry(ToolIndexEntry(id="dm_tool", version="1.0", name="DM"))
        store.store_index(index)

        store.update_index_entry(ToolIndexEntry(id="dm_tool", version="1.0", name="DM", description="updated"))
        store.invalidate_index_cache()

        reloaded = store.load_index()
        assert reloaded is not None
        versioned = reloaded.get("dm_tool", "1.0")
        assert versioned is not None
        assert versioned.description == "updated"

    def test_sqlalchemy_store_persistence(self, tmp_path):
        url = _sqlite_url(tmp_path / "ts.sqlite")
        store1 = SqlAlchemyToolSourceStore(url=url)
        store1.store(
            StoredToolSource(
                hash="persist_test_hash",
                tool_source_class="XmlToolSource",
                raw_source='<tool id="persist"><command>echo</command></tool>',
                tool_id="persist_tool",
                tool_version="1.0",
            )
        )
        store2 = SqlAlchemyToolSourceStore(url=url)
        assert store2.exists("persist_test_hash")
        retrieved = store2.get("persist_test_hash")
        assert retrieved is not None
        assert retrieved.tool_id == "persist_tool"


class TestBuildToolSourceStore:
    """Tests for the store factory function."""

    def test_build_default_sqlite_store(self, tmp_path):
        config = FakeConfig(
            tool_source_database_connection=_sqlite_url(tmp_path / "default.sqlite"),
            tool_configs=[],
            tool_source_stores=None,
            use_cached_toolbox=False,
        )
        store = build_tool_source_store(config)  # type: ignore[arg-type]
        assert isinstance(store, SqlAlchemyToolSourceStore)

    def test_build_default_in_memory_sqlite_store(self):
        config = FakeConfig(
            tool_source_database_connection="sqlite:///:memory:",
            tool_configs=[],
            tool_source_stores=None,
            use_cached_toolbox=False,
        )
        store = build_tool_source_store(config)  # type: ignore[arg-type]
        assert isinstance(store, SqlAlchemyToolSourceStore)

    def test_build_store_missing_connection_raises(self):
        config = FakeConfig(
            tool_source_database_connection=None,
            tool_configs=[],
            tool_source_stores=None,
            use_cached_toolbox=False,
        )
        with pytest.raises(ConfigurationError):
            build_tool_source_store(config)  # type: ignore[arg-type]

    def test_build_non_sqlite_url_passes_through(self, monkeypatch):
        class CapturingStore:
            read_only = False

            def __init__(self, url: str, read_only: bool, freshness_probe=None):
                self.url = url
                self.read_only = read_only
                self.freshness_probe = freshness_probe

        monkeypatch.setattr(factory_module, "SqlAlchemyToolSourceStore", CapturingStore)
        config = FakeConfig(
            tool_source_database_connection="postgresql://galaxy@example.org/tool_sources",
            tool_configs=[],
            tool_source_stores=None,
            use_cached_toolbox=False,
        )
        store = build_tool_source_store(config)  # type: ignore[arg-type]
        assert isinstance(store, CapturingStore)
        assert store.url == "postgresql://galaxy@example.org/tool_sources"
        assert store.read_only is False

    def test_named_store_missing_url_raises(self):
        with pytest.raises(ConfigurationError):
            build_named_store("missing", {"read_only": True}, None)  # type: ignore[arg-type]

    def test_named_store_old_backend_path_spec_raises(self, tmp_path):
        with pytest.raises(ConfigurationError):
            build_named_store("old", {"backend": "sqlalchemy", "path": str(tmp_path / "old.sqlite")}, None)  # type: ignore[arg-type]


class TestPerConfStoreRouting:
    """Tests for per-conf store routing in build_tool_source_store."""

    def _config(self, tmp_path, **overrides):
        defaults = dict(
            tool_source_database_connection=_sqlite_url(tmp_path / "ts.sqlite"),
            tool_configs=[],
            tool_source_stores={},
        )
        defaults.update(overrides)
        return FakeConfig(**defaults)

    def test_no_per_conf_store_returns_default(self, tmp_path):
        conf = tmp_path / "extra_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox/>\n')
        config = self._config(tmp_path, tool_configs=[str(conf)])
        store = build_tool_source_store(config)
        assert isinstance(store, SqlAlchemyToolSourceStore)
        assert not isinstance(store, CompositeToolSourceStore)

    def test_unknown_per_conf_store_raises(self, tmp_path):
        conf = tmp_path / "extra_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox store="missing_alias"/>\n')
        config = self._config(tmp_path, tool_configs=[str(conf)])
        with pytest.raises(ConfigurationError):
            build_tool_source_store(config)

    def test_store_declared_on_shed_conf_is_discovered(self, tmp_path):
        # Regression: a store referenced from shed_tool_config_file is reachable
        # only via all_tool_config_files(), not the bare tool_configs list, so
        # store discovery must walk the former.
        conf = tmp_path / "shed_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox store="cvmfs_main"/>\n')
        config = self._config(
            tmp_path,
            tool_configs=[],
            shed_tool_config_file=str(conf),
            tool_source_stores={"cvmfs_main": {"url": _sqlite_url(tmp_path / "cvmfs.sqlite")}},
        )
        store = build_tool_source_store(config)
        assert isinstance(store, CompositeToolSourceStore)


class TestToolIndex:
    """Tests for ToolIndex functionality."""

    def test_index_serialization(self):
        """Test index model_dump/model_validate round trip."""
        index = ToolIndex()
        index.entries["test_tool"] = ToolIndexEntry(
            id="test_tool",
            name="Test",
            version="1.0",
            description="Test tool",
            labels=["genomics"],
        )
        index.by_section["section1"] = ["test_tool"]

        data = index.model_dump(mode="json")

        restored = ToolIndex.model_validate(data)

        assert "test_tool" in restored.entries
        assert restored.entries["test_tool"].name == "Test"
        assert "section1" in restored.by_section

    def test_index_get_tests_summary(self):
        """Test generating tests summary from index."""
        index = ToolIndex()
        index.entries["tool1"] = ToolIndexEntry(
            id="tool1",
            name="Tool 1",
            version="1.0",
            test_count=3,
        )
        index.entries["tool2"] = ToolIndexEntry(
            id="tool2",
            name="Tool 2",
            version="2.0",
            test_count=0,
        )

        summary = index.get_tests_summary()
        # Tools with tests must appear; tools without tests must not.
        assert "tool1" in summary
        assert summary["tool1"]["1.0"]["count"] == 3
        assert summary["tool1"]["1.0"]["tool_name"] == "Tool 1"
        assert "tool2" not in summary

    def test_index_get_all_requirements(self):
        """Test aggregating all requirements from index."""
        index = ToolIndex()
        index.entries["tool1"] = ToolIndexEntry(
            id="tool1",
            name="Tool 1",
            version="1.0",
            requirements=[
                {"name": "samtools", "version": "1.0", "type": "package"},
            ],
        )

        requirements = index.get_all_requirements()
        assert isinstance(requirements, list)
        assert {"name": "samtools", "version": "1.0", "type": "package"} in requirements
