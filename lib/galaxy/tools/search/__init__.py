"""
Module for building and searching the index of tools
installed within this Galaxy. Before changing index-building
or searching related parts it is deeply recommended to read
through the library docs at https://whoosh.readthedocs.io.
"""
import logging
import os
import re
from typing import (
    Dict,
    List,
    Tuple,
    Union,
)

from whoosh import (
    analysis,
    index,
)
from whoosh.analysis import StandardAnalyzer
from whoosh.fields import (
    ID,
    KEYWORD,
    Schema,
    TEXT,
)
from whoosh.qparser import (
    MultifieldParser,
    OrGroup,
)
from whoosh.scoring import (
    BM25F,
    MultiWeighting,
)
from whoosh.writing import AsyncWriter

from galaxy.util import ExecutionTimer
from galaxy.web.framework.helpers import to_unicode

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
            panel_searches[panel_view_id] = ToolPanelViewSearch(panel_view_id, panel_index_dir, index_help=index_help)
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

    def __init__(self, panel_view_id: str, index_dir: str, index_help: bool = True):
        self.schema = Schema(
            id=ID(stored=True, unique=True),
            old_id=ID,
            stub=KEYWORD,
            name=TEXT(analyzer=analysis.SimpleAnalyzer()),
            description=TEXT,
            section=TEXT,
            help=TEXT,
            labels=KEYWORD,
        )
        self.rex = analysis.RegexTokenizer()
        self.index_dir = index_dir
        self.panel_view_id = panel_view_id
        self.index = self._index_setup()

    def _index_setup(self) -> index.Index:
        return get_or_create_index(index_dir=self.index_dir, schema=self.schema)

    def build_index(self, tool_cache, toolbox, index_help: bool = True) -> None:
        """
        Prepare search index for tools loaded in toolbox.
        Use `tool_cache` to determine which tools need indexing and which tools should be expired.
        """
        log.debug(f"Starting to build toolbox index of panel {self.panel_view_id}.")
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
                    add_doc_kwds = self._create_doc(tool_id=tool_id, tool=tool, index_help=index_help)
                    writer.update_document(**add_doc_kwds)
        log.debug(f"Toolbox index of panel {self.panel_view_id} finished {execution_timer}")

    def _create_doc(self, tool_id: str, tool, index_help: bool = True) -> Dict[str, str]:
        #  Do not add data managers to the public index
        if tool.tool_type == "manage_data":
            return {}
        add_doc_kwds = {
            "id": tool_id,
            "description": to_unicode(tool.description),
            "section": to_unicode(tool.get_panel_section()[1] if len(tool.get_panel_section()) == 2 else ""),
            "help": to_unicode(""),
        }
        if tool.name.find("-") != -1:
            # Replace hyphens, since they are wildcards in Whoosh causing false positives
            add_doc_kwds["name"] = (" ").join(token.text for token in self.rex(to_unicode(tool.name)))
        else:
            add_doc_kwds["name"] = to_unicode(tool.name)
        if tool.guid:
            # Create a stub consisting of owner, repo, and tool from guid
            slash_indexes = [m.start() for m in re.finditer("/", tool.guid)]
            id_stub = tool.guid[(slash_indexes[1] + 1) : slash_indexes[4]]
            add_doc_kwds["stub"] = (" ").join(token.text for token in self.rex(to_unicode(id_stub)))
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
                    # Don't fail to build index just because help can't be converted.
                    pass
        return add_doc_kwds

    def search(
        self,
        q: str,
        tool_name_boost: CanConvertToFloat,
        tool_id_boost: CanConvertToFloat,
        tool_section_boost: CanConvertToFloat,
        tool_description_boost: CanConvertToFloat,
        tool_label_boost: CanConvertToFloat,
        tool_stub_boost: CanConvertToFloat,
        tool_help_boost: CanConvertToFloat,
        tool_search_limit: CanConvertToFloat,
        tool_enable_ngram_search: bool,
        tool_ngram_minsize: CanConvertToInt,
        tool_ngram_maxsize: CanConvertToInt,
    ) -> List[str]:
        """
        Perform search on the in-memory index. Weight in the given boosts.
        """
        # Change field boosts for searcher
        self.searcher = self.index.searcher(
            weighting=MultiWeighting(
                BM25F(),
                old_id=BM25F(old_id_B=float(tool_id_boost)),
                name=BM25F(name_B=float(tool_name_boost)),
                section=BM25F(section_B=float(tool_section_boost)),
                description=BM25F(description_B=float(tool_description_boost)),
                labels=BM25F(labels_B=float(tool_label_boost)),
                stub=BM25F(stub_B=float(tool_stub_boost)),
                help=BM25F(help_B=float(tool_help_boost)),
            )
        )
        # Use OrGroup to change the default operation for joining multiple terms to logical OR.
        # This means e.g. for search 'bowtie of king arthur' a document that only has 'bowtie' will be a match.
        # https://whoosh.readthedocs.io/en/latest/api/qparser.html#whoosh.qparser.MultifieldPlugin
        # However this changes scoring i.e. searching 'bowtie of king arthur' a document with 'arthur arthur arthur'
        # would have a higher score than a document with 'bowtie arthur' which is usually unexpected for a user.
        # Hence we introduce a bonus on multi-hits using the 'factory()' method using a scaling factor between 0-1.
        # https://whoosh.readthedocs.io/en/latest/parsing.html#searching-for-any-terms-instead-of-all-terms-by-default
        # Adding the FuzzyTermPlugin to account for misspellings and typos, using a max distance of 2
        og = OrGroup.factory(0.9)
        self.parser = MultifieldParser(
            ["name", "old_id", "description", "section", "help", "labels", "stub"], schema=self.schema, group=og
        )

        cleaned_query = q.lower()
        if tool_enable_ngram_search is True:
            rval = self._search_ngrams(cleaned_query, tool_ngram_minsize, tool_ngram_maxsize, tool_search_limit)
            return rval
        else:
            cleaned_query = " ".join(token.text for token in self.rex(cleaned_query))
            # Use asterisk Whoosh wildcard so e.g. 'bow' easily matches 'bowtie'
            parsed_query = self.parser.parse(f"*{cleaned_query}*")
            hits = self.searcher.search(parsed_query, limit=float(tool_search_limit), sortedby="")
            return [hit["id"] for hit in hits]

    def _search_ngrams(
        self,
        cleaned_query: str,
        tool_ngram_minsize: CanConvertToInt,
        tool_ngram_maxsize: CanConvertToInt,
        tool_search_limit: CanConvertToFloat,
    ) -> List[str]:
        """
        Break tokens into ngrams and search on those instead.
        This should make searching more resistant to typos and unfinished words.
        See docs at https://whoosh.readthedocs.io/en/latest/ngrams.html
        """
        hits_with_score: Dict[str, float] = {}
        token_analyzer = StandardAnalyzer() | analysis.NgramFilter(
            minsize=int(tool_ngram_minsize), maxsize=int(tool_ngram_maxsize)
        )
        ngrams = [token.text for token in token_analyzer(cleaned_query)]
        for query in ngrams:
            # Get the tool list with respective scores for each qgram
            curr_hits = self.searcher.search(self.parser.parse(f"*{query}*"), limit=float(tool_search_limit))
            for i, curr_hit in enumerate(curr_hits):
                is_present = False
                for prev_hit in hits_with_score:
                    # Check if the tool appears again for the next qgram search
                    if curr_hit["id"] == prev_hit:
                        is_present = True
                        # Add the current score with the previous one if the
                        # tool appears again for the next qgram
                        hits_with_score[prev_hit] = curr_hits.score(i) + hits_with_score[prev_hit]
                # Add the tool if not present to the collection with its score
                if not is_present:
                    hits_with_score[curr_hit["id"]] = curr_hits.score(i)
        # Sort the results based on aggregated BM25 score in decreasing order of scores
        hits_with_score_list: List[Tuple[str, float]] = sorted(
            hits_with_score.items(), key=lambda x: x[1], reverse=True
        )
        # Return the tool ids
        return [item[0] for item in hits_with_score_list[0 : int(tool_search_limit)]]
