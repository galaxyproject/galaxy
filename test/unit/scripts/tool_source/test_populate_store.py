"""Tests for the populate_store.py script.

These tests cover the core functionality of the tool source population script,
including hash computation, file watching, and store updates.

Following test guidelines:
- Fakes over mocks where practical
- State verification over call count assertions
- Real objects with constraints (temp files, fake stores)
"""

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
)

# Add Galaxy lib to path for imports
galaxy_root = Path(__file__).parent.parent.parent.parent.parent
import sys

sys.path.insert(0, str(galaxy_root / "lib"))

from galaxy.tools.source_store import build_tool_source_store
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

    def test_process_tool_file_ignores_non_tool_xml(self):
        """XML files without <tool> tag should be ignored."""
        store = FakeToolSourceStore()
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write("<data>not a tool</data>")
            temp_path = f.name

        try:
            result = watcher._process_tool_file(temp_path)
            assert result is False
            assert store.count == 0
        finally:
            os.unlink(temp_path)

    def test_process_tool_file_populates_changed_tool(self):
        calls: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
            populate_callable=_recording_populate(calls),
        )

        tool_content = """<tool id="test_tool" name="Test" version="1.0">
            <command>echo hello</command>
        </tool>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(tool_content)
            temp_path = f.name

        try:
            result = watcher._process_tool_file(temp_path)
            assert result is True
            assert len(calls) == 1
            assert calls[0]["paths"] == [temp_path]
        finally:
            os.unlink(temp_path)

    def test_process_tool_file_skips_unchanged_tool(self):
        """Tool already in store with same hash should be skipped."""
        store = FakeToolSourceStore()

        tool_content = """<tool id="test_tool" name="Test" version="1.0">
            <command>echo hello</command>
        </tool>"""
        content_hash = compute_hash(tool_content)

        # Pre-populate store with this hash
        store.stored_sources[content_hash] = "already stored"

        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(tool_content)
            temp_path = f.name

        try:
            result = watcher._process_tool_file(temp_path)

            assert result is False
            # Store count unchanged (still just the pre-populated one)
            assert store.count == 1
            # No new store calls
            assert len(store.store_calls) == 0
        finally:
            os.unlink(temp_path)

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

        tool_path = tmp_path / "sometool.xml"
        tool_path.write_text('<tool id="t" name="T" version="1.0"><command>echo</command></tool>')
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

    def test_on_change_notifies_on_update(self):
        """A changed tool file re-populates and fires one notification."""
        notification_sent: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=FakeToolSourceStore(),
            tools_dirs=[],
            notify_callable=_recording_notify(notification_sent),
            populate_callable=_recording_populate([]),
        )

        tool_content = """<tool id="test" version="1.0">
            <command>echo</command>
        </tool>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(tool_content)
            temp_path = f.name

        try:
            watcher._on_change(temp_path)
            assert len(notification_sent) == 1
        finally:
            os.unlink(temp_path)

    def test_on_change_no_notification_when_unchanged(self):
        """No notification fires when the tool is already stored."""
        store = FakeToolSourceStore()

        tool_content = """<tool id="test" version="1.0">
            <command>echo</command>
        </tool>"""
        store.stored_sources[compute_hash(tool_content)] = "exists"

        notification_sent: list = []
        watcher = ToolFileWatcher(
            config=FakeConfig(),
            store=store,
            tools_dirs=[],
            notify_callable=_recording_notify(notification_sent),
        )

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(tool_content)
            temp_path = f.name

        try:
            watcher._on_change(temp_path)
            assert len(store.store_calls) == 0
            assert len(notification_sent) == 0
        finally:
            os.unlink(temp_path)


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


class TestIncrementalFastPath:
    """A second populate carries byte-identical tools forward without re-parsing."""

    def test_unchanged_tools_carried_forward(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        for i in (1, 2):
            (tools_dir / f"itest_{i}.xml").write_text(
                f'<tool id="itest_{i}" name="ITest {i}" version="1.0" profile="21.09"><command>echo</command></tool>'
            )
        conf = tmp_path / "tool_conf.xml"
        conf.write_text(
            f'<toolbox tool_path="{tools_dir}"><tool file="itest_1.xml"/><tool file="itest_2.xml"/></toolbox>'
        )
        cfg = _populate_config(tmp_path, conf)

        r1 = populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="itest_", incremental=True)
        assert (r1["stored"], r1["unchanged"]) == (2, 0)

        # Nothing changed on disk: the second run skips the parse and store
        # write, carrying both index entries forward.
        r2 = populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="itest_", incremental=True)
        assert (r2["stored"], r2["unchanged"]) == (0, 2)

    def test_manifest_is_opt_in_for_cli_callers(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "manifest_tool.xml").write_text(
            '<tool id="manifest_tool" name="Manifest" version="1.0" profile="21.09"><command>echo</command></tool>'
        )
        conf = tmp_path / "tool_conf.xml"
        conf.write_text(f'<toolbox tool_path="{tools_dir}"><tool file="manifest_tool.xml"/></toolbox>')
        cfg = _populate_config(tmp_path, conf)
        sidecar = tmp_path / "ts.sqlite.manifest.json"

        populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="manifest_tool")
        assert not sidecar.exists()

        populate_store_inline(
            cfg,
            target=DEFAULT_STORE_NAME,
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
        tools_dir.mkdir()
        for suffix in ("a", "b"):
            (tools_dir / f"twin_{suffix}.xml").write_text(
                f'<tool id="twin" name="Twin" version="1.0" profile="21.09"><command>echo {suffix}</command></tool>'
            )
        conf = tmp_path / "tool_conf.xml"
        conf.write_text(
            f'<toolbox tool_path="{tools_dir}">'
            '<section id="sec_a" name="A"><tool file="twin_a.xml"/></section>'
            '<section id="sec_b" name="B"><tool file="twin_b.xml"/></section>'
            "</toolbox>"
        )
        cfg = _populate_config(tmp_path, conf)

        # Run 2 is the interesting one: the run-1 winner (sec_b) comes back
        # via the unchanged fast path while its twin re-parses — the winner
        # must still be decided by document order, not by which path parsed.
        for run in (1, 2, 3):
            populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="twin_", incremental=True, parallel=4)
            index = build_tool_source_store(cfg).load_index()
            assert index is not None
            assert index.entries["twin"].panel_section_id == "sec_b", f"wrong twin won on run {run}"


class TestFreshnessStamping:
    """Populate stamps the default store's tool_confs token; boot trusts it."""

    def test_populate_stamps_token_and_conf_edit_invalidates(self, tmp_path):
        tools_dir = tmp_path / "tools"
        tools_dir.mkdir()
        (tools_dir / "ftest_1.xml").write_text(
            '<tool id="ftest_1" name="FTest" version="1.0" profile="21.09"><command>echo</command></tool>'
        )
        conf = tmp_path / "tool_conf.xml"
        conf.write_text(f'<toolbox tool_path="{tools_dir}"><tool file="ftest_1.xml"/></toolbox>')
        cfg = _populate_config(tmp_path, conf)

        populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="ftest_", incremental=True)

        store = _build_default_store(cfg)
        index = store.load_index()
        assert index is not None
        assert index.freshness_token == tool_confs_token(cfg)
        assert store.index_is_fresh() is True

        (tools_dir / "ftest_2.xml").write_text(
            '<tool id="ftest_2" name="FTest 2" version="1.0" profile="21.09"><command>echo</command></tool>'
        )
        conf.write_text(
            f'<toolbox tool_path="{tools_dir}"><tool file="ftest_1.xml"/><tool file="ftest_2.xml"/></toolbox>'
        )
        assert store.index_is_fresh() is False

        populate_store_inline(cfg, target=DEFAULT_STORE_NAME, pattern="ftest_", incremental=True)
        store.invalidate_index_cache()
        assert store.index_is_fresh() is True
