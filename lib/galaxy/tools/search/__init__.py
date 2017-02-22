"""
Module for building and searching the index of tools
installed within this Galaxy.
"""
import logging
import re
import tempfile
from datetime import datetime

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

from galaxy.web.framework.helpers import to_unicode

log = logging.getLogger( __name__ )


class ToolBoxSearch( object ):
    """
    Support searching tools in a toolbox. This implementation uses
    the Whoosh search library.
    """

    def __init__( self, toolbox, index_help=True ):
        """
        Create a searcher for `toolbox`.
        """
        self.schema = Schema( id=STORED,
                              stub=KEYWORD,
                              name=TEXT( analyzer=analysis.SimpleAnalyzer() ),
                              description=TEXT,
                              section=TEXT,
                              help=TEXT,
                              labels=KEYWORD )
        self.rex = analysis.RegexTokenizer()
        self.toolbox = toolbox
        self.build_index( index_help )

    def build_index( self, index_help=True ):
        # Works around https://bitbucket.org/mchaput/whoosh/issues/391/race-conditions-with-temp-storage
        RamStorage.temp_storage = _temp_storage
        self.storage = RamStorage()
        self.index = self.storage.create_index( self.schema )
        writer = self.index.writer()
        start_time = datetime.now()
        log.debug( 'Starting to build toolbox index.' )
        for id, tool in self.toolbox.tools():
            #  Do not add data managers to the public index
            if tool.tool_type == 'manage_data':
                continue
            add_doc_kwds = {
                "id": id,
                "description": to_unicode( tool.description ),
                "section": to_unicode( tool.get_panel_section()[1] if len( tool.get_panel_section() ) == 2 else '' ),
                "help": to_unicode( "" )
            }
            # Hyphens are wildcards in Whoosh causing bad things
            if tool.name.find( '-' ) != -1:
                add_doc_kwds['name'] = (' ').join( [ token.text for token in self.rex( to_unicode( tool.name ) ) ] )
            else:
                add_doc_kwds['name'] = to_unicode( tool.name )
            # We do not want to search Tool Shed or version parts
            # of the long ids
            if id.find( '/' ) != -1:
                slash_indexes = [ m.start() for m in re.finditer( '/', id ) ]
                id_stub = id[ ( slash_indexes[1] + 1 ): slash_indexes[4] ]
                add_doc_kwds['stub'] = (' ').join( [ token.text for token in self.rex( to_unicode( id_stub ) ) ] )
            else:
                add_doc_kwds['stub'] = to_unicode( id )
            if tool.labels:
                add_doc_kwds['labels'] = to_unicode( " ".join( tool.labels ) )
            if index_help and tool.help:
                try:
                    add_doc_kwds['help'] = to_unicode( tool.help.render( host_url="", static_path="" ) )
                except Exception:
                    # Don't fail to build index just because a help message
                    # won't render.
                    pass
            writer.add_document( **add_doc_kwds )
        writer.commit()
        stop_time = datetime.now()
        log.debug( 'Toolbox index finished. It took: ' + str(stop_time - start_time) )

    def search( self, q, tool_name_boost, tool_section_boost, tool_description_boost, tool_label_boost, tool_stub_boost, tool_help_boost, tool_search_limit, tool_enable_ngram_search, tool_ngram_minsize, tool_ngram_maxsize ):
        """
        Perform search on the in-memory index. Weight in the given boosts.
        """
        # Change field boosts for searcher
        searcher = self.index.searcher(
            weighting=BM25F(
                field_B={ 'name_B': float( tool_name_boost ),
                          'section_B': float( tool_section_boost ),
                          'description_B': float( tool_description_boost ),
                          'labels_B': float( tool_label_boost ),
                          'stub_B': float( tool_stub_boost ),
                          'help_B': float( tool_help_boost ) }
            )
        )
        # Set query to search name, description, section, help, and labels.
        parser = MultifieldParser( [ 'name', 'description', 'section', 'help', 'labels', 'stub' ], schema=self.schema )
        # Hyphens are wildcards in Whoosh causing bad things
        if q.find( '-' ) != -1:
            q = (' ').join( [ token.text for token in self.rex( to_unicode( q ) ) ] )
        # Perform tool search with ngrams if set to true in the config file
        if ( tool_enable_ngram_search is True or tool_enable_ngram_search == "True" ):
            hits_with_score = {}
            token_analyzer = StandardAnalyzer() | analysis.NgramFilter( minsize=int( tool_ngram_minsize ), maxsize=int( tool_ngram_maxsize ) )
            ngrams = [ token.text for token in token_analyzer( q ) ]
            for query in ngrams:
                # Get the tool list with respective scores for each qgram
                curr_hits = searcher.search( parser.parse( '*' + query + '*' ), limit=float( tool_search_limit ) )
                for i, curr_hit in enumerate( curr_hits ):
                    is_present = False
                    for prev_hit in hits_with_score:
                        # Check if the tool appears again for the next qgram search
                        if curr_hit[ 'id' ] == prev_hit:
                            is_present = True
                            # Add the current score with the previous one if the
                            # tool appears again for the next qgram
                            hits_with_score[ prev_hit ] = curr_hits.score(i) + hits_with_score[ prev_hit ]
                    # Add the tool if not present to the collection with its score
                    if not is_present:
                        hits_with_score[ curr_hit[ 'id' ] ] = curr_hits.score(i)
            # Sort the results based on aggregated BM25 score in decreasing order of scores
            hits_with_score = sorted( hits_with_score.items(), key=lambda x: x[1], reverse=True )
            # Return the tool ids
            return [ item[0] for item in hits_with_score[ 0:int( tool_search_limit ) ] ]
        else:
            # Perform the search
            hits = searcher.search( parser.parse( '*' + q + '*' ), limit=float( tool_search_limit ) )
            return [ hit[ 'id' ] for hit in hits ]


def _temp_storage(self, name=None):
    path = tempfile.mkdtemp()
    tempstore = FileStorage(path)
    return tempstore.create()
