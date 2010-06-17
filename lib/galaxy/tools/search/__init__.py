from galaxy.eggs import require
require( "Whoosh" )

from whoosh.filedb.filestore import RamStorage
from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
from whoosh.index import Index
from whoosh.qparser import QueryParser

schema = Schema( id = STORED, title = TEXT, help = TEXT )

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
            def to_unicode( a_basestr ):
                if type( a_basestr ) is str:
                    return unicode( a_basestr, 'utf-8' )
                else:
                    return a_basestr

            writer.add_document( id=id, title=to_unicode(tool.name), help=to_unicode(tool.help) )
        writer.commit()
        
    def search( self, query, return_attribute='id' ):
        searcher = self.index.searcher()
        parser = QueryParser( "help", schema = schema )
        results = searcher.search( parser.parse( query ) )
        return [ result[ return_attribute ] for result in results ]