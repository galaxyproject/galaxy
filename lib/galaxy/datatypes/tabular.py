"""
Tabular datatype

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging
import data
from galaxy import util
from cgi import escape
from galaxy.datatypes.metadata import MetadataElement

log = logging.getLogger(__name__)


class Tabular( data.Text ):
    """Tab delimited data"""

    """Provide the set of display formats supported by this datatype """
    supported_display_apps = []
    
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if not value:
                return True
        return False
        
    def make_html_table(self, data, skipchar=None):
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

    def get_estimated_display_viewport( self, dataset ):
        #TODO: fix me...
        return ('', '', '')

    def display_peek( self, dataset ):
        m_peek = self.make_html_table( dataset.peek )
        return m_peek
