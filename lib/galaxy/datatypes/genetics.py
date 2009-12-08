"""
rgenetics datatypes 
Ross Lazarus
for the rgenetics and galaxy projects 

genome graphs datatypes derived from Interval datatypes
genome graphs datasets have a header row with appropriate columnames
The first column is always the marker - eg columname = rs, first row= rs12345 if the rows are snps
subsequent row values are all numeric ! Will fail if any non numeric (eg '+' or 'NA') values
ross lazarus for rgenetics
august 20 2007
"""
import logging, os, sys, time, tempfile, shutil, string, glob
import data
from galaxy import util
from cgi import escape
import urllib, binascii
from galaxy.web import url_for
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.data import Text
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.images import Html
from galaxy.datatypes.interval import Interval
from galaxy.util.hash_util import *

log = logging.getLogger(__name__)

class GenomeGraphs(Interval):

    """gg version viewable at ucsc of Gff format"""
    file_ext = "gg"
    column_names = [ 'Seqname', 'Source', 'Feature', 'Start', 'End', 'Score', 'Strand', 'Frame', 'Group' ]

    """Add metadata elements"""
    MetadataElement( name="columns", default=9, desc="Number of columns", readonly=True, visible=False )
    MetadataElement( name="column_types", default=['str','str','str','int','int','int','str','str','str'], param=metadata.ColumnTypesParameter, desc="Column types", readonly=True, visible=False )
    MetadataElement( name="chromCol", default=1, desc="Chrom column", param=metadata.ColumnParameter )
    MetadataElement( name="startCol", default=4, desc="Start column", param=metadata.ColumnParameter )
    MetadataElement( name="endCol", default=5, desc="End column", param=metadata.ColumnParameter )
    MetadataElement( name="strandCol", desc="Strand column (click box & select)", param=metadata.ColumnParameter, optional=True, no_value=0 )
    ###do we need to repeat these? they are the same as should be inherited from interval type
    
    def __init__(self, **kwd):
        """Initialize datatype, by adding GBrowse display app"""
        Interval.__init__(self, **kwd)
        self.add_display_app ( 'ucsc', 'display at UCSC', 'as_ucsc_display_file', 'ucsc_links' )
    def as_ucsc_display_file( self, dataset, **kwd ):
        return open( dataset.file_name )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_meta( self, dataset, overwrite = True, **kwd ):
        i = 0
        for i, line in enumerate( file ( dataset.file_name ) ):
            line = line.rstrip('\r\n')
            if line and not line.startswith( '#' ):
                elems = line.split( '\t' )
                if len(elems) == 9:
                    try:
                        int( elems[3] )
                        int( elems[4] )
                        break
                    except:
                        pass
        Interval.set_meta( self, dataset, overwrite = overwrite, skip = i )
    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append( '<tr>' )
            for i, name in enumerate( self.column_names ):
                out.append( '<th>%s.%s</th>' % ( str( i+1 ), name ) )
            out.append( self.make_html_peek_rows( dataset, skipchars=skipchars ) )
            out.append( '</table>' )
            out = "".join( out )
        except Exception, exc:
            out = "Can't create peek %s" % exc
        return out
    def get_estimated_display_viewport( self, dataset ):
        """
        Return a chrom, start, stop tuple for viewing a file.  There are slight differences between gff 2 and gff 3
        formats.  This function should correctly handle both...
        """
        if True or (dataset.has_data() and dataset.state == dataset.states.OK):
            try:
                seqid = ''
                start = 2147483647  # Maximum value of a signed 32 bit integer ( 2**31 - 1 )
                stop = 0
                for i, line in enumerate( file( dataset.file_name ) ):
                    if i == 0: # track stuff there
                        continue
                    line = line.rstrip( '\r\n' )
                    if not line:
                        continue
                    if not line.startswith( '#' ):
                        elems = line.split( '\t' )
                        if not seqid:
                            # We can only set the viewport for a single chromosome
                            seqid = elems[0]
                        if seqid == elems[0]:
                            # Make sure we have not spanned chromosomes
                            start = min( start, int( elems[3] ) )
                            stop = max( stop, int( elems[4] ) )
                        else:
                            # We've spanned a chromosome
                            break
                    if i > 10: # span 10 features
                        break
            except:
                 seqid, start, stop = ( '', '', '' )
            return ( seqid, str( start ), str( stop ) )
        else:
            return ( '', '', '' )
    def gbrowse_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport( dataset )
            seqid = viewport_tuple[0]
            start = viewport_tuple[1]
            stop = viewport_tuple[2]
            if seqid and start and stop:
                for site_name, site_url in util.get_gbrowse_sites_by_build( dataset.dbkey ):
                    if site_name in app.config.gbrowse_display_sites:
                        link = "%s?start=%s&stop=%s&ref=%s&dbkey=%s" % ( site_url, start, stop, seqid, dataset.dbkey )
                        ret_val.append( ( site_name, link ) )
        return ret_val
    def ucsc_links( self, dataset, type, app, base_url ):
        ret_val = []
        if dataset.has_data:
            viewport_tuple = self.get_estimated_display_viewport(dataset)
            if viewport_tuple:
                chrom = viewport_tuple[0]
                start = viewport_tuple[1]
                stop = viewport_tuple[2]
                if start == '' or int(start) < 1:
                    start='1'
                if stop == '' or int(stop) <= start:
                    stop = '%d' % (int(start) + 10000)
                for site_name, site_url in util.get_ucsc_by_build(dataset.dbkey):
                    if site_name in app.config.ucsc_display_sites:
                        # HACK: UCSC doesn't support https, so force http even
                        # if our URL scheme is https.  Making this work
                        # requires additional hackery in your upstream proxy.
                        # If UCSC ever supports https, remove this hack.
                        internal_url = "%s" % url_for( controller='dataset',
                                dataset_id=dataset.id, action='display_at', filename='ucsc_' + site_name )
                        if base_url.startswith( 'https://' ):
                            base_url = base_url.replace( 'https', 'http', 1 )
                        display_url = urllib.quote_plus( "%s%s/display_as?id=%i&display_app=%s&authz_method=display_at" % (base_url, url_for( controller='root' ), dataset.id, type) )
                        redirect_url = urllib.quote_plus( "%sdb=%s&position=%s:%s-%s&hgt.customText=%%s" % (site_url, dataset.dbkey, chrom, start, stop) )
                        link = '%s?redirect_url=%s&display_url=%s' % ( internal_url, redirect_url, display_url )
                        ret_val.append( (site_name, link) )
            else:
                log.debug('@@@ gg ucsc_links - no viewport_tuple')
        return ret_val
    def sniff( self, filename ):
        """
        Determines whether the file is in gff format
        
        GFF lines have nine required fields that must be tab-separated.
        """
        f = open(filename,'r')
        headers = f.readline().split
        if headers[0].lower() == 'track':
            headers = f.readline.split()
        #headers = get_headers( filename, '\t' )
        try:
            if len(headers) < 2:
                return False
            for hdr in headers:
                if hdr and hdr[0].startswith( '##gff-version' ) and hdr[0].find( '2' ) < 0:
                    return False
                if hdr and hdr[0] and not hdr[0].startswith( '#' ):
                    if len(hdr) != 9:
                        return False
                    try:
                        int( hdr[3] )
                        int( hdr[4] )
                    except:
                        return False
                    if hdr[5] != '.':
                        try:
                            score = int(hdr[5])
                        except:
                            return False
                        if (score < 0 or score > 1000):
                            return False
                    if hdr[6] not in data.valid_strand:
                        return False
            return True
        except:
            return False

class rgTabList(Tabular):
    """
    for sampleid and for featureid lists of exclusions or inclusions in the clean tool
    featureid subsets on statistical criteria -> specialized display such as gg
    """    
    file_ext = "rgTList"

    def __init__(self, **kwd):
        """Initialize featurelistt datatype"""
        Tabular.__init__( self, **kwd )
        self.column_names = []
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def make_html_table( self, dataset, skipchars=[] ):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">']
        comments = []
        try:
            # Generate column header
            out.append( '<tr>' )
            for i, name in enumerate( self.column_names ):
                out.append( '<th>%s.%s</th>' % ( str( i+1 ), name ) )
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

class rgSampleList(rgTabList):
    """
    for sampleid exclusions or inclusions in the clean tool
    output from QC eg excess het, gender error, ibd pair member,eigen outlier,excess mendel errors,...
    since they can be uploaded, should be flexible
    but they are persistent at least
    same infrastructure for expression?
    """    
    file_ext = "rgSList"

    def __init__(self, **kwd):
        """
        Initialize samplelist datatype
        """
        rgTabList.__init__( self, **kwd )
        self.column_names[0] = 'FID'
        self.column_names[1] = 'IID'
        # this is what Plink wants as at 2009
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def sniff(self,filename):
        """
        """
        infile = open(dataset.file_name, "r")
        header= infile.next() # header
        if header[0] == 'FID' and header[1] == 'IID':
            return True
        else:
            return False
        
class rgFeatureList( rgTabList ):
    """
    for featureid lists of exclusions or inclusions in the clean tool
    output from QC eg low maf, high missingness, bad hwe in controls, excess mendel errors,...
    featureid subsets on statistical criteria -> specialized display such as gg
    same infrastructure for expression?
    """    
    file_ext = "rgFList"

    def __init__(self, **kwd):
        """Initialize featurelist datatype"""
        rgTabList.__init__( self, **kwd )
        for i,s in enumerate(['#FeatureId', 'Chr', 'Genpos', 'Mappos']):
            self.column_names[i] = s
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Rgenetics(Html):      
    """
    class to use for rgenetics
    """
    MetadataElement( name="base_name", desc="base name for all transformed versions of this genetic dataset", default="rgenetics", readonly=True, set_in_upload=True)
    
    composite_type = 'auto_primary_file'
    allow_datatype_change = False
    file_ext = 'rgenetics'

    def missing_meta( self, dataset=None, **kwargs):
        """Checks for empty meta values"""
        for key, value in dataset.metadata.items():
            if not value:
                return True
        return False
    def generate_primary_file( self, dataset = None ):
        rval = ['<html><head><title>Rgenetics Galaxy Composite Dataset </title></head><p/>']
        rval.append('<div>This composite dataset is composed of the following files:<p/><ul>')
        for composite_name, composite_file in self.get_composite_files( dataset = dataset ).iteritems():
            opt_text = ''
            if composite_file.optional:
                opt_text = ' (optional)'
            rval.append( '<li><a href="%s" type="application/binary">%s</a>%s' % ( composite_name, composite_name, opt_text ) )
        rval.append( '</ul></div></html>' )
        return "\n".join( rval )
    def regenerate_primary_file(self,dataset):
        """
        cannot do this until we are setting metadata 
        """
        def fix(oldpath,newbase):
           old,e = os.path.splitext(oldpath)
           head,rest = os.path.split(old)
           newpath = os.path.join(head,newbase)
           newpath = '%s%s' % (newpath,e)
           if oldpath <> newpath:
               shutil.move(oldpath,newpath)
           return newpath
        bn = dataset.metadata.base_name
        efp = dataset.extra_files_path
        flist = os.listdir(efp)
        proper_base = bn
        rval = ['<html><head><title>Files for Composite Dataset %s</title></head><p/>Comprises the following files:<p/><ul>' % (bn)]
        for i,fname in enumerate(flist):
            newpath = fix(os.path.join(efp,fname),proper_base)
            sfname = os.path.split(newpath)[-1] 
            rval.append( '<li><a href="%s">%s</a>' % ( sfname, sfname ) )
        rval.append( '</ul></html>' )
        f = file(dataset.file_name,'w')
        f.write("\n".join( rval ))
        f.write('\n')
        f.close()
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_meta( self, dataset, **kwd ):
        """
        for lped/pbed eg
        """
        if kwd.get('overwrite') == False:
            #log.debug('@@@ rgenetics set_meta called with overwrite = False')
            return True
        try:
            efp = dataset.extra_files_path
        except: 
            #log.debug('@@@rgenetics set_meta failed %s - dataset %s has no efp ?' % (sys.exc_info()[0], dataset.name))
            return False
        try:
            flist = os.listdir(efp)
        except:
            #log.debug('@@@rgenetics set_meta failed %s - dataset %s has no efp ?' % (sys.exc_info()[0],dataset.name))
            return False
        if len(flist) == 0:
            #log.debug('@@@rgenetics set_meta failed - %s efp %s is empty?' % (dataset.name,efp))
            return False
        bn = None
        for f in flist:
           n,e = os.path.splitext(f)[0]                  
           if (not bn) and e in ('.ped','.map','.bim','.fam'):
                bn = n
                dataset.metadata.base_name = bn
        if not bn:
            bn = '?'
        self.regenerate_primary_file(dataset)
        if not dataset.info:           
                dataset.info = 'Galaxy genotype datatype object'
        if not dataset.blurb:
               dataset.blurb = 'Composite file - Rgenetics Galaxy toolkit'
        return True

class SNPMatrix(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="snpmatrix"

    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek  = "Binary RGenetics file"
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def sniff(self,filename):
        """
        need to check the file header hex code
        """
        infile = open(dataset.file_name, "b")
        head = infile.read(16)
        head = [hex(x) for x in head]
        if head <> '':
            return False
        else:
            return True

class Lped(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="lped"
    
    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.ped', description = 'Pedigree File', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.map', description = 'Map File', substitute_name_with_metadata = 'base_name', is_binary = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Pphe(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="pphe"

    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.pphe', description = 'Plink Phenotype File', substitute_name_with_metadata = 'base_name' )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Lmap(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="lmap"

    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Fphe(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="fphe"

    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.fphe', description = 'FBAT Phenotype File', substitute_name_with_metadata = 'base_name' )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Phe(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="phe"

    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.phe', description = 'Phenotype File', substitute_name_with_metadata = 'base_name' )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Fped(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="fped"

    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.fped', description = 'FBAT format pedfile', substitute_name_with_metadata = 'base_name' )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Pbed(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="pbed"
    
    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.bim', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.bed', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.fam', substitute_name_with_metadata = 'base_name', is_binary = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Eigenstratgeno(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratgeno"
    
    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.eigenstratgeno', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.ind', substitute_name_with_metadata = 'base_name', is_binary = True )
        self.add_composite_file( '%s.map', substitute_name_with_metadata = 'base_name', is_binary = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Eigenstratpca(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="eigenstratpca"

    def __init__( self, **kwd ):
        Rgenetics.__init__(self, **kwd)
        self.add_composite_file( '%s.eigenstratpca', description = 'Eigenstrat PCA file', substitute_name_with_metadata = 'base_name' )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Snptest(Rgenetics):
    """
    fake class to distinguish different species of Rgenetics data collections
    """
    file_ext="snptest"
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Pheno(Tabular):
    """
    base class for pheno files
    """
    file_ext = 'pheno'
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class RexpBase( Html ):
    """
    base class for BioC data structures in Galaxy 
    must be constructed with the pheno data in place since that
    goes into the metadata for each instance
    """
    MetadataElement( name="columns", default=0, desc="Number of columns",  visible=True )
    MetadataElement( name="column_names", default=[], desc="Column names", visible=True )
    MetadataElement(name="pheCols",default=[],desc="Select list for potentially interesting variables",visible=True)
    MetadataElement( name="base_name", 
    desc="base name for all transformed versions of this expression dataset", default='rexpression', set_in_upload=True)
    MetadataElement( name="pheno_path", desc="Path to phenotype data for this experiment", default="rexpression.pheno", visible=True)
    file_ext = 'rexpbase'
    html_table = None
    is_binary = True
    composite_type = 'auto_primary_file'
    allow_datatype_change = False
    
    def __init__( self, **kwd ):
        Html.__init__(self,**kwd)
        self.add_composite_file( '%s.pheno', description = 'Phenodata tab text file', 
          substitute_name_with_metadata = 'base_name', is_binary=True)
    def generate_primary_file( self, dataset = None ):
        """
        This is called only at upload to write the html file
        cannot rename the datasets here - they come with the default unfortunately
        """
        return '<html><head></head><body>AutoGenerated Primary File for Composite Dataset</body></html>'
    def get_phecols(self, phenolist=[], maxConc=20):
        """
        sept 2009: cannot use whitespace to split - make a more complex structure here
        and adjust the methods that rely on this structure
        return interesting phenotype column names for an rexpression eset or affybatch
        to use in array subsetting and so on. Returns a data structure for a
        dynamic Galaxy select parameter.
        A column with only 1 value doesn't change, so is not interesting for
        analysis. A column with a different value in every row is equivalent to a unique
        identifier so is also not interesting for anova or limma analysis - both these
        are removed after the concordance (count of unique terms) is constructed for each
        column. Then a complication - each remaining pair of columns is tested for 
        redundancy - if two columns are always paired, then only one is needed :)
        """
        for nrows,row in enumerate(phenolist): # construct concordance
            if len(row.strip()) == 0:
                break
            row = row.strip().split('\t')
            if nrows == 0: # set up from header
               head = row
               totcols = len(row) 
               concordance = [{} for x in head] # list of dicts
            else:
                for col,code in enumerate(row): # keep column order correct
                    if col >= totcols:
                          log.warning('### get_phecols error in pheno file - row %d col %d (%s) longer than header %s' % (nrows, col, row, head))
                    else:
                        concordance[col].setdefault(code,0) # first one is zero
                        concordance[col][code] += 1 
        useCols = []
        useConc = [] # columns of interest to keep
        nrows = len(phenolist)
        nrows -= 1 # drop head from count
        for c,conc in enumerate(concordance): # c is column number
            if (len(conc) > 1) and (len(conc) < min(nrows,maxConc)): # not all same and not all different!!
                useConc.append(conc) # keep concordance
                useCols.append(c) # keep column
        nuse = len(useCols)
        # now to check for pairs of concordant columns - drop one of these.
        delme = []
        p = phenolist[1:] # drop header 
        plist = [x.strip().split('\t') for x in p] # list of lists
        phe = [[x[i] for i in useCols] for x in plist if len(x) >= totcols] # strip unused data 
        for i in range(0,(nuse-1)): # for each interesting column
            for j in range(i+1,nuse):
                kdict = {}
                for row in phe: # row is a list of lists
                    k = '%s%s' % (row[i],row[j]) # composite key
                    kdict[k] = k
                if (len(kdict.keys()) == len(concordance[useCols[j]])): # i and j are always matched
                    delme.append(j)
        delme = list(set(delme)) # remove dupes     
        listCol = [] 
        delme.sort()
        delme.reverse() # must delete from far end!
        for i in delme:
            del useConc[i] # get rid of concordance 
            del useCols[i] # and usecols entry
        for i,conc in enumerate(useConc): # these are all unique columns for the design matrix
                ccounts = [(conc.get(code,0),code) for code in conc.keys()] # decorate
                ccounts.sort()
                cc = [(x[1],x[0]) for x in ccounts] # list of code count tuples
                codeDetails = (head[useCols[i]],cc) # ('foo',[('a',3),('b',11),..])
                listCol.append(codeDetails)
        if len(listCol) > 0:
            res = listCol
            # metadata.pheCols becomes [('bar;22,zot;113','foo'), ...]
        else:
            res = [('no usable phenotype columns found',[('?',0),]),]     
        return res

    def get_pheno(self,dataset):
        """
        expects a .pheno file in the extra_files_dir - ugh
        note that R is wierd and adds the row.name in
        the header so the columns are all wrong - unless you tell it not to.
        A file can be written as  
        write.table(file='foo.pheno',pData(foo),sep='\t',quote=F,row.names=F)
        """
        p = file(dataset.metadata.pheno_path,'r').readlines() 
        if len(p) > 0: # should only need to fix an R pheno file once
            head = p[0].strip().split('\t')
            line1 = p[1].strip().split('\t')
            if len(head) < len(line1):
                head.insert(0,'ChipFileName') # fix R write.table b0rken-ness
                p[0] = '\t'.join(head)
        else:
            p = []
        return '\n'.join(p)
    def set_peek( self, dataset, is_multi_byte=False ):
        """
        expects a .pheno file in the extra_files_dir - ugh
        note that R is wierd and does not include the row.name in
        the header. why?
        """
        if not dataset.dataset.purged:
            pp = os.path.join(dataset.extra_files_path,'%s.pheno' % dataset.metadata.base_name)
            try:
            	p = file(pp,'r').readlines()
            except:
            	p = ['##failed to find %s' % pp,]
            dataset.peek = ''.join(p[:5])
            dataset.blurb = 'Galaxy Rexpression composite file'
        else:
            dataset.peek = 'file does not exist\n'
            dataset.blurb = 'file purged from disk'
    def get_peek( self, dataset ):
        """expects a .pheno file in the extra_files_dir - ugh"""
        pp = os.path.join(dataset.extra_files_path,'%s.pheno' % dataset.metadata.base_name)
        try:
            p = file(pp,'r').readlines()
        except:
            p = ['##failed to find %s' % pp]
        return ''.join(p[:5])
    def get_file_peek(self,filename):
        """
        can't really peek at a filename - need the extra_files_path and such?
        """
        h = '## rexpression get_file_peek: no file found'
        try:
            h = file(filename,'r').readlines()
        except:
            pass
        return ''.join(h[:5])
    def regenerate_primary_file(self,dataset):
        """cannot do this until we are setting metadata 
        """
        bn = dataset.metadata.base_name
        flist = os.listdir(dataset.extra_files_path)
        rval = ['<html><head><title>Files for Composite Dataset %s</title></head><p/>Comprises the following files:<p/><ul>' % (bn)]
        for i,fname in enumerate(flist):
            sfname = os.path.split(fname)[-1]
            rval.append( '<li><a href="%s">%s</a>' % ( sfname, sfname ) )
        rval.append( '</ul></html>' )
        f = file(dataset.file_name,'w')
        f.write("\n".join( rval ))
        f.write('\n')
        f.close()
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def init_meta( self, dataset, copy_from=None ):
        """Add metadata elements"""
        if copy_from:
            dataset.metadata = copy_from.metadata     
    def set_meta( self, dataset, **kwd ):         
        """
        NOTE we apply the tabular machinary to the phenodata extracted
        from a BioC eSet or affybatch.
        """
        try:
            flist = os.listdir(dataset.extra_files_path)
        except:
            #log.debug('@@@rexpression set_meta failed - no dataset?')
            return False
        bn = None
        for f in flist:
           n = os.path.splitext(f)[0]
           if not bn:
                bn = n
                dataset.metadata.base_name = bn
        if not bn:
            bn = '?'
        pn = '%s.pheno' % (bn)
        pp = os.path.join(dataset.extra_files_path,pn)
        dataset.metadata.pheno_path=pp
        try:
            pf = file(pp,'r').readlines() # read the basename.phenodata in the extra_files_path
        except:
            pf = None
        if pf:
            h = pf[0].strip()
            h = h.split('\t') # hope is header
            h = [escape(x) for x in h]
            dataset.metadata.column_names = h
            dataset.metadata.columns = len(h)
            dataset.peek = ''.join(pf[:5])
        else:
            dataset.metadata.column_names = []
            dataset.metadata.columns = 0
            dataset.peek = 'No pheno file found'
        if len(pf) > 1:
            dataset.metadata.pheCols = self.get_phecols(phenolist=pf)
        else:
            dataset.metadata.pheCols = [('','No useable phenotypes found',False),]
        #self.regenerate_primary_file(dataset)
        if not dataset.info:
                dataset.info = 'Galaxy Expression datatype object'
        if not dataset.blurb:
               dataset.blurb = 'R loadable BioC expression object for the Rexpression Galaxy toolkit'
        return True
    def make_html_table( self, pp='nothing supplied from peek\n'):
        """Create HTML table, used for displaying peek"""
        out = ['<table cellspacing="0" cellpadding="3">',]
        p = pp.split('\n')
        try:
            # Generate column header
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
            out = "Can't create html table %s" % str( exc )
        return out
    def display_peek( self, dataset ):
        """Returns formatted html of peek"""
        out=self.make_html_table(dataset.peek)
        return out
    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/html'

class Affybatch( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "affybatch"

    def __init__( self, **kwd ):
        RexpBase.__init__(self, **kwd)
        self.add_composite_file( '%s.affybatch', description = 'AffyBatch R object saved to file', 
        substitute_name_with_metadata = 'base_name', is_binary=True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class Eset( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "eset"

    def __init__( self, **kwd ):
        RexpBase.__init__(self, **kwd)
        self.add_composite_file( '%s.eset', description = 'ESet R object saved to file', 
        substitute_name_with_metadata = 'base_name', is_binary = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

class MAlist( RexpBase ):
    """derived class for BioC data structures in Galaxy """
    file_ext = "malist"    

    def __init__( self, **kwd ):
        RexpBase.__init__(self, **kwd)
        self.add_composite_file( '%s.malist', description = 'MAlist R object saved to file', 
        substitute_name_with_metadata = 'base_name', is_binary = True )
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass

if __name__ == '__main__':
    import doctest, sys
    doctest.testmod(sys.modules[__name__])
