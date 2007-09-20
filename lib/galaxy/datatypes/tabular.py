"""
Tabular datatype

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging
import data, sniff
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
    MetadataElement( name="column_types", default=[], desc="Column types", readonly=True, visible=False )

    def init_meta( self, dataset, copy_from=None ):
        data.Text.init_meta( self, dataset, copy_from=copy_from )
        
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if not value:
                return True
        return False

    def set_meta( self, dataset ):
        """
        Tries to determine the number of columns as well as those columns
        that contain numerical values in the dataset
        """
        if dataset.has_data():
            column_types = []
            format = sniff.guess_ext( dataset.file_name )

            if dataset.extension != format:
                """
                We need to rely on the ability of our sniffer to properly detect datatypes here since
                there are many ways that the datatype could be improperly set.  
                TODO: we may want to automatically convert the datset to the proper datatype here,
                but for now we'll leave it and just rely on the value in format.
                """
                pass

            """
            The 'proceed' value allows us to skip different numbers of lines based on the data 
            format (type).  We need this because different formats can include lines of information 
            that are not properly commented (properly commented lines start with a '#' character).
            """  
            proceed = False
            col1_startswith = ['chr', 'chl', 'groupun', 'reftig_', 'scaffold', 'super_', 'vcho']
 
            for i, line in enumerate( file ( dataset.file_name ) ):
                line = line.rstrip('\r\n')
                valid = True
                if line and not line.startswith( '#' ):
                    elems = line.split( '\t' )
                    elems_len = len(elems)

                    if elems_len > 0:
                        if format == 'bed':
                            for str in col1_startswith:
                                if elems[0].lower().startswith(str):
                                    proceed = True
                                    break
                        elif format == 'interval':
                            if elems_len > 2:
                                try:
                                    map( int, [elems[1], elems[2]] )
                                    proceed = True
                                except:
                                    pass  # proceed is False
                        elif format == 'gff':
                            if elems_len == 9:
                                try:
                                    map( int, [hdr[3], hdr[4]] )
                                    proceed = True
                                except:
                                    pass
                        elif format == 'gff3':
                            valid_gff3_strand = ['+', '-', '.', '?']
                            valid_start = False
                            valid_end = False
                            if elems_len == 9:
                                try:
                                    start = int(hdr[3])
                                    valid_start = True                                    
                                except:
                                    if hdr[3] == '.':
                                        valid_start = True                                        
                                try:
                                    end = int(hdr[4])
                                    valid_end = True
                                except:
                                    if hdr[4] == '.':
                                        valid_end = True
                                    srand = hdr[6]
                                if valid_start and valid_end and start < end and strand in valid_gff3_strand:
                                    proceed = True                
                        elif format=='wig':
                            try:
                                int( elems[0] )
                                proceed = True
                            except:
                                for str in col1_startswith:
                                    if elems[0].lower().startswith(str):
                                        proceed = True
                                        break
                        elif ( format =='tabular' or format == "customtrack" or format == 'gbrowsetrack' ) and i > 1:
                            proceed = True
            
                        if proceed:
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

    def make_html_table(self, data, skipchar=None):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        first = True
        comments = []
        try:
            lines =  data.splitlines()
            for line in lines:
                if skipchar and line.startswith(skipchar):
                    comments.append(line.strip())
                    continue
                line = line.strip()
                if not line:
                    continue
                elems = line.split("\t")
                
                if first: #generate header
                    first = False
                    out.append('<tr>')
                    for index, elem in enumerate(elems):
                        out.append("<th>%s</th>" % (index+1))
                    out.append('</tr>')
                
                while len(comments)>0:
                    out.append('<tr><td colspan="100%">')
                    out.append(escape(comments.pop(0)))
                    out.append('</td></tr>')
                
                out.append('<tr>') # body
                for elem in elems:
                    elem = escape(elem)
                    out.append("<td>%s</td>" % elem)
                out.append('</tr>')
            out.append('</table>')
            out = "".join(out)
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out

    def display_peek( self, dataset ):
        """Returns formated html of peek"""
        m_peek = self.make_html_table( dataset.peek )
        return m_peek

    def before_edit( self, dataset ):
        data.Text.before_edit( self, dataset )
        if self.missing_meta( dataset ):
            self.set_meta( dataset )    
