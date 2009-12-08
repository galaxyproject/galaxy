"""
Binary classes
"""

import data, logging, binascii
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy.datatypes.sniff import *
from urllib import urlencode, quote_plus
import zipfile, gzip
import os, subprocess, tempfile

log = logging.getLogger(__name__)

# Currently these supported binary data types must be manually set on upload
unsniffable_binary_formats = [ 'ab1', 'scf' ]

class Binary( data.Data ):
    """Binary data"""
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = 'data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def get_mime( self ):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'

class Ab1( Binary ):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"

    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_peek( self, dataset, is_multi_byte=False ):
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

    def before_setting_metadata( self, dataset ):
        """ Ensures that the Bam file contents are sorted.  This function is called on the dataset before set_meta() is called."""
        sorted = False
        try:
            index_file = dataset.metadata.bam_index
        except:
            index_file = None
        if index_file:
            # If an index file already exists on disk, then the data must have previously been sorted
            # since samtools requires a sorted Bam file in order to create an index.
            sorted = os.path.exists( index_file.file_name )
        if not sorted:
            # Use samtools to sort the Bam file
            tmp_dir = tempfile.gettempdir()
            # Create a symlink from the temporary directory to the dataset file so that samtools can mess with it.
            tmp_dataset_file_name = os.path.join( tmp_dir, os.path.basename( dataset.file_name ) )
            # Here tmp_dataset_file_name looks something like /tmp/dataset_XX.dat
            os.symlink( dataset.file_name, tmp_dataset_file_name )
            # Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created.
            # TODO: This command may also create temporary files <out.prefix>.%d.bam when the
            # whole alignment cannot be fitted into memory ( controlled by option -m ).  We're
            # not handling this case here.
            tmp_sorted_dataset_file = tempfile.NamedTemporaryFile( prefix=tmp_dataset_file_name )
            tmp_sorted_dataset_file_name = tmp_sorted_dataset_file.name
            tmp_sorted_dataset_file.close()
            command = "samtools sort %s %s 2>/dev/null" % ( tmp_dataset_file_name, tmp_sorted_dataset_file_name )
            proc = subprocess.Popen( args=command, shell=True )
            proc.wait()
            tmp_sorted_bam_file_name = '%s.bam' % tmp_sorted_dataset_file_name
            # Move tmp_sorted_bam_file_name to our output dataset location
            shutil.move( tmp_sorted_bam_file_name, dataset.file_name )
            # Remove all remaining temporary files
            os.unlink( tmp_dataset_file_name )
    def init_meta( self, dataset, copy_from=None ):
        Binary.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """ Creates the index for the BAM file. """
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bam_index
        if not index_file:
            index_file = dataset.metadata.spec['bam_index'].param.new_file( dataset = dataset )
        tmp_dir = tempfile.gettempdir()
        # Create a symlink from the temporary directory to the dataset file so that samtools can mess with it.
        tmp_dataset_file_name = os.path.join( tmp_dir, os.path.basename( dataset.file_name ) )
        # Here tmp_dataset_file_name looks something like /tmp/dataset_XX.dat
        os.symlink( dataset.file_name, tmp_dataset_file_name )
        errors = False
        try:
            # Create the Bam index
            command = 'samtools index %s' % tmp_dataset_file_name
            proc = subprocess.Popen( args=command, shell=True )
            proc.wait()
        except Exception, e:
            errors = True
            err_msg = 'Error creating index for BAM file (%s)' % str( tmp_dataset_file_name )
            log.exception( err_msg )
            sys.stderr.write( err_msg + str( e ) )
        if not errors:
            # Move the temporary index file ~/tmp/dataset_XX.dat.bai to our metadata file
            # storage location ~/database/files/_metadata_files/dataset_XX.dat
            shutil.move( '%s.bai' % ( tmp_dataset_file_name ), index_file.file_name )
            # Remove all remaining temporary files
            os.unlink( tmp_dataset_file_name )
            # Set the metadata
            dataset.metadata.bam_index = index_file
    def sniff( self, filename ):
        # BAM is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        # The first 4 bytes of any bam file is 'BAM\1', and the file is binary. 
        try:
            header = gzip.open( filename ).read(4)
            if binascii.b2a_hex( header ) == binascii.hexlify( 'BAM\1' ):
                return True
            return False
        except:
            return False
    def set_peek( self, dataset, is_multi_byte=False ):
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

class Binseq( Binary ):
    """Class describing a zip archive of binary sequence files"""
    file_ext = "binseq.zip"

    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_peek( self, dataset, is_multi_byte=False ):
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

    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def set_peek( self, dataset, is_multi_byte=False ):
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
    def before_setting_metadata( self, dataset ):
        """This function is called on the dataset before metadata is edited."""
        pass
    def sniff( self, filename ):
        # The first 4 bytes of any sff file is '.sff', and the file is binary. For details
        # about the format, see http://www.ncbi.nlm.nih.gov/Traces/trace.cgi?cmd=show&f=formats&m=doc&s=format
        try:
            header = open( filename ).read(4)
            if binascii.b2a_hex( header ) == binascii.hexlify( '.sff' ):
                return True
            return False
        except:
            return False
    def set_peek( self, dataset, is_multi_byte=False ):
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
