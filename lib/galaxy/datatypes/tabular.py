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
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True )
    MetadataElement( name="dbkey", desc="Database/Build", default="?", param=metadata.SelectParameter, multiple=False, values=util.dbnames )

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
        Tries to determine the number of columns in the dataset
        """
        if dataset.has_data():
            for i, line in enumerate( file(dataset.file_name) ):
                line = line.rstrip('\r\n')
                if line and not line.startswith('#') and len(line) > 0:
                    elems = line.split('\t')
                    if len(elems) != dataset.metadata.columns:
                        dataset.metadata.columns = len(elems)
                        break
                if i == 30:
                    break

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
        try:
            maxcols = 0
            count = 0
            for line in open( dataset.file_name ):
                line = line.rstrip('\r\n')
                if line and not line.startswith( '#' ):
                    count += 1
                    """
                    We should be able to figure out the number of columns within 30 lines
                    """
                    if count > 30: 
                        break
                    cols = len( line.split("\t") )
                    if cols > maxcols: 
                        maxcols = cols
            setattr( dataset.metadata, "columns", maxcols )
        except:
            pass        
