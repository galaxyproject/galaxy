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

        # Galaxy indexes twice on startup: the postfork
        # `rebuild_toolbox_search_index` control task and, for the test driver,
        # an explicit `reindex_tool_search()`.
        self.app.tool_cache.reset_status()
        search.build_index(self.app.tool_cache, self.toolbox)
        assert TOOL_ID in search.search("Test Tool", "default", self.app.config)

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
