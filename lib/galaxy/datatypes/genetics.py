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
from galaxy.web import url_for
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
                        display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s" % (base_url, url_for( controller='root' ), dataset.id, type))
                        sl = ["%sdb=%s" % (site_url,dataset.dbkey ),]
                        sl.append("&hgGenome_dataSetName=%s&hgGenome_dataSetDescription=%s" % (dataset.name, 'GalaxyGG_data'))
                        sl.append("&hgGenome_formatType=best%20guess&hgGenome_markerType=best%20guess")
                        sl.append("&hgGenome_columnLabels=first%20row&hgGenome_maxVal=&hgGenome_labelVals=")
                        sl.append("&hgGenome_maxGapToFill=25000000&hgGenome_uploadFile=%%s")
                        sl.append(ggtail)
                        s = urllib.quote_plus( ''.join(sl) )
                        link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, s, display_url )
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
    MetadataElement( name="base_name", desc="base name for all transformed versions of this genetic dataset", default="galaxy", readonly=True, set_in_upload=True)
    
    file_ext="html"
    composite_type = 'auto_primary_file'
    allow_datatype_change = False
    
    def missing_meta( self, dataset ):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if not value:
                return True
        return False

    def generate_primary_file( self, dataset = None ):
        rval = ['<html><head><title>Files for Composite Dataset (%s)</title></head><p/>This composite dataset is composed of the following files:<p/><ul>' % ( self.file_ext ) ]
        for composite_name, composite_file in self.get_composite_files( dataset = dataset ).iteritems():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append( '<li><a href="%s">%s</a>%s' % ( composite_name, composite_name, opt_text ) )
        rval.append( '</ul></html>' )
        return "\n".join( rval )

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


class Lped(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="lped"
    
    def __init__( self, **kwd ):
        Rgenetics.__init__( self, **kwd )
        self.add_composite_file( '%s.ped', description = 'Pedigree File', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.map', description = 'Map File', substitute_name_with_metadata = 'base_name', is_binary = True )


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
    
    def __init__( self, **kwd ):
        Rgenetics.__init__( self, **kwd )
        self.add_composite_file( '%s.bim', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.bed', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.fam', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.map', substitute_name_with_metadata = 'base_name', is_binary = True )


class Eigenstratgeno(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratgeno"
    
    def __init__( self, **kwd ):
        Rgenetics.__init__( self, **kwd )
        self.add_composite_file( '%s.eigenstratgeno', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.ind', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.map', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s_fo.eigenstratgeno', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        self.add_composite_file( '%s_fo.ind', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        self.add_composite_file( '%s_fo.map', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        self.add_composite_file( '%s_oo.eigenstratgeno', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        self.add_composite_file( '%s_oo.ind', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        self.add_composite_file( '%s_oo.map', substitute_name_with_metadata = 'base_name', optional = 'True', is_binary = True )
        


class Eigenstratpca(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratpca"

class Snptest(Rgenetics):
    """fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="snptest"
    
class RexpBase( Html ):
    """base class for BioC data structures in Galaxy 
    must be constructed with the pheno data in place since that
    goes into the metadata for each instance"""

    """Add metadata elements"""
    MetadataElement( name="columns", default=0, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_names", default=[], desc="Column names", readonly=True,visible=True )
    MetadataElement( name="base_name", 
    desc="base name for all transformed versions of this genetic dataset", readonly=True, default='galaxy', set_in_upload=True)
    ### Do we really need these below? can we rely on dataset.extra_files_path: os.path.join( dataset.extra_files_path, '%s.phenodata' % dataset.metadata.base_name ) ?
    ### Do these have a different purpose? Ross will need to clarify
    ### Uploading these datatypes will not work until this is sorted out (set_peek fails)...
    MetadataElement( name="pheno_path", 
    desc="Path to phenotype data for this experiment", readonly=True)
    MetadataElement( name="pheno", 
    desc="Phenotype data for this experiment", readonly=True)
    
    file_ext = None 
    
    is_binary = True
    
    allow_datatype_change = False
    
    composite_type = 'basic'
    
    def __init__( self, **kwd ):
        Html.__init__( self, **kwd )
        self.add_composite_file( '%s.phenodata', substitute_name_with_metadata = 'base_name', is_binary = True )
    
    def set_peek( self, dataset ):
        """expects a .pheno file in the extra_files_dir - ugh
        note that R is wierd and does not include the row.name in
        the header. why?"""
        p = file(dataset.metadata.pheno_path,'r').readlines() #this fails
        head = p[0].strip().split('\t')
        head.insert(0,'ChipFileName') # fix R write.table b0rken-ness
        p[0] = '\t'.join(head)
        p = '\n'.join(p)
        dataset.peek = p
        dataset.metadata.pheno = p
        dataset.blurb = 'R loadable BioC expression object for the Rexpression Galaxy toolkit'

    # stolen from Tabular
    # class Tabular( data.Text ):
    """Tab delimited data"""

    """Add metadata elements"""
    def init_meta( self, dataset, copy_from=None ):
        if copy_from:
            dataset.metadata = copy_from.metadata
            

    #def set_readonly_meta( self, dataset, skip=0, **kwd ):
    #    """Resets the values of readonly metadata elements."""
    #    RexpBase.set_meta( self, dataset, skip=skip )

    def set_readonly_meta( self, dataset, **kwd ):        
        """Resets the values of readonly metadata elements."""
        RexpBase.set_meta( self, dataset )           

    #def set_meta( self, dataset, skip=0, **kwd ):
    def set_meta( self, dataset, **kwd ):         

        """
        NOTE we apply the tabular machinary to the phenodata extracted
        from a BioC eSet or affybatch.

        """
        if not dataset.peek:
            dataset.set_peek()
        pk = dataset.peek # use the peek which is the pheno data insead of dataset (!)
        ###this is probably not the best source, can we just access the raw data directly?
        if pk:
            p = pk.split('\n')
            h = p[0].strip().split('\t') # hope is header
            h = [escape(x) for x in h]
            dataset.metadata.column_names = h
            dataset.metadata.columns = len(h)
        else:
            dataset.metadata.column_names = []
            dataset.metadata.columns = 0
            
    def make_html_table( self, dataset):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">',]
        try:
            # Generate column header
            pk = dataset.peek
            p = pk.split('\n')
            for i,row in enumerate(p):
                lrow = row.strip().split('\t')
                if i == 0:                
                    orow = ['<th>%s</th>' % escape(x) for x in lrow]
                    orow.insert(0,'<tr>')
                    orow.append('</tr>')
                else:            
                    orow = ['<td>%s</td>' % escape(x) for x in lrow]
                    orow.insert(0,'<tr>')
                    orow.append('</tr>')
                out.append(''.join(orow))
            out.append( '</table>' )
            out = "\n".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % str( exc )
        return out
    
    def display_peek( self, dataset ):
        """Returns formatted html of peek"""
        if not dataset.peek:
            dataset.set_peek()
        return self.make_html_table( dataset )
    
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/gzip'
    

class AffyBatch( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "affybatch"

    
class ESet( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "eset"


class MAList( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "malist"    


if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])

