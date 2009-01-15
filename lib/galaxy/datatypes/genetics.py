"""
rgenetics datatypes 
Use at your peril
Ross Lazarus
for the rgenetics and galaxy projects 

genome graphs datatypes derived from Interval datatypes
genome graphs datasets have a header row with appropriate columnames
The first column is always the marker - eg columname = rs, first row= rs12345 if the rows are snps
subsequent row values are all numeric ! Will fail if any non numeric (eg '+' or 'NA') values
ross lazarus for rgenetics
august 20 2007
"""

import logging, os, sys, time, sets, tempfile, shutil
import data
from galaxy import util
from cgi import escape
import urllib
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
#from galaxy.datatypes.data import Text
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.images import Html

log = logging.getLogger(__name__)



class GenomeGraphs( Tabular ):
    """Tab delimited data containing a marker id and any number of numeric values"""

    """Add metadata elements"""
    MetadataElement( name="markerCol", default=1, desc="Marker ID column", param=metadata.ColumnParameter )
    MetadataElement( name="columns", default=3, desc="Number of columns", readonly=True )
    MetadataElement( name="column_types", default=[], desc="Column types", readonly=True, visible=False )
    file_ext = 'gg'

    def __init__(self, **kwd):
        """Initialize gg datatype, by adding UCSC display apps"""
        Tabular.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'Genome Graph', 'as_ucsc_display_file', 'ucsc_links' )
    
    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek( dataset.file_name )
            dataset.blurb = util.commaify( str( data.get_line_count( dataset.file_name ) ) ) + " rows"
            #i don't think set_meta should not be called here, it should be called separately
            self.set_meta( dataset )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
        
    def get_estimated_display_viewport( self, dataset ):
        """Return a chrom, start, stop tuple for viewing a file."""
        raise notImplemented

    def as_ucsc_display_file( self, dataset, **kwd ):
        """Returns file"""
        return file(dataset.file_name,'r')

    def ucsc_links( self, dataset, type, app, base_url ):
        """ from the ever-helpful angie hinrichs angie@soe.ucsc.edu
        a genome graphs call looks like this 
        http://genome.ucsc.edu/cgi-bin/hgGenome?clade=mammal&org=Human&db=hg18&hgGenome_dataSetName=dname
        &hgGenome_dataSetDescription=test&hgGenome_formatType=best%20guess&hgGenome_markerType=best%20guess
        &hgGenome_columnLabels=best%20guess&hgGenome_maxVal=&hgGenome_labelVals=
        &hgGenome_maxGapToFill=25000000&hgGenome_uploadFile=http://galaxy.esphealth.org/datasets/333/display/index
        &hgGenome_doSubmitUpload=submit
                Galaxy gives this for an interval file
        http://genome.ucsc.edu/cgi-bin/hgTracks?db=hg18&position=chr1:1-1000&hgt.customText=
        http%3A%2F%2Fgalaxy.esphealth.org%2Fdisplay_as%3Fid%3D339%26display_app%3Ducsc
        """
        ret_val = []
        ggtail = '&hgGenome_doSubmitUpload=submit'
        if not dataset.dbkey:
              dataset.dbkey = 'hg18' # punt!
        if dataset.has_data:
              for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
                    if site_name in app.config.ucsc_display_sites:
                        site_url = site_url.replace('/hgTracks?','/hgGenome?') # for genome graphs
                        display_url = urllib.quote_plus( "%s/display_as?id=%i&display_app=%s" % (base_url, dataset.id, type) )
                        sl = ["%sdb=%s" % (site_url,dataset.dbkey ),]
                        sl.append("&hgGenome_dataSetName=%s&hgGenome_dataSetDescription=%s" % (dataset.name, 'GalaxyGG_data'))
                        sl.append("&hgGenome_formatType=best%20guess&hgGenome_markerType=best%20guess")
                        sl.append("&hgGenome_columnLabels=first%20row&hgGenome_maxVal=&hgGenome_labelVals=")
                        sl.append("&hgGenome_maxGapToFill=25000000&hgGenome_uploadFile=")
                        s = ''.join(sl)
                        link = "%s%s%s" % (s, display_url, ggtail )
                        ret_val.append( (site_name, link) )
        return ret_val

    def validate( self, dataset ):
        """Validate a gg file - all numeric after header row"""
        errors = list()
        infile = open(dataset.file_name, "r")
        header= infile.next() # header
        for i,row in enumerate(infile):
           ll = row.strip().split('\t')
           badvals = []
           for j,x in enumerate(ll):
              try:
                x = float(x)
              except:
                badval.append('col%d:%s' % (j+1,x))
        if len(badvals) > 0:
            errors.append('row %d, %s' % (' '.join(badvals)))
            return errors 
        
    def repair_methods( self, dataset ):
        """Return options for removing errors along with a description"""
        return [("lines","Remove erroneous lines")]
    

class Rgenetics(Html):      
    """class to use for rgenetics"""
    """Add metadata elements"""

    MetadataElement( name="base_name", desc="base name for all transformed versions of this genetic dataset", readonly=True)
    file_ext="html"

    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if not value:
                return True
        return False

class SNPMatrix(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="snpmatrix"

    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            dataset.peek  = "Binary RGenetics file"
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff( self, filename ):
        """
        """
        return True

class Lped(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="lped"

class Pphe(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="pphe"

class Lmap(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="lmap"

class Fphe(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="fphe"

class Phe(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="phe"


class Fped(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="fped"


class Pbed(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="pbed"

class Eigenstratgeno(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratgeno"

class Eigenstratpca(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratpca"

class Snptest(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="snptest"



if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])

