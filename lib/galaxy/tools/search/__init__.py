from galaxy.eggs import require
from galaxy.web.framework.helpers import to_unicode
# Whoosh is compatible with Python 2.5+ Try to import Whoosh and set flag to indicate whether tool search is enabled.
try:
    require( "Whoosh" )

    from whoosh.filedb.filestore import RamStorage
    from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
    from whoosh.index import Index
    from whoosh.scoring import BM25F
    from whoosh.qparser import MultifieldParser
    tool_search_enabled = True
    schema = Schema( id = STORED, title = TEXT, description = TEXT, help = TEXT )
except ImportError, e:
    tool_search_enabled = False
    schema = None

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
        self.enabled = tool_search_enabled
        if tool_search_enabled:
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
        if not tool_search_enabled:
            return []
        # Change field boosts for searcher to place more weight on title, description than help.
        searcher = self.index.searcher( \
                        weighting=BM25F( field_B={ 'title_B' : 3, 'description_B' : 2, 'help_B' : 1 } \
                                    ) )
        # Set query to search title, description, and help.
        parser = MultifieldParser( [ 'title', 'description', 'help' ], schema = schema )
        results = searcher.search( parser.parse( query ), minscore=2.0 )
        return [ result[ return_attribute ] for result in results ]
