import os
import threading

from galaxy.app_unittest_utils.toolbox_support import BaseToolBoxTestCase
from galaxy.config import (
    GALAXY_APP_NAME,
    GALAXY_CONFIG_SCHEMA_PATH,
)
from galaxy.config.schema import AppSchema
from galaxy.tools.search import ToolBoxSearch

SEARCH_OPTIONS = (
    "tool_description_boost",
    "tool_enable_ngram_search",
    "tool_help_bm25f_k1",
    "tool_help_boost",
    "tool_id_boost",
    "tool_label_boost",
    "tool_name_boost",
    "tool_name_exact_multiplier",
    "tool_ngram_factor",
    "tool_ngram_maxsize",
    "tool_ngram_minsize",
    "tool_section_boost",
    "tool_stub_boost",
)


TOOL_ID = "toolbox_search_versioned_tool"


class TestToolBoxSearch(BaseToolBoxTestCase):
    def test_versioned_tool_survives_reindex(self):
        # tool_conf.xml.sample lists the newest revision of a multi-version tool
        # first (filters/grep.xml before filters/grep_1.0.1.xml), so the tool
        # cache ends up pointing the shared id at the *older* revision.
        self._init_tool(filename="tool_v02.xml", version="0.2", tool_id=TOOL_ID)
        self._init_tool(filename="tool_v01.xml", version="0.1", tool_id=TOOL_ID)
        self._add_config("""<toolbox><tool file="tool_v02.xml" /><tool file="tool_v01.xml" /></toolbox>""")

        # ``ToolLineage.lineages_by_id`` is a class attribute that outlives each
        # test, so an id shared with another test would carry that test's
        # versions in here and change which revision counts as the latest.
        tool = self.toolbox.get_tool(TOOL_ID)
        assert tool.tool_versions == ["0.1", "0.2"]
        assert tool.is_latest_version

        search = self._build_search()
        search.build_index(self.app.tool_cache, self.toolbox)
        assert TOOL_ID in search.search("Test Tool", "default", self.app.config)

        # Installs and uninstalls reindex an index that already holds the tool.
        self.app.tool_cache.reset_status()
        search.build_index(self.app.tool_cache, self.toolbox)
        assert TOOL_ID in search.search("Test Tool", "default", self.app.config)

    def test_build_index_commits_before_returning(self):
        self._init_tool(filename="tool_v01.xml", version="0.1", tool_id="toolbox_search_locked_tool")
        self._add_config("""<toolbox><tool file="tool_v01.xml" /></toolbox>""")
        search = self._build_search()
        held_writer = search.panel_searches["default"].index.writer()

        build = threading.Thread(target=search.build_index, args=(self.app.tool_cache, self.toolbox))
        build.start()
        build.join(timeout=1)
        assert build.is_alive()

        held_writer.cancel()
        build.join(timeout=30)
        assert not build.is_alive()
        assert "toolbox_search_locked_tool" in search.search("Test Tool", "default", self.app.config)

    def test_build_index_if_stale_builds_once_per_reload(self):
        self._init_tool(filename="tool_v01.xml", version="0.1", tool_id="toolbox_search_once_tool")
        self._add_config("""<toolbox><tool file="tool_v01.xml" /></toolbox>""")
        search = self._build_search()

        assert search.build_index_if_stale(self.app.tool_cache, self.toolbox)
        assert not search.build_index_if_stale(self.app.tool_cache, self.toolbox)

        self.toolbox._reload_count += 1
        assert search.build_index_if_stale(self.app.tool_cache, self.toolbox)
        assert "toolbox_search_once_tool" in search.search("Test Tool", "default", self.app.config)

    def test_rebuild_without_reload_does_not_cover_next_reload(self):
        self._init_tool(filename="tool_v01.xml", version="0.1", tool_id="toolbox_search_rebuild_tool")
        self._add_config("""<toolbox><tool file="tool_v01.xml" /></toolbox>""")
        search = self._build_search()
        search.build_index_if_stale(self.app.tool_cache, self.toolbox)
        search.build_index(self.app.tool_cache, self.toolbox)

        self.toolbox._reload_count += 1
        assert search.build_index_if_stale(self.app.tool_cache, self.toolbox)

    def test_wait_until_current_returns_once_index_is_built(self):
        self._init_tool(filename="tool_v01.xml", version="0.1", tool_id="toolbox_search_wait_tool")
        self._add_config("""<toolbox><tool file="tool_v01.xml" /></toolbox>""")
        search = self._build_search()
        assert not search.wait_until_current(self.toolbox, timeout=0.1)

        build = threading.Thread(target=search.build_index_if_stale, args=(self.app.tool_cache, self.toolbox))
        build.start()
        assert search.wait_until_current(self.toolbox, timeout=30)
        build.join()
        assert "toolbox_search_wait_tool" in search.search("Test Tool", "default", self.app.config)

    def _build_search(self) -> ToolBoxSearch:
        schema = AppSchema(GALAXY_CONFIG_SCHEMA_PATH, GALAXY_APP_NAME)
        for option in SEARCH_OPTIONS:
            setattr(self.app.config, option, schema.defaults[option])
        # ToolSearchTuning.from_config also reads index_tool_help, which is not a
        # schema option (GalaxyAppConfiguration sets it from raw kwargs), so the
        # schema-defaults loop above cannot provide it.
        self.app.config.index_tool_help = True
        index_dir = os.path.join(self.test_directory, "tool_search_index")
        self.app.config.tool_search_index_dir = index_dir
        return ToolBoxSearch(self.toolbox, index_dir=index_dir)
