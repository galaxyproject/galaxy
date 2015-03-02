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
                 title=TEXT,
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

    def build_index( self, index_help ):
        self.storage = RamStorage()
        self.index = self.storage.create_index( schema )
        writer = self.index.writer()
        for id, tool in self.toolbox.tools():
            add_doc_kwds = {
                "id": id,
                "title": to_unicode( tool.name ),
                "description": to_unicode( tool.description ),
                "section": to_unicode( tool.get_panel_section()[1] if len( tool.get_panel_section() ) == 2 else '' ),
                "help": to_unicode( "" ),
            }
            if index_help and tool.help:
                try:
                    add_doc_kwds['help'] = to_unicode(tool.help.render( host_url="", static_path="" ))
                except Exception:
                    # Don't fail to build index just because a help message
                    # won't render.
                    pass
            writer.add_document( **add_doc_kwds )
        writer.commit()

    def search( self, query, return_attribute='id' ):
        # Change field boosts for searcher
        searcher = self.index.searcher(
            weighting=BM25F(
                field_B={ 'title_B': 9,
                          'section_B': 3,
                          'description_B': 2,
                          'help_B': 0.5 }
            )
        )
        # Set query to search title, description, section, and help.
        parser = MultifieldParser( [ 'title', 'description', 'section', 'help' ], schema=schema )
        # Perform the search
        hits = searcher.search( parser.parse( '*' + query + '*' ), limit=20 )

        return [ hit[ return_attribute ] for hit in hits ]
