"""
Module for building and searching the index of tools
installed within this Galaxy. Before changing index-building
or searching related parts it is deeply recommended to read
through the library docs at https://whoosh.readthedocs.io.
"""
import logging
import os
import pprint
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
    Schema,
    TEXT,
    NGRAMWORDS,
)
from whoosh.qparser import (
    MultifieldParser,
)
from whoosh.scoring import (
    BM25F,
    Frequency,
    MultiWeighting,
)
from whoosh.writing import AsyncWriter

from galaxy.util import ExecutionTimer
from galaxy.web.framework.helpers import to_unicode
from galaxy.config import GalaxyAppConfiguration

log = logging.getLogger(__name__)

CanConvertToFloat = Union[str, int, float]
CanConvertToInt = Union[str, int, float]


def get_or_create_index(index_dir: str, schema: Schema) -> index.Index:
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)
    if index.exists_in(index_dir):
        idx = index.open_dir(index_dir)
        try:
            assert idx.schema == schema
            return idx
        except AssertionError:
            log.warning("Index at '%s' uses outdated schema, creating new index", index_dir)

    # Delete the old index if schema has changed
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
                panel_view_id, panel_index_dir, index_help=index_help,
                config=toolbox.app.config)
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
        index_help: bool = True
    ):
        """Build the schema and validate against the index."""
        schema_conf = {
            # The ID field is currently not searchable!?
            # Can't fix, spent hours trying
            'id': ID(stored=True, unique=True),
            'id_exact': TEXT(
                field_boost=(
                    config.tool_id_boost
                    * config.tool_name_exact_multiplier),
                analyzer=analysis.IDTokenizer() | analysis.LowercaseFilter(),
            ),
            'name': TEXT(
                field_boost=(
                    config.tool_name_boost
                    * config.tool_name_exact_multiplier),
                analyzer=analysis.IDTokenizer() | analysis.LowercaseFilter(),
            ),
            'stub': KEYWORD(field_boost=float(config.tool_stub_boost)),
            'section': TEXT(field_boost=float(config.tool_section_boost)),
            'description': TEXT(
                field_boost=config.tool_description_boost,
                analyzer=analysis.StemmingAnalyzer()),
            'help': TEXT(
                field_boost=config.tool_help_boost,
                analyzer=analysis.StemmingAnalyzer()),
            'labels': KEYWORD(field_boost=float(config.tool_label_boost)),
        }

        if config.tool_enable_ngram_search:
            schema_conf.update({
                'name_ngrams': NGRAMWORDS(
                    stored=True,
                    minsize=config.tool_ngram_minsize,
                    maxsize=config.tool_ngram_maxsize,
                    field_boost=(
                        float(config.tool_name_boost)
                        * config.tool_ngram_factor
                    ),
                ),
            })

        self.schema = Schema(**schema_conf)
        self.rex = analysis.RegexTokenizer()
        self.index_dir = index_dir
        self.panel_view_id = panel_view_id
        self.index = self._index_setup()

    def _index_setup(self) -> index.Index:
        return get_or_create_index(index_dir=self.index_dir, schema=self.schema)

    def build_index(self, tool_cache, toolbox, index_help: bool = True) -> None:
        """Prepare search index for tools loaded in toolbox.

        Use `tool_cache` to determine which tools need indexing and which tools
        should be expired.
        """
        log.debug(
            f"Starting to build toolbox index of panel {self.panel_view_id}.")
        execution_timer = ExecutionTimer()
        with self.index.reader() as reader:
            # Index ocasionally contains empty stored fields
            indexed_tool_ids = {f["id"] for f in reader.all_stored_fields() if f}
        tool_ids_to_remove = (indexed_tool_ids - set(tool_cache._tool_paths_by_id.keys())).union(
            tool_cache._removed_tool_ids
        )
        for indexed_tool_id in indexed_tool_ids:
            indexed_tool = tool_cache.get_tool_by_id(indexed_tool_id)
            if indexed_tool:
                if indexed_tool.is_latest_version:
                    continue
                latest_version = indexed_tool.latest_version
                if latest_version and latest_version.hidden:
                    continue
            tool_ids_to_remove.add(indexed_tool_id)

        with AsyncWriter(self.index) as writer:
            for tool_id in tool_ids_to_remove:
                writer.delete_by_term("id", tool_id)
            for tool_id in tool_cache._new_tool_ids - indexed_tool_ids:
                tool = toolbox.get_tool(tool_id)
                if tool and tool.is_latest_version and toolbox.panel_has_tool(tool, self.panel_view_id):
                    if tool.hidden:
                        # we check if there is an older tool we can return
                        if tool.lineage:
                            for tool_version in reversed(tool.lineage.get_versions()):
                                tool = tool_cache.get_tool_by_id(tool_version.id)
                                if tool and not tool.hidden:
                                    tool_id = tool.id
                                    break
                            else:
                                continue
                        else:
                            continue
                    add_doc_kwds = self._create_doc(
                        tool_id=tool_id,
                        tool=tool,
                        index_help=index_help,
                        config=toolbox.app.config,
                    )
                    writer.update_document(**add_doc_kwds)

        log.debug(
            f"Toolbox index of panel {self.panel_view_id}"
            f" finished {execution_timer}")

    def _create_doc(
        self,
        tool_id: str,
        tool,
        index_help: bool = True,
        config: GalaxyAppConfiguration = None,
    ) -> Dict[str, str]:
        #  Do not add data managers to the public index
        if tool.tool_type == "manage_data":
            return {}
        add_doc_kwds = {
            "id": to_unicode(tool_id),
            "id_exact": to_unicode(tool_id),
            "description": to_unicode(tool.description),
            "section": to_unicode(
                tool.get_panel_section()[1]
                if len(tool.get_panel_section()) == 2
                else ""
            ),
            "help": to_unicode(""),
        }
        if tool.name.find("-") != -1:
            # Replace hyphens since they are wildcards in Whoosh
            add_doc_kwds["name"] = (" ").join(
                token.text for token in self.rex(to_unicode(tool.name))
            )
        else:
            add_doc_kwds["name"] = to_unicode(tool.name)
        if tool.guid:
            # Create a stub consisting of owner, repo, and tool from guid
            slash_indexes = [m.start() for m in re.finditer("/", tool.guid)]
            id_stub = tool.guid[(slash_indexes[1] + 1):slash_indexes[4]]
            add_doc_kwds["stub"] = (" ").join(
                token.text for token in self.rex(to_unicode(id_stub))
            )
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

        if config.tool_enable_ngram_search:
            add_doc_kwds["name_ngrams"] = add_doc_kwds["name"]

        return add_doc_kwds

    def search(
        self,
        q: str,
        config: GalaxyAppConfiguration = None,
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
            "description",
            "section",
            "help",
            "labels",
            "stub",
        ]
        if config.tool_enable_ngram_search:
            fields += [
                "name_ngrams",
            ]
        self.parser = MultifieldParser(
            fields,
            schema=self.schema,
        )
        cleaned_query = " ".join(
            token.text for token in self.rex(q.lower())
        )
        parsed_query = self.parser.parse(cleaned_query)
        hits = self.searcher.search(
            parsed_query,
            limit=float(config.tool_search_limit),
            sortedby="",
            terms=True,
        )

        # !!! log match scores --------------------------------------------
        scores = [
            x[0] for x in hits.top_n
        ][:config.tool_search_limit]

        log.debug(pprint.pformat([
            {
                'score': score,
                'details': hit['id'],
                'matched_terms': hit.matched_terms(),
            }
            for hit, score in zip(hits[:config.tool_search_limit], scores)
        ]))
        # !!! -------------------------------------------------------------

        return [hit["id"] for hit in hits[:config.tool_search_limit]]
