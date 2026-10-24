"""Tests for the populate_store.py script.

These tests cover the core functionality of the tool source population script,
including hash computation, file watching, and store updates.

Following test guidelines:
- Fakes over mocks where practical
- State verification over call count assertions
- Real objects with constraints (temp files, fake stores)
"""

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import (
    Any,
)

# Add Galaxy lib to path for imports
galaxy_root = Path(__file__).parent.parent.parent.parent.parent
import sys

sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.config import GalaxyAppConfiguration
from galaxy.tools.source_store import populator
from galaxy.tools.source_store.discover import discover_tools as actual_discover_tools
from galaxy.tools.source_store.factory import _build_default_store
from galaxy.tools.source_store.freshness import tool_confs_token
from galaxy.tools.source_store.populator import (
    compute_hash,
    DEFAULT_STORE_NAME,
    populate_store_inline,
    send_reload_notification,
    ToolFileWatcher,
)

# --- Fakes for testing ---


class FakeToolSourceStore:
    """In-memory fake implementation of a tool source store."""

    def __init__(self):
        self.stored_sources: dict[str, Any] = {}
        self.store_calls: list[Any] = []

    def exists(self, hash_key: str) -> bool:
        return hash_key in self.stored_sources

    def store(self, source) -> None:
        self.stored_sources[source.hash] = source
        self.store_calls.append(source)

    def get(self, hash_key: str) -> Any | None:
        return self.stored_sources.get(hash_key)

    @property
    def count(self) -> int:
        return len(self.stored_sources)


@dataclass
class FakeTool:
    """Minimal tool representation for testing iter_tool_sources."""

    version: str
    tool_source: object = None
    tool_dir: str = "/fake/path"


class FakeToolbox:
    """Minimal toolbox representation for testing."""

    def __init__(self, tools: dict[str, FakeTool]):
        self._tools_by_id = tools


@dataclass
class FakeConfig:
    """Minimal config for testing."""

    amqp_internal_connection: str | None = None
    database_connection: str = "sqlite:///:memory:"


def _tool_xml(tool_id: str, *, name: str | None = None, version: str = "1.0", command: str = "echo") -> str:
    return (
        f'<tool id="{tool_id}" name="{name or tool_id}" version="{version}" profile="21.09">'
        f"<command>{command}</command></tool>"
    )


def _write_tool(path: Path, tool_id: str, **kwds: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_tool_xml(tool_id, **kwds))
    return path


def _write_tool_conf(path: Path, tools_dir: Path, items: str = "") -> Path:
    path.write_text(f'<toolbox tool_path="{tools_dir}">{items}</toolbox>')
    return path


# --- Tests ---


class TestComputeHash:
    """Tests for the compute_hash function."""

    def test_returns_sha256_hex_digest(self):
        """Verify hash is valid SHA256 format."""
        result = compute_hash("any content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_for_same_input(self):
        """Same input always produces same output."""
        content = "test content"
        assert compute_hash(content) == compute_hash(content)

    def test_different_inputs_produce_different_hashes(self):
        """Different content should produce different hashes."""
        assert compute_hash("content one") != compute_hash("content two")


class TestSendReloadNotification:
    """Tests for the send_reload_notification function."""

    def test_returns_false_when_no_amqp_url_configured(self):
        """Without AMQP URL, notification should fail gracefully."""
        config = FakeConfig(amqp_internal_connection=None)
        result = send_reload_notification(config)
        assert result is False


def _recording_notify(sink: list):
    """Build a fake notify callable that records every invocation in ``sink``.

    A plain lambda doesn't work here because ``list.append`` returns ``None``,
    which mypy's ``func-returns-value`` check rejects.
    """

    def notify(config: Any) -> bool:
        sink.append(config)
        return True

    return notify


def _recording_populate(sink: list):
    """Fake populate callable that records each call's kwargs in ``sink``."""

    def populate(config: Any, **kwargs: Any) -> dict:
        sink.append(kwargs)
        return {}

    return populate


class TestToolFileWatcher:
    """Tests for the ToolFileWatcher class."""

    def test_initialization_stores_config(self):
        """Watcher should store configuration parameters."""
        config = FakeConfig()
        store = FakeToolSourceStore()
        tools_dirs = [Path("/tmp/tools")]

        watcher = ToolFileWatcher(
            config=config,
            store=store,
            tools_dirs=tools_dirs,
            verbose=True,
        )

        assert watcher.config is config
        assert watcher.store is store
        assert watcher.tools_dirs == tools_dirs
        assert watcher.verbose is True

    def test_process_tool_file_ignores_non_tool_xml(self, tmp_path):
        """XML files without <tool> tag should be ignored."""
        store = FakeToolSourceStore()
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
        )

        path = tmp_path / "not_a_tool.xml"
        path.write_text("<data>not a tool</data>")

        result = watcher._process_tool_file(str(path))

        assert result is False
        assert store.count == 0

    def test_process_tool_file_populates_changed_tool(self, tmp_path):
        calls: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
            populate_callable=_recording_populate(calls),
        )

        path = _write_tool(tmp_path / "test_tool.xml", "test_tool", name="Test", command="echo hello")

        result = watcher._process_tool_file(str(path))

        assert result is True
        assert len(calls) == 1
        assert calls[0]["paths"] == [str(path)]

    def test_process_tool_file_skips_unchanged_tool(self, tmp_path):
        """Tool already in store with same hash should be skipped."""
        store = FakeToolSourceStore()

        tool_content = _tool_xml("test_tool", name="Test", command="echo hello")
        content_hash = compute_hash(tool_content)

        # Pre-populate store with this hash
        store.stored_sources[content_hash] = "already stored"

        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
        )

        path = tmp_path / "test_tool.xml"
        path.write_text(tool_content)

        result = watcher._process_tool_file(str(path))

        assert result is False
        assert store.count == 1
        assert len(store.store_calls) == 0

    def test_process_tool_file_macro_repopulates_siblings(self, tmp_path):
        # A changed macros file re-expands the sibling tools that import it,
        # excluding the macro file itself.
        calls: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
            populate_callable=_recording_populate(calls),
        )

        tool_path = _write_tool(tmp_path / "sometool.xml", "t", name="T")
        macro_path = tmp_path / "macros.xml"
        macro_path.write_text('<macros><token name="@X@">1</token></macros>')

        result = watcher._process_tool_file(str(macro_path))

        assert result is True
        assert len(calls) == 1
        assert str(tool_path) in calls[0]["paths"]
        assert str(macro_path) not in calls[0]["paths"]

    def test_shutdown_sets_event(self):
        """Shutdown should signal the shutdown event."""
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
        )

        watcher.shutdown()

        assert watcher._shutdown_event.is_set()

    def test_on_change_notifies_on_update(self, tmp_path):
        """A changed tool file re-populates and fires one notification."""
        notification_sent: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
            notify_callable=_recording_notify(notification_sent),
            populate_callable=_recording_populate([]),
        )

        path = _write_tool(tmp_path / "test.xml", "test")

        watcher._on_change(str(path))

        assert len(notification_sent) == 1

    def test_on_change_no_notification_when_unchanged(self, tmp_path):
        """No notification fires when the tool is already stored."""
        store = FakeToolSourceStore()

        tool_content = _tool_xml("test")
        store.stored_sources[compute_hash(tool_content)] = "exists"

        notification_sent: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
            notify_callable=_recording_notify(notification_sent),
        )

        path = tmp_path / "test.xml"
        path.write_text(tool_content)

        watcher._on_change(str(path))

        assert len(store.store_calls) == 0
        assert len(notification_sent) == 0


def _populate_config(tmp_path, conf):
    class _Cfg:
        enable_beta_tool_formats = False
        tool_source_stores: dict = {}
        tool_search_index_dir = None
        root = str(tmp_path)
        tool_path = str(tmp_path)
        tool_source_database_connection = f"sqlite:///{tmp_path}/ts.sqlite"
        data_manager_config_file: str | None = None
        shed_data_manager_config_file: str | None = None
        biotools_content_directory = None
        biotools_use_api = False
        biotools_service_cache_type = "memory"
        biotools_service_cache_data_dir = None
        biotools_service_cache_lock_dir = None
        biotools_service_cache_url = None
        biotools_service_cache_table_name = None
        biotools_service_cache_schema_name = None
        # Lets a populate that writes the default store build an empty
        # datatypes registry for converter discovery.
        datatypes_config: list[str] = []

        def all_tool_config_files(self):
            return [str(conf)]

        def get(self, key, default=None):
            return getattr(self, key, default)

    return _Cfg()


def _populate_default(config: Any, **kwds: Any) -> dict[str, int]:
    return populate_store_inline(config, target=DEFAULT_STORE_NAME, **kwds)


def _load_default_index(config: Any):
    store = _build_default_store(config)
    index = store.load_index()
    assert index is not None
    return store, index


class TestIncrementalFastPath:
    """A second populate carries byte-identical tools forward without re-parsing."""

    def test_unchanged_tools_carried_forward(self, tmp_path):
        tools_dir = tmp_path / "tools"
        for i in (1, 2):
            _write_tool(tools_dir / f"itest_{i}.xml", f"itest_{i}", name=f"ITest {i}")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<tool file="itest_1.xml"/><tool file="itest_2.xml"/>',
        )
        cfg = _populate_config(tmp_path, conf)

        r1 = _populate_default(cfg, pattern="itest_", incremental=True)
        assert (r1["stored"], r1["unchanged"]) == (2, 0)

        # Nothing changed on disk: the second run skips the parse and store
        # write, carrying both index entries forward.
        r2 = _populate_default(cfg, pattern="itest_", incremental=True)
        assert (r2["stored"], r2["unchanged"]) == (0, 2)

    def test_adhoc_shed_tool_becomes_panel_tool_when_conf_catches_up(self, tmp_path):
        tools_dir = tmp_path / "shed_tools"
        tool_path = _write_tool(tools_dir / "fastp.xml", "fastp", version="0.20.1+galaxy0")
        conf = _write_tool_conf(tmp_path / "shed_tool_conf.xml", tools_dir)
        cfg = _populate_config(tmp_path, conf)
        guid = "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.20.1+galaxy0"

        _populate_default(
            cfg,
            paths=[str(tool_path)],
            path_guids={str(tool_path): guid},
            incremental=True,
        )
        store, index = _load_default_index(cfg)
        entry = index.entries[guid]
        assert entry.in_panel is False

        _write_tool_conf(
            conf,
            tools_dir,
            '<section id="test_section_multi" name="Test Section with Multiple Versions">'
            f'<tool file="{tool_path.name}" guid="{guid}">'
            "<tool_shed>toolshed.g2.bx.psu.edu</tool_shed>"
            "<repository_name>fastp</repository_name>"
            "<repository_owner>iuc</repository_owner>"
            "<installed_changeset_revision>dbf9c561ef29</installed_changeset_revision>"
            "</tool></section>",
        )

        result = _populate_default(
            cfg,
            pattern="fastp.xml",
            incremental=True,
        )
        assert result["unchanged"] == 1
        store.invalidate_index_cache()
        index = store.load_index()
        assert index is not None
        entry = index.entries[guid]
        assert entry.in_panel is True
        assert entry.panel_section_id == "test_section_multi"
        assert [(item.tool_id, item.section_id) for item in index.panel_items] == [(guid, "test_section_multi")]

    def test_adhoc_shed_update_replaces_configured_entry_before_conf_catches_up(self, tmp_path):
        # A shed update indexes the new revision ad hoc while the conf still
        # names the old one, whose directory the update may already have moved.
        guid = "toolshed.g2.bx.psu.edu/repos/iuc/fastp/fastp/0.20.1+galaxy0"
        old_tool = _write_tool(tmp_path / "shed_tools" / "rev1" / "fastp.xml", "fastp", version="0.20.1+galaxy0")
        conf = _write_tool_conf(
            tmp_path / "shed_tool_conf.xml",
            old_tool.parent,
            f'<section id="s" name="S"><tool file="{old_tool.name}" guid="{guid}">'
            "<tool_shed>toolshed.g2.bx.psu.edu</tool_shed>"
            "<repository_name>fastp</repository_name>"
            "<repository_owner>iuc</repository_owner>"
            "<installed_changeset_revision>rev1</installed_changeset_revision>"
            "</tool></section>",
        )
        cfg = _populate_config(tmp_path, conf)
        _populate_default(cfg)
        new_tool = _write_tool(tmp_path / "shed_tools" / "rev2" / "fastp.xml", "fastp", version="0.20.1+galaxy0")

        _populate_default(cfg, paths=[str(new_tool)], path_guids={str(new_tool): guid}, incremental=True)

        _, index = _load_default_index(cfg)
        assert index.get(guid, "0.20.1+galaxy0").source_path == str(new_tool)
        assert index.entries[guid].source_path == str(new_tool)
        assert [(item.tool_id, item.section_id) for item in index.panel_items] == [(guid, "s")]

    def test_partial_populate_discovers_only_requested_paths(self, tmp_path, monkeypatch):
        tools_dir = tmp_path / "shed_tools"
        items = []
        for i in range(30):
            _write_tool(tools_dir / f"shed_{i}.xml", f"shed_{i}")
            items.append(f'<tool file="shed_{i}.xml" guid="toolshed.example.org/repos/iuc/shed_{i}/shed_{i}/1.0"/>')
        conf = _write_tool_conf(
            tmp_path / "shed_tool_conf.xml",
            tools_dir,
            f'<section id="shed_section" name="Shed Section">{"".join(items)}</section>',
        )
        cfg = _populate_config(tmp_path, conf)
        requested = str(tools_dir / "shed_7.xml")

        discovered_paths: list[str] = []

        def recording_discover_tools(*args, **kwargs):
            for discovered in actual_discover_tools(*args, **kwargs):
                discovered_paths.append(discovered.path)
                yield discovered

        monkeypatch.setattr(populator, "discover_tools", recording_discover_tools)

        _populate_default(cfg, paths=[requested])

        assert discovered_paths == [requested]
        _, index = _load_default_index(cfg)
        entry = index.entries["toolshed.example.org/repos/iuc/shed_7/shed_7/1.0"]
        assert entry.panel_section_id == "shed_section"

    def test_partial_populate_writes_index_only_when_an_entry_changed(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tool = _write_tool(tools_dir / "rescan.xml", "rescan")
        conf = _write_tool_conf(tmp_path / "tool_conf.xml", tools_dir, '<tool file="rescan.xml"/>')
        cfg = _populate_config(tmp_path, conf)
        _populate_default(cfg)

        assert _populate_default(cfg, paths=[str(tool)], incremental=False)["indexes_written"] == 0

        _write_tool(tool, "rescan", command="echo changed")
        assert _populate_default(cfg, paths=[str(tool)], incremental=False)["indexes_written"] == 1

    def test_partial_populate_picks_up_macro_only_change(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        tool = tools_dir / "macro_tool.xml"
        tool.write_text(
            '<tool id="macro_tool" name="Macro" version="@TOOL_VERSION@" profile="21.09">'
            "<macros><import>macros.xml</import></macros><command>echo</command></tool>"
        )
        macros = tools_dir / "macros.xml"
        macros.write_text('<macros><token name="@TOOL_VERSION@">1.0</token></macros>')
        conf = _write_tool_conf(tmp_path / "tool_conf.xml", tools_dir, '<tool file="macro_tool.xml"/>')
        cfg = _populate_config(tmp_path, conf)
        _populate_default(cfg)

        macros.write_text('<macros><token name="@TOOL_VERSION@">2.0</token></macros>')
        _populate_default(cfg, paths=[str(tool)], incremental=False)

        _, index = _load_default_index(cfg)
        assert index.entries["macro_tool"].version == "2.0"

    def test_partial_populate_drops_version_an_edited_file_no_longer_defines(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tool = _write_tool(tools_dir / "probe.xml", "probe", version="1.1")
        _write_tool(tools_dir / "other.xml", "other")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<section id="s" name="S"><tool file="probe.xml"/><tool file="other.xml"/></section>',
        )
        cfg = _populate_config(tmp_path, conf)
        _populate_default(cfg)

        _write_tool(tool, "probe", version="1.2")
        assert _populate_default(cfg, paths=[str(tool)], incremental=False)["indexes_written"] == 1

        _, index = _load_default_index(cfg)
        assert set(index.entries_by_version["probe"]) == {"1.2"}
        assert index.entries["probe"].version == "1.2"
        # The bump keeps the tool's place instead of moving it to the section head.
        assert [item.tool_id for item in index.panel_items] == ["probe", "other"]

    def test_in_process_population_is_atomic_with_tool_removal(self, tmp_path, monkeypatch):
        """A stale scan must commit before a concurrent uninstall can prune it."""
        tools_dir = tmp_path / "tools"
        _write_tool(tools_dir / "keep.xml", "keep")
        _write_tool(tools_dir / "doomed.xml", "doomed")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<tool file="keep.xml"/><tool file="doomed.xml"/>',
        )
        cfg = _populate_config(tmp_path, conf)
        _populate_default(cfg)

        scan_complete = threading.Event()
        allow_commit = threading.Event()

        def pause_after_discovery(*args, **kwargs):
            discovered = list(actual_discover_tools(*args, **kwargs))
            scan_complete.set()
            if not allow_commit.wait(timeout=5):
                raise TimeoutError("test did not release the paused population")
            return iter(discovered)

        monkeypatch.setattr(populator, "discover_tools", pause_after_discovery)
        app = SimpleNamespace(_toolbox_lock=threading.RLock())
        errors: list[Exception] = []

        def populate_from_stale_scan():
            try:
                _populate_default(cfg, app=app, incremental=False)
            except Exception as exc:
                errors.append(exc)

        population = threading.Thread(target=populate_from_stale_scan)
        population.start()
        assert scan_complete.wait(timeout=5)

        # With no population lock this succeeds: uninstall prunes the index,
        # then the paused stale scan writes ``doomed`` straight back.
        acquired_during_population = app._toolbox_lock.acquire(blocking=False)
        if acquired_during_population:
            _write_tool_conf(conf, tools_dir, '<tool file="keep.xml"/>')
            _build_default_store(cfg).remove_index_entry("doomed")
            app._toolbox_lock.release()

        allow_commit.set()
        population.join(timeout=10)
        assert not population.is_alive()
        assert not errors

        if not acquired_during_population:
            with app._toolbox_lock:
                _write_tool_conf(conf, tools_dir, '<tool file="keep.xml"/>')
                _build_default_store(cfg).remove_index_entry("doomed")

        assert not acquired_during_population
        _, index = _load_default_index(cfg)
        assert "doomed" not in index.entries

    def test_manifest_is_opt_in_for_cli_callers(self, tmp_path):
        tools_dir = tmp_path / "tools"
        _write_tool(tools_dir / "manifest_tool.xml", "manifest_tool", name="Manifest")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<tool file="manifest_tool.xml"/>',
        )
        cfg = _populate_config(tmp_path, conf)
        sidecar = tmp_path / "ts.sqlite.manifest.json"

        _populate_default(cfg, pattern="manifest_tool")
        assert not sidecar.exists()

        _populate_default(
            cfg,
            pattern="manifest_tool",
            write_manifests=True,
        )
        payload = json.loads(sidecar.read_text())
        assert payload["store"] == DEFAULT_STORE_NAME
        assert payload["tool_snapshot"]["default_tool_count"] == 1


class TestTwinDeterminism:
    """Same-id twins resolve by conf document order, stably across re-runs.

    Regression: the winner among same-id/same-version twins is decided by
    index add-order. Consuming pool results as_completed — or adding
    carried-forward entries before re-parsed ones — flipped the winner (and
    its panel section in the search corpus) between runs even though no input
    changed.
    """

    def test_twin_winner_stable_across_runs(self, tmp_path):
        tools_dir = tmp_path / "tools"
        for suffix in ("a", "b"):
            _write_tool(tools_dir / f"twin_{suffix}.xml", "twin", name="Twin", command=f"echo {suffix}")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<section id="sec_a" name="A"><tool file="twin_a.xml"/></section>'
            '<section id="sec_b" name="B"><tool file="twin_b.xml"/></section>',
        )
        cfg = _populate_config(tmp_path, conf)

        # Run 2 is the interesting one: the run-1 winner (sec_b) comes back
        # via the unchanged fast path while its twin re-parses — the winner
        # must still be decided by document order, not by which path parsed.
        for run in (1, 2, 3):
            _populate_default(cfg, pattern="twin_", incremental=True, parallel=4)
            _, index = _load_default_index(cfg)
            assert index.entries["twin"].panel_section_id == "sec_b", f"wrong twin won on run {run}"


class TestFreshnessStamping:
    """Populate stamps the default store's tool_confs token; boot trusts it."""

    def test_populate_stamps_token_and_conf_edit_invalidates(self, tmp_path):
        tools_dir = tmp_path / "tools"
        _write_tool(tools_dir / "ftest_1.xml", "ftest_1", name="FTest")
        conf = _write_tool_conf(
            tmp_path / "tool_conf.xml",
            tools_dir,
            '<tool file="ftest_1.xml"/>',
        )
        cfg = _populate_config(tmp_path, conf)

        _populate_default(cfg, pattern="ftest_", incremental=True)

        store, index = _load_default_index(cfg)
        assert index.freshness_token == tool_confs_token(cfg)
        assert store.index_is_fresh() is True

        _write_tool(tools_dir / "ftest_2.xml", "ftest_2", name="FTest 2")
        _write_tool_conf(
            conf,
            tools_dir,
            '<tool file="ftest_1.xml"/><tool file="ftest_2.xml"/>',
        )
        assert store.index_is_fresh() is False

        _populate_default(cfg, pattern="ftest_", incremental=True)
        store.invalidate_index_cache()
        assert store.index_is_fresh() is True


class TestToolsMissingFromReadOnlyStore:
    """A conf routed to a read-only store can list tools installed after it was published."""

    def _config(self, tmp_path, shed_conf, read_only):
        return GalaxyAppConfiguration(
            root=str(galaxy_root),
            data_dir=str(tmp_path / "data"),
            override_tempdir=False,
            tool_config_file=str(shed_conf),
            tool_source_database_connection=f"sqlite:///{tmp_path}/default.sqlite",
            tool_source_stores={"published": {"url": f"sqlite:///{tmp_path}/published.sqlite", "read_only": read_only}},
        )

    def _published_conf(self, tmp_path):
        tools_dir = tmp_path / "shed_tools"
        _write_tool(tools_dir / "published.xml", "published")
        installed = _write_tool(tools_dir / "installed.xml", "installed")
        shed_conf = tmp_path / "shed_tool_conf.xml"
        shed_conf.write_text(
            f'<toolbox tool_path="{tools_dir}" store="published">'
            '<section id="shed" name="Shed"><tool file="published.xml"/></section></toolbox>'
        )
        populate_store_inline(self._config(tmp_path, shed_conf, read_only=False), target="published")
        # The install appends the new tool to the conf after the store was published.
        shed_conf.write_text(
            f'<toolbox tool_path="{tools_dir}" store="published"><section id="shed" name="Shed">'
            '<tool file="published.xml"/><tool file="installed.xml"/></section></toolbox>'
        )
        return shed_conf, installed

    def test_partial_populate_indexes_installed_tool_with_its_panel_placement(self, tmp_path):
        shed_conf, installed = self._published_conf(tmp_path)
        config = self._config(tmp_path, shed_conf, read_only=True)

        populate_store_inline(config, paths=[str(installed)])

        _, index = _load_default_index(config)
        entry = index.entries["installed"]
        assert (entry.in_panel, entry.panel_section_id) == (True, "shed")
        assert ("installed", "shed") in [(item.tool_id, item.section_id) for item in index.panel_items]
        assert "published" not in index.entries

    def test_full_populate_keeps_installed_tool(self, tmp_path):
        shed_conf, installed = self._published_conf(tmp_path)
        config = self._config(tmp_path, shed_conf, read_only=True)
        populate_store_inline(config, paths=[str(installed)])

        populate_store_inline(config, prune=True)

        _, index = _load_default_index(config)
        assert index.entries["installed"].in_panel is True
        assert "published" not in index.entries
