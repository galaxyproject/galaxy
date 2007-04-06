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
      
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if key in ['strandCol']: continue #we skip check for strand column here, since it is considered optional
            if not value:
                return True
        return False
    
    
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
            if len(line)>0 and (first_line_is_header or line[0] == '#'):
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
        if t >= 0: # strand column (should) exists
            for elems in util.file_iter(dataset.file_name):
                strand = "+"
                if t<len(elems): strand = elems[t]
                tmp = [ elems[c], elems[s], elems[e], '1', '2', strand ]
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

    def repair_methods( self, dataset ):
        """Return options for removing errors along with a description"""
        return [("lines","Remove erroneous lines")]

class Bed( Interval ):
    """Tab delimited data in BED format"""
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        return Tabular.missing_meta(self, dataset)
    
    def init_meta( self, dataset ):
        dataset.metadata.chromCol  = 1
        dataset.metadata.startCol  = 2
        dataset.metadata.endCol    = 3
        dataset.metadata.strandCol = 6
        dataset.mark_metadata_changed()
        
    def set_meta( self, dataset ):
        """
        Overrides the default setting for dataset.metadata.strandCol for BED
        files that do not contain a strand column.  This will result in changing
        the format of the file from BED to Interval.
        """
        valid_bed_data = False
        if dataset.has_data():
            for i, line in enumerate( file(dataset.file_name) ):
                line = line.strip()
                if len(line) > 0 and ( line.startswith('chr') or line.startswith('scaff') ):
                    valid_bed_data = True
                    elems = line.split("\t")
                    if len(elems) < 6:
                        dataset.metadata.strandCol = 0
                        dataset.mark_metadata_changed()
                    break
                if i == 30:
                    break
        if not valid_bed_data:
            dataset.metadata.strandCol = 0
            dataset.mark_metadata_changed()
        
    def as_bedfile( self, dataset ):
        '''Returns a file that contains only the bed data. If bed 6+, treat as interval.'''
        for line in open(dataset.file_name):
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            fields = line.split('\t')
            #check to see if this file doesn't conform to strict genome browser accepted bed
            try:
                if len(fields) > 12:
                    return Interval.as_bedfile(self, dataset) #too many fields
                if len(fields) > 6:
                    int(fields[6])
                    if len(fields) > 7:
                        int(fields[7])
                        if len(fields) > 8:
                            if int(fields[8]) != 0:
                                return Interval.as_bedfile(self, dataset)
                            if len(fields) > 9:
                                int(fields[9])
                                if len(fields) > 10:
                                    fields2 = fields[10].rstrip(",").split(",") #remove trailing comma and split on comma
                                    for field in fields2: 
                                        int(field)
                                    if len(fields) > 11:
                                        fields2 = fields[11].rstrip(",").split(",") #remove trailing comma and split on comma
                                        for field in fields2:
                                            int(field)
            except: return Interval.as_bedfile(self, dataset)
            #only check first line for proper form
            break
            
        try: return dataset.file_name
        except: return "This item contains no content"

class Gff( Tabular ):
    """Tab delimited data in Gff format"""
    def __init__(self, id=None):
        data.Text.__init__(self, id=id)
    
    def make_html_table(self, data):
        return Tabular.make_html_table(self, data, skipchar='#')

#Extend Tabular type, since interval tools will fail on track def line (we should fix this)
#This is a skeleton class for now, allows viewing at ucsc and formatted peeking.
class CustomTrack ( Tabular ):
    """UCSC CustomTrack"""
    def __init__(self, id=None):
        data.Text.__init__(self, id=id)
    
    def make_html_table(self, dataset):
        return Tabular.make_html_table(self, dataset, skipchar='track')
    
    def bed_viewport( self, dataset ):
        return "." #Not ideal solution, will cause genome browser to give warning
    
    def as_bedfile( self, dataset ):
        return dataset.file_name

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])        
