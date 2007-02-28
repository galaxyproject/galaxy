"""
Interval datatypes

"""
import pkg_resources
pkg_resources.require( "bx-python" )

import logging, os, sys, time, sets, tempfile, shutil
import data
from galaxy import util
from cgi import escape
from bx.intervals.io import *

log = logging.getLogger(__name__)

#
# contain the meta columns and the words that map to it
# list aliases on the right side of the : in decreasing order of priority
#
alias_spec = { 
    'chromCol'  : [ 'chrom' , 'CHROMOSOME' , 'CHROM', 'Chromosome Name' ],  
    'startCol'  : [ 'start' , 'START', 'chromStart', 'txStart', 'Start Position (bp)' ],
    'endCol'    : [ 'end'   , 'END'  , 'STOP', 'chromEnd', 'txEnd', 'End Position (bp)'  ], 
    'strandCol' : [ 'strand', 'STRAND', 'Strand' ],
}

# a little faster lookup
alias_helper = {}
for key, value in alias_spec.items():
    for elem in value:
        alias_helper[elem] = key

class Tabular( data.Text ):
    """Tab delimited data"""

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
        
    def display_peek( self, dataset ):
        m_peek = self.make_html_table( dataset.peek )
        return m_peek

class Interval( Tabular ):
    """Tab delimited data containing interval information"""
      
    def init_meta( self, dataset ):
        for key in alias_spec:
            setattr( dataset.metadata, key, '' ) 
        setattr( dataset.metadata, 'strandCol', '0' )                 
    
    def set_peek( self, dataset ):
        dataset.peek  = data.get_file_peek( dataset.file_name )
        ## dataset.peek  = self.make_html_table( dataset.peek )
        dataset.blurb = util.commaify( str( data.get_line_count( dataset.file_name ) ) ) + " regions"
        self.set_meta( dataset )
    
    def set_meta( self, dataset, first_line_is_header=False ):
        """
        Tries to guess from the line the location number of the column for the chromosome, region start-end and strand
        """
        if dataset.has_data():
            line = file(dataset.file_name).readline().strip()
            if first_line_is_header or line[0] == '#':
                self.init_meta(dataset)
                line  = line.strip("#")
                elems = line.split("\t")
                valid = dict(alias_helper) # shrinks
                for index, col_name in enumerate(elems):
                    if col_name in valid:
                        meta_name = valid[col_name]
                        setattr(dataset.metadata, meta_name, index+1)
                        values = alias_spec[meta_name]
                        start  = values.index(col_name)
                        for lower in values[start:]:
                            del valid[lower]  # removes lower priority keys 
                dataset.mark_metadata_changed()
    
    

    def bed_viewport( self, dataset ):
        """
        Return a start position for viewing a bed file.
        """
        if dataset.has_data() and dataset.state == dataset.states.OK:
            try:
                c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
                c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
                
                peek = []
                for idx, line in enumerate(file(dataset.file_name)):
                    if line[0] != '#':
                        peek.append( line.split() )
                        if idx > 10:
                            break

                chr, start, stop = peek[0][c], int( peek[0][s] ), int( peek[0][e] )
                
                for p in peek[1:]:
                    if p[0] == chr:
                        start = min( start, int( p[s] ) )
                        stop  = max( stop, int( p[e] ) )
            except Exception, exc:
                log.error( 'Viewport generation error -> %s ' % str(exc) )
                chr, start, stop = 'chr1', 1, 1000
            return "%s:%d-%d" % ( chr, start, stop ) 
        else:
            return ""

    def as_bedfile( self, dataset ):
        '''Returns a file that contains only the bed data'''
        fd, temp_name = tempfile.mkstemp()
        c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
        c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
        if t >= 0: # strand column exists
            for elems in util.file_iter(dataset.file_name):
                tmp = [ elems[c], elems[s], elems[e], '1', '2', elems[t] ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )
        else:
            for elems in util.file_iter(dataset.file_name):
                tmp = [ elems[c], elems[s], elems[e] ]
                os.write(fd, '%s\n' % '\t'.join(tmp) )    
        os.close(fd)
        return temp_name

    def validate( self, dataset ):
        """Validate an interval file using the bx GenomicIntervalReader"""
        errors = list()
        c, s, e, t = dataset.metadata.chromCol, dataset.metadata.startCol, dataset.metadata.endCol, dataset.metadata.strandCol 
        c, s, e, t = int(c)-1, int(s)-1, int(e)-1, int(t)-1
        infile = open(dataset.file_name, "r")
        reader = GenomicIntervalReader(
            infile,
            chrom_col = c,
            start_col = s,
            end_col = e,
            strand_col = t)

        while True:
            try:
                reader.next()
            except ParseError, e:
                errors.append(e)
            except StopIteration:
                infile.close()
                return errors

class Bed( Interval ):
    """Tab delimited data in BED format"""
    def init_meta( self, dataset ):
        dataset.metadata.chromCol  = 1
        dataset.metadata.startCol  = 2
        dataset.metadata.endCol    = 3
        dataset.metadata.strandCol = 6
        dataset.mark_metadata_changed()
    def set_meta( self, dataset ):
        # metadata already set
        pass

class Gff( Tabular ):
    """Tab delimited data in Gff format"""
    def __init__(self, id=None):
        data.Text.__init__(self, id=id)
    
    def make_html_table(self, data):
        return Tabular.make_html_table(self, data, skipchar='#')

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])        
