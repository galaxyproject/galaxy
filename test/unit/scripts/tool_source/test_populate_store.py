"""Tests for the populate_store.py script.

These tests cover the core functionality of the tool source population script,
including hash computation, file watching, and store updates.

Following test guidelines:
- Fakes over mocks where practical
- State verification over call count assertions
- Real objects with constraints (temp files, fake stores)
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
)

# Add Galaxy lib to path for imports
galaxy_root = Path(__file__).parent.parent.parent.parent.parent
import sys

sys.path.insert(0, str(galaxy_root / "lib"))

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

        def all_tool_config_files(self):
            return [str(conf)]

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
            rebuild_whoosh=False,
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
            rebuild_whoosh=False,
        )
        assert result["unchanged"] == 1
        store.invalidate_index_cache()
        index = store.load_index()
        assert index is not None
        entry = index.entries[guid]
        assert entry.in_panel is True
        assert entry.panel_section_id == "test_section_multi"
        assert [(item.tool_id, item.section_id) for item in index.panel_items] == [(guid, "test_section_multi")]

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
    its panel section in the whoosh corpus) between runs, defeating the
    whoosh corpus-signature rebuild skip.
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
