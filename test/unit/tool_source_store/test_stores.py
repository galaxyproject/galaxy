"""Unit tests for tool source storage backends.

Tests verify that the tool source store classes work correctly with
different backends (database, sqlalchemy). These tests directly
instantiate the stores to test the backend implementations.
"""

import pytest

from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.tool_source_store import (
    build_tool_source_store,
    ConfigurationError,
    StoredToolSource,
)
from galaxy.tool_source_store.database import DatabaseToolSourceStore
from galaxy.tool_source_store.index import (
    ToolIndex,
    ToolIndexEntry,
)
from galaxy.tool_source_store.sqlalchemy import SqlAlchemyToolSourceStore


class FakeConfig:
    """Fake config for testing store factory."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestDatabaseBackend:
    """Unit tests for database backend using MockApp."""

    def test_database_store_basic_operations(self):
        """Test basic store/get operations with database backend."""
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        test_hash = "test_hash_unit_123"

        try:
            tool_source = StoredToolSource(
                hash=test_hash,
                tool_source_class="XmlToolSource",
                raw_source='<tool id="test" version="1.0"><command>echo</command></tool>',
                tool_id="test_unit_tool",
                tool_version="1.0",
            )

            store.store(tool_source)
            app.model.context.commit()

            assert store.exists(tool_source.hash)

            retrieved = store.get(tool_source.hash)
            assert retrieved is not None
            assert retrieved.tool_id == "test_unit_tool"
            assert retrieved.tool_version == "1.0"
            assert "<tool" in retrieved.raw_source

            assert store.delete(tool_source.hash)
            app.model.context.commit()
            assert not store.exists(tool_source.hash)
        finally:
            if store.exists(test_hash):
                store.delete(test_hash)
                app.model.context.commit()

    def test_database_store_index_operations(self):
        """Test tool index storage with database backend."""
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]

        index = ToolIndex()
        index.entries["test_tool_db"] = ToolIndexEntry(
            id="test_tool_db",
            name="Test Tool DB",
            version="1.0",
            description="A test tool",
        )

        store.store_index(index)
        app.model.context.commit()

        # Clear the cached index to force reload from database
        store.invalidate_index_cache()

        loaded_index = store.load_index()
        assert loaded_index is not None
        assert "test_tool_db" in loaded_index.entries
        assert loaded_index.entries["test_tool_db"].name == "Test Tool DB"

    def test_database_store_get_by_tool_id(self):
        """Test retrieving tool sources by tool ID."""
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]

        unique_id = "tool_by_id_test_unit"
        test_hash = f"hash_for_{unique_id}"

        try:
            tool_source = StoredToolSource(
                hash=test_hash,
                tool_source_class="XmlToolSource",
                raw_source=f'<tool id="{unique_id}" version="1.0"><command>echo</command></tool>',
                tool_id=unique_id,
                tool_version="1.0",
            )
            store.store(tool_source)
            app.model.context.commit()

            sources = store.get_by_tool_id(unique_id)
            assert len(sources) >= 1
            assert any(s.tool_id == unique_id for s in sources)
        finally:
            if store.exists(test_hash):
                store.delete(test_hash)
                app.model.context.commit()

    def test_database_store_count(self):
        """Test counting stored tool sources."""
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        test_hash = "count_test_hash_unit"

        try:
            initial_count = store.count()

            tool_source = StoredToolSource(
                hash=test_hash,
                tool_source_class="XmlToolSource",
                raw_source='<tool id="count_test"><command>echo</command></tool>',
                tool_id="count_test",
                tool_version="1.0",
            )
            store.store(tool_source)
            app.model.context.commit()

            assert store.count() == initial_count + 1

            store.delete(test_hash)
            app.model.context.commit()
            assert store.count() == initial_count
        finally:
            if store.exists(test_hash):
                store.delete(test_hash)
                app.model.context.commit()


class TestDatabaseBackendPathRows:
    """One row per source path — identical content must not swallow paths."""

    def _stored(self, hash, path, raw='<tool id="upload1" version="1.1.7"/>'):
        return StoredToolSource(
            hash=hash,
            tool_source_class="XmlToolSource",
            raw_source=raw,
            tool_id="upload1",
            tool_version="1.1.7",
            source_path=path,
        )

    def test_identical_content_keeps_row_per_source_path(self):
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        twin_hash = "twin_hash_per_path"
        store.store(self._stored(twin_hash, "/galaxy/tools/data_source/upload.xml"))
        store.store(self._stored(twin_hash, "/galaxy/test/functional/tools/upload.xml"))
        app.model.context.commit()

        first = store.get_by_source_path("/galaxy/tools/data_source/upload.xml")
        second = store.get_by_source_path("/galaxy/test/functional/tools/upload.xml")
        assert first is not None and first.hash == twin_hash
        assert second is not None and second.hash == twin_hash

        assert store.delete(twin_hash)
        app.model.context.commit()
        assert store.get_by_source_path("/galaxy/tools/data_source/upload.xml") is None
        assert store.get_by_source_path("/galaxy/test/functional/tools/upload.xml") is None

    def test_changed_content_updates_path_row_in_place(self):
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        path = "/galaxy/tools/edited.xml"
        store.store(self._stored("edited_hash_v1", path, raw="<tool/>"))
        app.model.context.commit()
        store.store(self._stored("edited_hash_v2", path, raw="<tool><description/></tool>"))
        app.model.context.commit()

        row = store.get_by_source_path(path)
        assert row is not None
        assert row.hash == "edited_hash_v2"
        assert not store.exists("edited_hash_v1")
        store.delete("edited_hash_v2")
        app.model.context.commit()

    def test_remove_index_entry_persists_removal(self):
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        index = ToolIndex()
        entry = ToolIndexEntry(id="removable", version="1.0", name="Removable", panel_section_id="sec1")
        index.add_entry(entry)
        index.by_section["sec1"] = ["removable"]
        store.store_index(index)
        app.model.context.commit()

        store.remove_index_entry("removable")
        app.model.context.commit()
        store.invalidate_index_cache()

        reloaded = store.load_index()
        assert reloaded is not None
        assert reloaded.get("removable") is None
        assert "removable" not in reloaded.by_section.get("sec1", [])

    def test_pathless_sources_dedupe_on_hash(self):
        app = MockApp()
        store = DatabaseToolSourceStore(app.model.context)  # type: ignore[arg-type]
        store.store(self._stored("pathless_hash", None))
        store.store(self._stored("pathless_hash", None))
        app.model.context.commit()
        assert store.exists("pathless_hash")
        assert store.delete("pathless_hash")
        app.model.context.commit()
        assert not store.exists("pathless_hash")


class TestSqlAlchemyBackend:
    """Tests for the sqlalchemy/sqlite backend."""

    def test_sqlalchemy_store_basic_operations(self, tmp_path):
        store = SqlAlchemyToolSourceStore(path=str(tmp_path / "ts.sqlite"))

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
        store = SqlAlchemyToolSourceStore(path=str(tmp_path / "twins.sqlite"))
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

    def test_sqlalchemy_store_persistence(self, tmp_path):
        path = str(tmp_path / "ts.sqlite")
        store1 = SqlAlchemyToolSourceStore(path=path)
        store1.store(
            StoredToolSource(
                hash="persist_test_hash",
                tool_source_class="XmlToolSource",
                raw_source='<tool id="persist"><command>echo</command></tool>',
                tool_id="persist_tool",
                tool_version="1.0",
            )
        )
        store2 = SqlAlchemyToolSourceStore(path=path)
        assert store2.exists("persist_test_hash")
        retrieved = store2.get("persist_test_hash")
        assert retrieved is not None
        assert retrieved.tool_id == "persist_tool"


class TestBuildToolSourceStore:
    """Tests for the store factory function."""

    def test_build_database_store(self):
        app = MockApp()
        store = build_tool_source_store(app.config, app.model.context)  # type: ignore[arg-type]
        assert isinstance(store, DatabaseToolSourceStore)

    def test_build_sqlalchemy_store(self, tmp_path):
        config = FakeConfig(
            tool_source_store="sqlalchemy",
            tool_source_disk_path=str(tmp_path / "ts.sqlite"),
            tool_configs=[],
            tool_source_stores=None,
            use_lazy_toolbox=False,
        )
        store = build_tool_source_store(config, None)  # type: ignore[arg-type]
        assert isinstance(store, SqlAlchemyToolSourceStore)

    def test_build_sqlalchemy_store_missing_path_raises(self):
        config = FakeConfig(
            tool_source_store="sqlalchemy",
            tool_source_disk_path=None,
            tool_configs=[],
            tool_source_stores=None,
            use_lazy_toolbox=False,
        )
        with pytest.raises(ConfigurationError):
            build_tool_source_store(config, None)  # type: ignore[arg-type]

    def test_build_unknown_backend_raises(self):
        config = FakeConfig(
            tool_source_store="not-a-backend",
            tool_source_disk_path=None,
            tool_configs=[],
            tool_source_stores=None,
            use_lazy_toolbox=False,
        )
        with pytest.raises(ConfigurationError):
            build_tool_source_store(config, None)  # type: ignore[arg-type]


class TestPerConfStoreRouting:
    """Tests for per-conf store routing in build_tool_source_store."""

    def _config(self, tmp_path, **overrides):
        defaults = dict(
            tool_source_store="sqlalchemy",
            tool_source_disk_path=str(tmp_path / "ts.sqlite"),
            tool_configs=[],
            tool_source_stores={},
            use_lazy_toolbox=False,
        )
        defaults.update(overrides)
        return FakeConfig(**defaults)

    def test_lazy_off_ignores_unknown_per_conf_store(self, tmp_path, caplog):
        conf = tmp_path / "extra_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox store="missing_alias"/>\n')
        config = self._config(tmp_path, tool_configs=[str(conf)])
        with caplog.at_level("INFO", logger="galaxy.tool_source_store"):
            store = build_tool_source_store(config, None)
        from galaxy.tool_source_store.composite import CompositeToolSourceStore

        assert isinstance(store, SqlAlchemyToolSourceStore)
        assert not isinstance(store, CompositeToolSourceStore)
        assert any("missing_alias" in rec.message for rec in caplog.records)

    def test_lazy_unset_also_ignores_per_conf_store(self, tmp_path):
        conf = tmp_path / "extra_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox store="anything"/>\n')
        config = self._config(tmp_path, tool_configs=[str(conf)], use_lazy_toolbox=None)
        store = build_tool_source_store(config, None)
        assert isinstance(store, SqlAlchemyToolSourceStore)

    def test_lazy_on_with_unknown_store_still_raises(self, tmp_path):
        conf = tmp_path / "extra_tool_conf.xml"
        conf.write_text('<?xml version="1.0"?>\n<toolbox store="missing_alias"/>\n')
        config = self._config(tmp_path, tool_configs=[str(conf)], use_lazy_toolbox=True)
        with pytest.raises(ConfigurationError):
            build_tool_source_store(config, None)


class TestToolIndex:
    """Tests for ToolIndex functionality."""

    def test_index_search(self):
        """Test searching the tool index."""
        index = ToolIndex()
        index.entries["filter_tool"] = ToolIndexEntry(
            id="filter_tool",
            name="Filter Tool",
            version="1.0",
            description="Filters data by column",
        )
        index.entries["cat_tool"] = ToolIndexEntry(
            id="cat_tool",
            name="Concatenate",
            version="2.0",
            description="Concatenates files",
        )

        results = index.search("Filter", limit=10)
        assert len(results) >= 1
        assert any(r.id == "filter_tool" for r in results)

        results = index.search("column", limit=10)
        assert len(results) >= 1
        assert any(r.id == "filter_tool" for r in results)

    def test_index_serialization(self):
        """Test index to_dict/from_dict round trip."""
        index = ToolIndex()
        index.entries["test_tool"] = ToolIndexEntry(
            id="test_tool",
            name="Test",
            version="1.0",
            description="Test tool",
            labels=["genomics"],
        )
        index.by_section["section1"] = ["test_tool"]

        data = index.to_dict()

        restored = ToolIndex.from_dict(data)

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
