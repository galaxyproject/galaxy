"""
Tabular datatype

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging
import data
from galaxy import util
from cgi import escape
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.metadata import MetadataAttributes

log = logging.getLogger(__name__)

class Tabular( data.Text ):
    """Tab delimited data"""

    """Add metadata elements"""
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=[], desc="Column types", param=metadata.ColumnTypesParameter, readonly=True, visible=False )

    def init_meta( self, dataset, copy_from=None ):
        data.Text.init_meta( self, dataset, copy_from=copy_from )
    def set_readonly_meta( self, dataset, skip=1, **kwd ):
        """Resets the values of readonly metadata elements."""
        Tabular.set_meta( self, dataset, skip=skip )
    def set_meta( self, dataset, skip=1, **kwd ):
        """
        Tries to determine the number of columns as well as those columns
        that contain numerical values in the dataset.  A skip parameter is
        used because various tabular data types reuse this function, and
        their data type classes are responsible to determine how many invalid
        comment lines should be skipped.
        """
        if dataset.has_data():
            column_types = []
 
            for i, line in enumerate( file ( dataset.file_name ) ):
                if i < skip:
                    continue
                line = line.rstrip('\r\n')
                if line and not line.startswith( '#' ):
                    elems = line.split( '\t' )
                    elems_len = len(elems)

                    if elems_len > 0:
                        """Set the columns metadata attribute"""
                        if elems_len != dataset.metadata.columns:
                            dataset.metadata.columns = elems_len

                        """Set the column_types metadata attribute"""
                        for col in range(0, elems_len):
                            col_type = None
                            val = elems[col]
                            if not col_type:
                                """See if val is an int"""
                                try:
                                    int( val )
                                    col_type = 'int'
                                except: 
                                    pass
                            if not col_type:
                                """See if val is a float"""
                                try:
                                    float( val )
                                    col_type = 'float'
                                except:
                                    if val and val.strip().lower() == 'na':
                                        col_type = 'float'
                            if not col_type:
                                """See if val is a list"""
                                val_elems = val.split(',')
                                if len( val_elems ) > 1:
                                    col_type = 'list'
                            if not col_type:
                                """All parameters are strings, so this will be the default"""
                                col_type = 'str'

                            column_types.append(col_type)
                        if len(column_types) > 0: break

                if i > 100: break # Hopefully we never get here...
            dataset.metadata.column_types = column_types
    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        try:
            out.append( '<tr>' )
            # Generate column header
            for i in range( 1, dataset.metadata.columns+1 ):
                out.append( '<th>%s</th>' % str( i ) )
            out.append( '</tr>' )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out
    def make_html_peek_rows( self, dataset, skipchars=[] ):
        out = [""]
        comments = []
        data = dataset.peek
        lines =  data.splitlines()
        for line in lines:
            line = line.rstrip( '\r\n' )
            if not line:
                continue
            comment = False
            for skipchar in skipchars:
                if line.startswith( skipchar ):
                    comments.append( line )
                    comment = True
                    break
            if comment:
                continue
            elems = line.split( '\t' )
            if len( elems ) != dataset.metadata.columns:
                # We may have an invalid comment line or invalid data
                comments.append( line )
                comment = True
                continue
            while len( comments ) > 0: # Keep comments
                try:
                    out.append( '<tr><td colspan="100%">' )
                except:
                    out.append( '<tr><td>' )
                out.append( '%s</td></tr>'  % escape( comments.pop(0) ) )
            out.append( '<tr>' )
            for elem in elems: # valid data
                elem = escape( elem )
                out.append( '<td>%s</td>' % elem )
            out.append( '</tr>' )
        # Peek may consist only of comments
        while len( comments ) > 0:
            try:
                out.append( '<tr><td colspan="100%">' )
            except:
                out.append( '<tr><td>' )
            out.append( '%s</td></tr>'  % escape( comments.pop(0) ) )
        return "".join( out )
    def display_peek( self, dataset ):
        """Returns formatted html of peek"""
        return self.make_html_table( dataset )

class Taxonomy( Tabular ):
    def __init__(self, **kwd):
        """Initialize taxonomy datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = ['Name', 'TaxId', 'Root', 'Superkingdom', 'Kingdom', 'Subkingdom',
                             'Superphylum', 'Phylum', 'Subphylum', 'Superclass', 'Class', 'Subclass',
                             'Superorder', 'Order', 'Suborder', 'Superfamily', 'Family', 'Subfamily',
                             'Tribe', 'Subtribe', 'Genus', 'Subgenus', 'Species', 'Subspecies'
                             ]

    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append( '<tr>' )
            for i, name in enumerate( self.column_names ):
                out.append( '<th>%s.%s</th>' % ( str( i+1 ), name ) )
            # This data type requires at least 24 columns in the data
            if dataset.metadata.columns - len( self.column_names ) > 0:
                for i in range( len( self.column_names ), dataset.metadata.columns ):
                    out.append( '<th>%s</th>' % str( i+1 ) )
                out.append( '</tr>' )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out

