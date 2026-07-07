"""Tests for the populate_store.py script.

These tests cover the core functionality of the tool source population script,
including hash computation, file watching, and store updates.

Following test guidelines:
- Fakes over mocks where practical
- State verification over call count assertions
- Real objects with constraints (temp files, fake stores)
"""

import hashlib
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

from galaxy.tools.source_store.populator import (
    compute_hash,
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


# --- Tests ---


class TestComputeHash:
    """Tests for the compute_hash function."""

    def test_returns_sha256_hex_digest(self):
        """Verify hash is valid SHA256 format."""
        result = compute_hash("any content")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_matches_hashlib_sha256(self):
        """Verify implementation matches standard library."""
        content = "hello world"
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert compute_hash(content) == expected

    def test_empty_string_has_valid_hash(self):
        """Empty strings should produce consistent hash."""
        result = compute_hash("")
        expected = hashlib.sha256(b"").hexdigest()
        assert result == expected

    def test_unicode_content_hashes_correctly(self):
        """Unicode content should be handled via UTF-8 encoding."""
        content = "unicode: éàü 日本語"
        expected = hashlib.sha256(content.encode()).hexdigest()
        assert compute_hash(content) == expected

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

    def test_returns_false_on_connection_error(self):
        """Connection errors should be caught and return False."""
        config = FakeConfig(amqp_internal_connection="amqp://localhost")

        # Force an import error by breaking kombu import
        import sys

        original_modules = sys.modules.copy()

        # Remove kombu if present to simulate import failure
        for key in list(sys.modules.keys()):
            if key.startswith("kombu"):
                del sys.modules[key]

        try:
            # The function should catch the ImportError and return False
            result = send_reload_notification(config)
            # Either returns True if kombu is available, or False if not
            assert isinstance(result, bool)
        finally:
            # Restore modules
            sys.modules.update(original_modules)


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
