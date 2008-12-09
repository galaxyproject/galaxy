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

log = logging.getLogger(__name__)

class Tabular( data.Text ):
    """Tab delimited data"""

    """Add metadata elements"""
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=False, no_value=0 )
    MetadataElement( name="column_types", default=[], desc="Column types", param=metadata.ColumnTypesParameter, readonly=True, visible=False, no_value=[] )

    def init_meta( self, dataset, copy_from=None ):
        data.Text.init_meta( self, dataset, copy_from=copy_from )
    def set_readonly_meta( self, dataset, skip=None, **kwd ):
        """Resets the values of readonly metadata elements."""
        Tabular.set_meta( self, dataset, overwrite = True, skip = skip )
    def set_meta( self, dataset, overwrite = True, skip = None, **kwd ):
        """
        Tries to determine the number of columns as well as those columns
        that contain numerical values in the dataset.  A skip parameter is
        used because various tabular data types reuse this function, and
        their data type classes are responsible to determine how many invalid
        comment lines should be skipped. Using None for skip will cause skip 
        to be zero, but the first line will be processed as a header.
        """
        #we treat 'overwrite' as always True (we always want to set tabular metadata when called)
        #if a tabular file has no data, it will have one column of type str
        
        num_check_lines = 100 #we will only check up to this many lines into the file
        requested_skip = skip #store original skip value to check with later
        if skip is None:
            skip = 0
        
        column_type_set_order = [ 'int', 'float', 'list', 'str'  ] #Order to set column types in
        default_column_type = column_type_set_order[-1] # Default column type is lowest in list
        column_type_compare_order = list( column_type_set_order ) #Order to compare column types
        column_type_compare_order.reverse() 
        def type_overrules_type( column_type1, column_type2 ):
            if column_type1 is None or column_type1 == column_type2:
                return False
            if column_type2 is None:
                return True
            for column_type in column_type_compare_order:
                if column_type1 == column_type:
                    return True
                if column_type2 == column_type:
                    return False
            #neither column type was found in our ordered list, this cannot happen
            raise "Tried to compare unknown column types"
        def is_int( column_text ):
            try:
                int( column_text )
                return True
            except: 
                return False
        def is_float( column_text ):
            try:
                float( column_text )
                return True
            except: 
                if column_text.strip().lower() == 'na':
                    return True #na is special cased to be a float
                return False
        def is_list( column_text ):
            return "," in column_text
        def is_str( column_text ):
            #anything, except an empty string, is True
            if column_text == "":
                return False
            return True
        is_column_type = {} #Dict to store column type string to checking function
        for column_type in column_type_set_order:
            is_column_type[column_type] = locals()[ "is_%s" % ( column_type ) ]
        def guess_column_type( column_text ):
            for column_type in column_type_set_order:
                if is_column_type[column_type]( column_text ):
                    return column_type
            return None
        
        column_types = []
        first_line_column_types = [default_column_type] # default value is one column of type str
        if dataset.has_data():
            #NOTE: if skip > num_check_lines, we won't detect any metadata, and will use default
            for i, line in enumerate( file ( dataset.file_name ) ):
                line = line.rstrip('\r\n')
                if i < skip or not line or line.startswith( '#' ):
                    continue
                
                fields = line.split( '\t' )
                for field_count, field in enumerate( fields ):
                    if field_count >= len( column_types ): #found a previously unknown column, we append None
                        column_types.append( None )
                    column_type = guess_column_type( field )
                    if type_overrules_type( column_type, column_types[field_count] ):
                        column_types[field_count] = column_type
                
                if i == 0 and requested_skip is None:
                    #this is our first line, people seem to like to upload files that have a header line, but do not start with '#' (i.e. all column types would then most likely be detected as str)
                    #we will assume that the first line is always a header (this was previous behavior - it was always skipped) when the requested skip is None
                    #we only use the data from the first line if we have no other data for a column
                    #this is far from perfect, as:
                    #1,2,3	1.1	2.2	qwerty
                    #0	0		1,2,3
                    #will detect as
                    #"column_types": ["int", "int", "float", "list"]
                    #instead of:
                    #"column_types": ["list", "float", "float", "str"]  *** would seem to be the 'Truth' by manual observation that the first line should be included as data
                    #old method would have detected as:
                    #"column_types": ["int", "int", "str", "list"]
                    first_line_column_types = column_types
                    column_types = [ None for col in first_line_column_types ]
                elif ( column_types and None not in column_types ) or i > num_check_lines:
                    #found and set all known columns, or we exceeded our max check lines
                    break
        
        #we error on the larger number of columns
        #first we pad our column_types by using data from first line
        if len( first_line_column_types ) > len( column_types ):
            for column_type in first_line_column_types[len( column_types ):]:
                column_types.append( column_type )
        
        #Now we fill any unknown (None) column_types with data from first line
        for i in range( len( column_types ) ):
            if column_types[i] is None:
                if first_line_column_types[i] is None:
                    column_types[i] = default_column_type
                else:
                    column_types[i] = first_line_column_types[i]
        
        dataset.metadata.column_types = column_types
        dataset.metadata.columns = len( column_types )
        
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
        if not dataset.peek:
            dataset.set_peek()
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

