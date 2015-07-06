"""
Module for building and searching the index of tools
installed within this Galaxy.
"""
from galaxy import eggs
from galaxy.web.framework.helpers import to_unicode

eggs.require( "Whoosh" )
from whoosh.filedb.filestore import RamStorage
from whoosh.fields import Schema, STORED, TEXT
from whoosh.scoring import BM25F
from whoosh.qparser import MultifieldParser
schema = Schema( id=STORED,
                 name=TEXT,
                 description=TEXT,
                 section=TEXT,
                 help=TEXT )
import logging
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
        self.toolbox = toolbox
        self.build_index( index_help )

    def build_index( self, index_help=True ):
        log.debug( 'Starting to build toolbox index.' )
        self.storage = RamStorage()
        self.index = self.storage.create_index( schema )
        writer = self.index.writer()
        for id, tool in self.toolbox.tools():
            #  Do not add data managers to the public index
            if tool.tool_type == 'manage_data':
                continue
            add_doc_kwds = {
                "id": id,
                "name": to_unicode( tool.name ),
                "description": to_unicode( tool.description ),
                "section": to_unicode( tool.get_panel_section()[1] if len( tool.get_panel_section() ) == 2 else '' ),
                "help": to_unicode( "" )
            }
            if index_help and tool.help:
                try:
                    add_doc_kwds['help'] = to_unicode( tool.help.render( host_url="", static_path="" ) )
                except Exception:
                    # Don't fail to build index just because a help message
                    # won't render.
                    pass
            writer.add_document( **add_doc_kwds )
        writer.commit()
        log.debug( 'Toolbox index finished.' )

    def search( self, q, tool_name_boost, tool_section_boost, tool_description_boost, tool_help_boost, tool_search_limit ):
        """
        Perform search on the in-memory index. Weight in the given boosts.
        """
        # Change field boosts for searcher
        searcher = self.index.searcher(
            weighting=BM25F(
                field_B={ 'name_B': float( tool_name_boost ),
                          'section_B': float( tool_section_boost ),
                          'description_B': float( tool_description_boost ),
                          'help_B': float( tool_help_boost ) }
            )
        )
        # Set query to search name, description, section, and help.
        parser = MultifieldParser( [ 'name', 'description', 'section', 'help' ], schema=schema )
        # Perform the search
        hits = searcher.search( parser.parse( '*' + q + '*' ), limit=float( tool_search_limit ) )
        return [ hit[ 'id' ] for hit in hits ]
