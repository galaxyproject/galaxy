import os

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


class TestToolBoxSearch(BaseToolBoxTestCase):
    def test_versioned_tool_survives_reindex(self):
        # tool_conf.xml.sample lists the newest revision of a multi-version tool
        # first (filters/grep.xml before filters/grep_1.0.1.xml), so the tool
        # cache ends up pointing the shared id at the *older* revision.
        self._init_tool(filename="tool_v02.xml", version="0.2")
        self._init_tool(filename="tool_v01.xml", version="0.1")
        self._add_config("""<toolbox><tool file="tool_v02.xml" /><tool file="tool_v01.xml" /></toolbox>""")
        search = self._build_search()

        search.build_index(self.app.tool_cache, self.toolbox)
        assert "test_tool" in search.search("Test Tool", "default", self.app.config)

        # Galaxy indexes twice on startup: the postfork
        # `rebuild_toolbox_search_index` control task and, for the test driver,
        # an explicit `reindex_tool_search()`.
        self.app.tool_cache.reset_status()
        search.build_index(self.app.tool_cache, self.toolbox)
        assert "test_tool" in search.search("Test Tool", "default", self.app.config)

    def _build_search(self) -> ToolBoxSearch:
        schema = AppSchema(GALAXY_CONFIG_SCHEMA_PATH, GALAXY_APP_NAME)
        for option in SEARCH_OPTIONS:
            setattr(self.app.config, option, schema.defaults[option])
        index_dir = os.path.join(self.test_directory, "tool_search_index")
        self.app.config.tool_search_index_dir = index_dir
        return ToolBoxSearch(self.toolbox, index_dir=index_dir)
