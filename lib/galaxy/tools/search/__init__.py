"""
Module for building and searching the index of tools
installed within this Galaxy.
"""
import logging
import re
import tempfile

from galaxy.web.framework.helpers import to_unicode
from datetime import datetime

from whoosh.filedb.filestore import RamStorage, FileStorage
from whoosh.fields import KEYWORD, Schema, STORED, TEXT
from whoosh.scoring import BM25F
from whoosh.qparser import MultifieldParser
from whoosh import analysis


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

    def search( self, q, tool_name_boost, tool_section_boost, tool_description_boost, tool_label_boost, tool_stub_boost, tool_help_boost, tool_search_limit ):
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
        # Perform the search
        hits = searcher.search( parser.parse( '*' + q + '*' ), limit=float( tool_search_limit ) )
        return [ hit[ 'id' ] for hit in hits ]


def _temp_storage(self, name=None):
    path = tempfile.mkdtemp()
    tempstore = FileStorage(path)
    return tempstore.create()
