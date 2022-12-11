"""
Module for building and searching the index of installed tools.

Before changing index-building or searching related parts it is highly
recommended to read the docs at https://whoosh.readthedocs.io.

Schema - this is how we define the index, both for building and searching. A
    field is created for each data element that we want to add e.g. tool name,
    tool ID, description. The type of field and its attributes define how
    entries for that field will be indexed and ultimately how they can be
    searched. Score weighting (boost) is added here on a per-field bases, to
    allow matches to important fields like "name" to receive a higher score.

Tokenizers - these take an attribute (e.g. name) and parse it into "tokens" to
    be stored in the index. Can be done in many ways for different search
    functionality. For example, the IDTokenizer creates one token for an entire
    entry, resulting in an index field that requires a full-field match. The
    default tokenizer will break an entry into words, so that single word
    matches are possible.

Filters - various filters are available for processing content as the index is
    built. A StopFilter removes common articles 'a', 'for', 'and' etc. A
    StemmingFilter removes suffixes from words to create a 'base work' e.g.
    stemming -> stem; opened -> open; philosophy -> philosoph.

"""
import logging
import os
import re
import shutil
from typing import (
    Dict,
    List,
    Union,
)

from whoosh import (
    analysis,
    index,
)
from whoosh.fields import (
    ID,
    KEYWORD,
    NGRAMWORDS,
    Schema,
    TEXT,
)
from whoosh.qparser import (
    MultifieldParser,
    OrGroup,
)
from whoosh.scoring import (
    BM25F,
    Frequency,
    MultiWeighting,
)
from whoosh.writing import AsyncWriter

from galaxy.config import GalaxyAppConfiguration
from galaxy.util import ExecutionTimer
from galaxy.web.framework.helpers import to_unicode

log = logging.getLogger(__name__)

CanConvertToFloat = Union[str, int, float]
CanConvertToInt = Union[str, int, float]


def get_or_create_index(index_dir, schema):
    """Get or create a reference to the index."""
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    if index.exists_in(index_dir):
        idx = index.open_dir(index_dir)
        if idx.schema == schema:
            return idx
    log.warning(f"Index at '{index_dir}' uses outdated schema, creating a new index")

    # Delete the old index and return a new index reference
    shutil.rmtree(index_dir)
    os.makedirs(index_dir)
    return index.create_in(index_dir, schema=schema)


class ToolBoxSearch:
    """Support searching across all fixed panel views in a toolbox.

    Search is delegated off to ToolPanelViewSearch for each panel object.
    """

    def __init__(self, toolbox, index_dir: str, index_help: bool = True):
        panel_searches = {}
        for panel_view in toolbox.panel_views():
            panel_view_id = panel_view.id
            panel_index_dir = os.path.join(index_dir, panel_view_id)
            panel_searches[panel_view_id] = ToolPanelViewSearch(
                panel_view_id,
                panel_index_dir,
                index_help=index_help,
                config=toolbox.app.config,
            )
        self.panel_searches = panel_searches
        # We keep track of how many times the tool index has been rebuilt.
        # We start at -1, so that after the first index the count is at 0,
        # which is the same as the toolbox reload count. This way we can skip
        # reindexing if the index count is equal to the toolbox reload count.
        self.index_count = -1

    def build_index(self, tool_cache, toolbox, index_help: bool = True) -> None:
        self.index_count += 1
        for panel_search in self.panel_searches.values():
            panel_search.build_index(tool_cache, toolbox, index_help=index_help)

    def search(self, *args, **kwd) -> List[str]:
        panel_view = kwd.pop("panel_view")
        if panel_view not in self.panel_searches:
            raise KeyError(f"Unknown panel_view specified {panel_view}")
        panel_search = self.panel_searches[panel_view]
        return panel_search.search(*args, **kwd)


class ToolPanelViewSearch:
    """
    Support searching tools in a toolbox. This implementation uses
    the Whoosh search library.
    """

    def __init__(
        self,
        panel_view_id: str,
        index_dir: str,
        config: GalaxyAppConfiguration,
        index_help: bool = True,
    ):
        """Build the schema and validate against the index."""
        schema_conf = {
            # The stored ID field is not searchable
            "id": ID(stored=True, unique=True),
            # This exact field is searchable by exact matches only
            "id_exact": TEXT(
                field_boost=(config.tool_id_boost * config.tool_name_exact_multiplier),
                analyzer=analysis.IDTokenizer() | analysis.LowercaseFilter(),
            ),
            # The primary name field is searchable by exact match only, and is
            # eligible for massive score boosting. A secondary ngram or text
            # field for name is added below
            "name_exact": TEXT(
                field_boost=(config.tool_name_boost * config.tool_name_exact_multiplier),
                analyzer=analysis.IDTokenizer() | analysis.LowercaseFilter(),
            ),
            # The owner/repo/tool_id parsed from the GUID
            "stub": KEYWORD(field_boost=float(config.tool_stub_boost)),
            # The section where the tool is listed in the tool panel
            "section": TEXT(field_boost=float(config.tool_section_boost)),
            # The edam operations section where the tool is listed in the tool panel
            "edam_operations": TEXT(field_boost=float(config.tool_section_boost)),
            # The edam topics section where the tool is listed in the tool panel
            "edam_topics": TEXT(field_boost=float(config.tool_section_boost)),
            # Short description defined in the tool XML
            "description": TEXT(
                field_boost=config.tool_description_boost,
                analyzer=analysis.StemmingAnalyzer(),
            ),
            # Help text parsed from the tool XML
            "help": TEXT(field_boost=config.tool_help_boost, analyzer=analysis.StemmingAnalyzer()),
            "labels": KEYWORD(field_boost=float(config.tool_label_boost)),
        }

        if config.tool_enable_ngram_search:
            schema_conf.update(
                {
                    "name": NGRAMWORDS(
                        minsize=config.tool_ngram_minsize,
                        maxsize=config.tool_ngram_maxsize,
                        field_boost=(float(config.tool_name_boost) * config.tool_ngram_factor),
                    ),
                }
            )
        else:
            schema_conf.update(
                {
                    "name": TEXT(
                        field_boost=float(config.tool_name_boost),
                    ),
                }
            )

        self.schema = Schema(**schema_conf)
        self.rex = analysis.RegexTokenizer()
        self.index_dir = index_dir
        self.panel_view_id = panel_view_id
        self.index = self._index_setup()

    def _index_setup(self) -> index.Index:
        """Get or create a reference to the index."""
        return get_or_create_index(self.index_dir, self.schema)

    def build_index(self, tool_cache, toolbox, index_help: bool = True) -> None:
        """Prepare search index for tools loaded in toolbox.

        Use `tool_cache` to determine which tools need indexing and which
        should be removed.
        """
        log.debug(f"Starting to build toolbox index of panel {self.panel_view_id}.")
        execution_timer = ExecutionTimer()

        with self.index.reader() as reader:
            # Index ocasionally contains empty stored fields
            self.indexed_tool_ids = {f["id"] for f in reader.all_stored_fields() if f}

        tool_ids_to_remove = self._get_tools_to_remove(tool_cache)
        tools_to_index = self._get_tool_list(
            toolbox,
            tool_cache,
        )

        with AsyncWriter(self.index) as writer:
            for tool_id in tool_ids_to_remove:
                writer.delete_by_term("id", tool_id)
            for tool in tools_to_index:
                add_doc_kwds = self._create_doc(
                    tool=tool,
                    index_help=index_help,
                )
                # Add tool document to index (or overwrite if existing)
                writer.update_document(**add_doc_kwds)

        log.debug(f"Toolbox index of panel {self.panel_view_id}" f" finished {execution_timer}")

    def _get_tools_to_remove(self, tool_cache) -> list:
        """Return list of tool IDs to be removed from index."""
        tool_ids_to_remove = (self.indexed_tool_ids - set(tool_cache._tool_paths_by_id.keys())).union(
            tool_cache._removed_tool_ids
        )

        for indexed_tool_id in self.indexed_tool_ids:
            indexed_tool = tool_cache.get_tool_by_id(indexed_tool_id)
            if indexed_tool:
                if indexed_tool.is_latest_version:
                    continue
                latest_version = indexed_tool.latest_version
                if latest_version and latest_version.hidden:
                    continue
            tool_ids_to_remove.add(indexed_tool_id)

        return list(tool_ids_to_remove)

    def _get_tool_list(self, toolbox, tool_cache) -> list:
        """Return list of tools to add and remove from index."""
        tools_to_index = []

        for tool_id in tool_cache._new_tool_ids - self.indexed_tool_ids:
            tool = toolbox.get_tool(tool_id)
            if tool and tool.is_latest_version and toolbox.panel_has_tool(tool, self.panel_view_id):
                if tool.hidden:
                    # Check if there is an older tool we can return
                    if tool.lineage:
                        tool_versions = reversed(tool.lineage.get_versions())
                        for tool_version in tool_versions:
                            tool = tool_cache.get_tool_by_id(tool_version.id)
                            if tool and not tool.hidden:
                                break
                    else:
                        continue
                tools_to_index.append(tool)

        return tools_to_index

    def _create_doc(
        self,
        tool,
        index_help: bool = True,
    ) -> Dict[str, str]:
        def clean(string):
            """Remove hyphens as they are Whoosh wildcards."""
            if "-" in string:
                return (" ").join(token.text for token in self.rex(to_unicode(tool.name)))
            else:
                return string

        if tool.tool_type == "manage_data":
            #  Do not add data managers to the public index
            return {}
        add_doc_kwds = {
            "id": to_unicode(tool.id),
            "id_exact": to_unicode(tool.id),
            "name": clean(tool.name),
            "description": to_unicode(tool.description),
            "section": to_unicode(tool.get_panel_section()[1] if len(tool.get_panel_section()) == 2 else ""),
            "edam_operations": clean(tool.edam_operations),
            "edam_topics": clean(tool.edam_topics),
            "help": to_unicode(""),
        }
        if tool.guid:
            # Create a stub consisting of owner, repo, and tool from guid
            slash_indexes = [m.start() for m in re.finditer("/", tool.guid)]
            id_stub = tool.guid[(slash_indexes[1] + 1) : slash_indexes[4]]
            add_doc_kwds["stub"] = clean(id_stub)
        else:
            add_doc_kwds["stub"] = to_unicode(id)
        if tool.labels:
            add_doc_kwds["labels"] = to_unicode(" ".join(tool.labels))
        if index_help:
            raw_help = tool.raw_help
            if raw_help:
                try:
                    add_doc_kwds["help"] = to_unicode(raw_help)
                except Exception:
                    # Don't fail to build index when help fails to parse
                    pass

        add_doc_kwds["name_exact"] = add_doc_kwds["name"]

        return add_doc_kwds

    def search(
        self,
        q: str,
        config: GalaxyAppConfiguration,
    ) -> List[str]:
        """Perform search on the in-memory index."""
        # Change field boosts for searcher
        self.searcher = self.index.searcher(
            weighting=MultiWeighting(
                Frequency(),
                help=BM25F(K1=config.tool_help_bm25f_k1),
            )
        )
        fields = [
            "id",
            "id_exact",
            "name",
            "name_exact",
            "description",
            "section",
            "edam_operations",
            "edam_topics",
            "help",
            "labels",
            "stub",
        ]
        self.parser = MultifieldParser(
            fields,
            schema=self.schema,
            group=OrGroup,
        )
        parsed_query = self.parser.parse(q)
        hits = self.searcher.search(
            parsed_query,
            limit=None,
            sortedby="",
            terms=True,
        )

        return [hit["id"] for hit in hits]
