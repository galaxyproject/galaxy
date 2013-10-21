from galaxy.eggs import require
from galaxy.web.framework.helpers import to_unicode
require( "Whoosh" )

from whoosh.filedb.filestore import RamStorage
from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import Index
from whoosh.scoring import BM25F
from whoosh.qparser import MultifieldParser
schema = Schema( id = STORED, title = TEXT, description = TEXT, help = TEXT )

class ToolBoxSearch( object ):
    """
    Support searching tools in a toolbox. This implementation uses
    the "whoosh" search library.
    """

    def __init__( self, toolbox ):
        """
        Create a searcher for `toolbox`.
        """
        self.toolbox = toolbox
        self.build_index()

    def build_index( self ):
        self.storage = RamStorage()
        self.index = self.storage.create_index( schema )
        writer = self.index.writer()
        ## TODO: would also be nice to search section headers.
        for id, tool in self.toolbox.tools_by_id.iteritems():
            writer.add_document( id=id, title=to_unicode(tool.name), description=to_unicode(tool.description), help=to_unicode(tool.help) )
        writer.commit()

    def search( self, query, return_attribute='id' ):
        # Change field boosts for searcher to place more weight on title, description than help.
        searcher = self.index.searcher( \
                        weighting=BM25F( field_B={ 'title_B' : 3, 'description_B' : 2, 'help_B' : 1 } \
                                    ) )
        # Set query to search title, description, and help.
        parser = MultifieldParser( [ 'title', 'description', 'help' ], schema = schema )
        results = searcher.search( parser.parse( query ) )
        return [ result[ return_attribute ] for result in results ]
