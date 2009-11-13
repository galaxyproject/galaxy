"""
Binary classes
"""

import data, logging, binascii
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy.datatypes.sniff import *
from urllib import urlencode, quote_plus
import zipfile
import os, subprocess, tempfile

log = logging.getLogger(__name__)

sniffable_binary_formats = [ 'sff' ]
# Currently these supported binary data types must be manually set on upload
unsniffable_binary_formats = [ 'ab1', 'scf' ]

class Binary( data.Data ):
    """Binary data"""
    def set_peek( self, dataset ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = 'data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

class Ab1( Binary ):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            export_url = "/history_add_to?" + urlencode( {'history_id':dataset.history_id,'ext':'ab1','name':'ab1 sequence','info':'Sequence file','dbkey':dataset.dbkey} )
            dataset.peek  = "Binary ab1 sequence file"
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary ab1 sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )

class Bam( Binary ):
    """Class describing a BAM binary file"""
    file_ext = "bam"
    MetadataElement( name="bam_index", desc="BAM Index File", param=metadata.FileParameter, readonly=True, no_value=None, visible=False, optional=True )    
    def init_meta( self, dataset, copy_from=None ):
        Binary.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """
        Sets index for BAM file.
        """
        index_file = dataset.metadata.bam_index
        if not index_file:
            index_file = dataset.metadata.spec['bam_index'].param.new_file( dataset = dataset )
        tmp_dir = tempfile.gettempdir()
        tmpf1 = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmpf1bai = '%s.bai' % tmpf1.name
        try:
            os.system( 'cd %s' % tmp_dir )
            os.system( 'cp %s %s' % ( dataset.file_name, tmpf1.name ) )
            os.system( 'samtools index %s' % tmpf1.name )
            os.system( 'cp %s %s' % ( tmpf1bai, index_file.file_name ) )
        except Exception, ex:
            sys.stderr.write( 'There was a problem creating the index for the BAM file\n%s\n' + str( ex ) )
        tmpf1.close()
        if os.path.exists( tmpf1bai ):
            os.remove( tmpf1bai )
        dataset.metadata.bam_index = index_file
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            export_url = "/history_add_to?" + urlencode( {'history_id':dataset.history_id,'ext':'bam','name':'bam alignments','info':'Alignments file','dbkey':dataset.dbkey} )
            dataset.peek  = "Binary bam alignments file" 
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary bam alignments file (%s)" % ( data.nice_size( dataset.get_size() ) )
    def get_mime( self ):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'

class Binseq( Binary ):
    """Class describing a zip archive of binary sequence files"""
    file_ext = "binseq.zip"
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            zip_file = zipfile.ZipFile( dataset.file_name, "r" )
            num_files = len( zip_file.namelist() )
            dataset.peek  = "Archive of %s binary sequence files" % ( str( num_files ) )
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary sequence file archive (%s)" % ( data.nice_size( dataset.get_size() ) )
    def get_mime( self ):
        """Returns the mime type of the datatype"""
        return 'application/zip'

class Scf( Binary ):
    """Class describing an scf binary sequence file"""
    file_ext = "scf"
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            export_url = "/history_add_to?" + urlencode({'history_id':dataset.history_id,'ext':'scf','name':'scf sequence','info':'Sequence file','dbkey':dataset.dbkey})
            dataset.peek  = "Binary scf sequence file" 
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary scf sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )

class Sff( Binary ):
    """ Standard Flowgram Format (SFF) """
    file_ext = "sff"
    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )
    def sniff( self, filename ):
        # The first 4 bytes of any sff file is '.sff', and the file is binary. For details
        # about the format, see http://www.ncbi.nlm.nih.gov/Traces/trace.cgi?cmd=show&f=formats&m=doc&s=format
        try:
            header = open( filename ).read(4)
            if binascii.b2a_hex( header ) == binascii.hexlify( '.sff' ):
                return True
            return False
        except Exception, e:
            return False
    def set_peek( self, dataset ):
        if not dataset.dataset.purged:
            export_url = "/history_add_to?" + urlencode( {'history_id':dataset.history_id,'ext':'sff','name':'sff file','info':'sff file','dbkey':dataset.dbkey} )
            dataset.peek  = "Binary sff file" 
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary sff file (%s)" % ( data.nice_size( dataset.get_size() ) )
