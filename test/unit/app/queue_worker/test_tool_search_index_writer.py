"""Only the elected config watcher writes the shared tool search index."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from galaxy.app import (
    GalaxyManagerApplication,
    UniverseApplication,
)
from galaxy.queue_worker import (
    rebuild_toolbox_search_index,
    reload_tool_source_cache,
)
from galaxy.tools.cached_toolbox import CachedToolBox

WRITER_CASES = [
    # (is_webapp, is_config_watcher, writes)
    (True, True, True),
    (True, False, False),
    (False, False, False),
]


class _SearchIndexApp:
    reindex_tool_search = GalaxyManagerApplication.reindex_tool_search
    ensure_tool_search_index = GalaxyManagerApplication.ensure_tool_search_index
    writes_tool_search_index = UniverseApplication.writes_tool_search_index

    def __init__(self, is_webapp: bool, is_config_watcher: bool) -> None:
        self.is_webapp = is_webapp
        self.database_heartbeat = SimpleNamespace(is_config_watcher=is_config_watcher)
        self.toolbox = MagicMock(spec=CachedToolBox)
        self.toolbox_or_none = self.toolbox
        self.toolbox_search = MagicMock()
        self.tool_cache = MagicMock()
        self.tool_source_store = None
        self.config = SimpleNamespace(index_tool_help=True, server_name="test")


@pytest.mark.parametrize(("is_webapp", "is_config_watcher", "writes"), WRITER_CASES)
def test_reload_tool_source_cache_reindexes_only_on_config_watcher(is_webapp, is_config_watcher, writes):
    app = _SearchIndexApp(is_webapp, is_config_watcher)
    reload_tool_source_cache(app)
    app.toolbox.invalidate_index_cache.assert_called_once_with()
    assert app.toolbox_search.build_index.called is writes


@pytest.mark.parametrize(("is_webapp", "is_config_watcher", "writes"), WRITER_CASES)
def test_rebuild_toolbox_search_index_builds_only_on_config_watcher(is_webapp, is_config_watcher, writes):
    app = _SearchIndexApp(is_webapp, is_config_watcher)
    rebuild_toolbox_search_index(app)
    assert app.toolbox_search.build_index_if_stale.called is writes


def test_reindex_tool_search_is_skipped_off_the_config_watcher():
    # remove_tool_by_id reindexes in whichever process served the uninstall;
    # its reload broadcast reaches the watcher, which does the write.
    app = _SearchIndexApp(is_webapp=True, is_config_watcher=False)
    app.reindex_tool_search()
    app.toolbox_search.build_index.assert_not_called()
