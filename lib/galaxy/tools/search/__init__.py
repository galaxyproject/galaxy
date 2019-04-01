"""
Module for building and searching the index of tools
installed within this Galaxy.
"""
import logging
import re
import tempfile

from bleach import clean
from whoosh import analysis
from whoosh.analysis import StandardAnalyzer
from whoosh.fields import (
    KEYWORD,
    Schema,
    STORED,
    TEXT
)
from whoosh.filedb.filestore import (
    FileStorage,
    RamStorage
)
from whoosh.qparser import MultifieldParser
from whoosh.scoring import BM25F

from galaxy.util import ExecutionTimer
from galaxy.web.framework.helpers import to_unicode

log = logging.getLogger(__name__)


class ToolBoxSearch(object):
    """
    Support searching tools in a toolbox. This implementation uses
    the Whoosh search library.
    """

    def __init__(self, toolbox, index_help=True):
        """
        Create a searcher for `toolbox`.
        """
        self.schema = Schema(id=STORED,
                             stub=KEYWORD,
                             name=TEXT(analyzer=analysis.SimpleAnalyzer()),
                             description=TEXT,
                             section=TEXT,
                             help=TEXT,
                             labels=KEYWORD)
        self.rex = analysis.RegexTokenizer()
        self.toolbox = toolbox
        self.storage, self.index = self._index_setup()
        # We keep track of how many times the tool index has been rebuilt.
        # We start at -1, so that after the first index the count is at 0,
        # which is the same as the toolbox reload count. This way we can skip
        # reindexing if the index count is equal to the toolbox reload count.
        self.index_count = -1

    def _index_setup(self):
        RamStorage.temp_storage = _temp_storage
        # Works around https://bitbucket.org/mchaput/whoosh/issues/391/race-conditions-with-temp-storage
        storage = RamStorage()
        index = storage.create_index(self.schema)
        return storage, index

    def build_index(self, tool_cache, index_help=True):
        """
        Prepare search index for tools loaded in toolbox.
        Use `tool_cache` to determine which tools need indexing and which tools should be expired.
        """
        log.debug('Starting to build toolbox index.')
        self.index_count += 1
        execution_timer = ExecutionTimer()
        writer = self.index.writer()
        for tool_id in tool_cache._removed_tool_ids:
            writer.delete_by_term('id', tool_id)
        for tool_id in tool_cache._new_tool_ids:
            tool = tool_cache.get_tool_by_id(tool_id)
            if tool:
                add_doc_kwds = self._create_doc(tool_id=tool_id, tool=tool, index_help=index_help)
                writer.add_document(**add_doc_kwds)
        writer.commit()
        log.debug("Toolbox index finished %s", execution_timer)

    def _create_doc(self, tool_id, tool, index_help=True):
        #  Do not add data managers to the public index
        if tool.tool_type == 'manage_data':
            return {}
        add_doc_kwds = {
            "id": tool_id,
            "description": to_unicode(tool.description),
            "section": to_unicode(tool.get_panel_section()[1] if len(tool.get_panel_section()) == 2 else ''),
            "help": to_unicode("")
        }
        if tool.name.find('-') != -1:
            # Hyphens are wildcards in Whoosh causing bad things
            add_doc_kwds['name'] = (' ').join([token.text for token in self.rex(to_unicode(tool.name))])
        else:
            add_doc_kwds['name'] = to_unicode(tool.name)
        if tool.guid:
            # Create a stub consisting of owner, repo, and tool from guid
            slash_indexes = [m.start() for m in re.finditer('/', tool.guid)]
            id_stub = tool.guid[(slash_indexes[1] + 1): slash_indexes[4]]
            add_doc_kwds['stub'] = (' ').join([token.text for token in self.rex(to_unicode(id_stub))])
        else:
            add_doc_kwds['stub'] = to_unicode(id)
        if tool.labels:
            add_doc_kwds['labels'] = to_unicode(" ".join(tool.labels))
        if index_help and tool.help:
            try:
                raw_html = tool.help.render(host_url="", static_path="")
                cleantext = clean(raw_html, tags=[''], strip=True).replace('\n', ' ')
                add_doc_kwds['help'] = to_unicode(cleantext)
            except Exception:
                # Don't fail to build index just because a help message
                # won't render.
                pass
        return add_doc_kwds

    def search(self, q, tool_name_boost, tool_section_boost, tool_description_boost, tool_label_boost, tool_stub_boost, tool_help_boost, tool_search_limit, tool_enable_ngram_search, tool_ngram_minsize, tool_ngram_maxsize):
        """
        Perform search on the in-memory index. Weight in the given boosts.
        """
        # Change field boosts for searcher
        searcher = self.index.searcher(
            weighting=BM25F(
                field_B={'name_B': float(tool_name_boost),
                         'section_B': float(tool_section_boost),
                         'description_B': float(tool_description_boost),
                         'labels_B': float(tool_label_boost),
                         'stub_B': float(tool_stub_boost),
                         'help_B': float(tool_help_boost)}
            )
        )
        # Set query to search name, description, section, help, and labels.
        parser = MultifieldParser(['name', 'description', 'section', 'help', 'labels', 'stub'], schema=self.schema)
        # Hyphens are wildcards in Whoosh causing bad things
        if q.find('-') != -1:
            q = (' ').join([token.text for token in self.rex(to_unicode(q))])
        # Perform tool search with ngrams if set to true in the config file
        if (tool_enable_ngram_search is True or tool_enable_ngram_search == "True"):
            hits_with_score = {}
            token_analyzer = StandardAnalyzer() | analysis.NgramFilter(minsize=int(tool_ngram_minsize), maxsize=int(tool_ngram_maxsize))
            ngrams = [token.text for token in token_analyzer(q)]
            for query in ngrams:
                # Get the tool list with respective scores for each qgram
                curr_hits = searcher.search(parser.parse('*' + query + '*'), limit=float(tool_search_limit))
                for i, curr_hit in enumerate(curr_hits):
                    is_present = False
                    for prev_hit in hits_with_score:
                        # Check if the tool appears again for the next qgram search
                        if curr_hit['id'] == prev_hit:
                            is_present = True
                            # Add the current score with the previous one if the
                            # tool appears again for the next qgram
                            hits_with_score[prev_hit] = curr_hits.score(i) + hits_with_score[prev_hit]
                    # Add the tool if not present to the collection with its score
                    if not is_present:
                        hits_with_score[curr_hit['id']] = curr_hits.score(i)
            # Sort the results based on aggregated BM25 score in decreasing order of scores
            hits_with_score = sorted(hits_with_score.items(), key=lambda x: x[1], reverse=True)
            # Return the tool ids
            return [item[0] for item in hits_with_score[0:int(tool_search_limit)]]
        else:
            # Perform the search
            hits = searcher.search(parser.parse('*' + q + '*'), limit=float(tool_search_limit))
            return [hit['id'] for hit in hits]


def _temp_storage(self, name=None):
    path = tempfile.mkdtemp()
    tempstore = FileStorage(path)
    return tempstore.create()
