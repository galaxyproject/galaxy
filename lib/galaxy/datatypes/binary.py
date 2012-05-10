"""
Binary classes
"""

import data, logging, binascii
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes import metadata
from galaxy.datatypes.sniff import *
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )
from bx.seq.twobit import TWOBIT_MAGIC_NUMBER, TWOBIT_MAGIC_NUMBER_SWAP, TWOBIT_MAGIC_SIZE
from urllib import urlencode, quote_plus
import zipfile, gzip
import os, subprocess, tempfile
import struct

log = logging.getLogger(__name__)

# Currently these supported binary data types must be manually set on upload
unsniffable_binary_formats = [ 'ab1', 'scf', 'h5' ]

class Binary( data.Data ):
    """Binary data"""
    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def get_mime( self ):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, size=None, offset=None, **kwd):
        trans.response.set_content_type(dataset.get_mime())
        trans.log_event( "Display dataset id: %s" % str( dataset.id ) )
        trans.response.headers['Content-Length'] = int( os.stat( dataset.file_name ).st_size )
        to_ext = dataset.extension
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        fname = ''.join(c in valid_chars and c or '_' for c in dataset.name)[0:150]
        trans.response.set_content_type( "application/octet-stream" ) #force octet-stream so Safari doesn't append mime extensions to filename
        trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (dataset.hid, fname, to_ext)
        return open( dataset.file_name )

class Ab1( Binary ):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
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
    MetadataElement( name="bam_index", desc="BAM Index File", param=metadata.FileParameter, file_ext="bai", readonly=True, no_value=None, visible=False, optional=True )

    def _get_samtools_version( self ):
        # Determine the version of samtools being used.  Wouldn't it be nice if
        # samtools provided a version flag to make this much simpler?
        version = '0.0.0'
        output = subprocess.Popen( [ 'samtools' ], stderr=subprocess.PIPE, stdout=subprocess.PIPE ).communicate()[1]
        lines = output.split( '\n' )
        for line in lines:
            if line.lower().startswith( 'version' ):
                # Assuming line looks something like: version: 0.1.12a (r862)
                version = line.split()[1]
                break
        return version
    def _is_coordinate_sorted( self, file_name ):
        """See if the input BAM file is sorted from the header information."""
        params = [ "samtools", "view", "-H", file_name ]
        output = subprocess.Popen( params, stderr=subprocess.PIPE, stdout=subprocess.PIPE ).communicate()[0]
        # find returns -1 if string is not found
        return output.find( "SO:coordinate" ) != -1 or output.find( "SO:sorted" ) != -1
    def dataset_content_needs_grooming( self, file_name ):
        """See if file_name is a sorted BAM file"""
        version = self._get_samtools_version()
        if version < '0.1.13':
            return not self._is_coordinate_sorted( file_name )
        else:
            # Samtools version 0.1.13 or newer produces an error condition when attempting to index an
            # unsorted bam file - see http://biostar.stackexchange.com/questions/5273/is-my-bam-file-sorted.
            # So when using a newer version of samtools, we'll first check if the input BAM file is sorted
            # from the header information.  If the header is present and sorted, we do nothing by returning False.
            # If it's present and unsorted or if it's missing, we'll index the bam file to see if it produces the
            # error.  If it does, sorting is needed so we return True (otherwise False).
            #
            # TODO: we're creating an index file here and throwing it away.  We then create it again when
            # the set_meta() method below is called later in the job process.  We need to enhance this overall
            # process so we don't create an index twice.  In order to make it worth the time to implement the
            # upload tool / framework to allow setting metadata from directly within the tool itself, it should be
            # done generically so that all tools will have the ability.  In testing, a 6.6 gb BAM file took 128
            # seconds to index with samtools, and 45 minutes to sort, so indexing is relatively inexpensive.
            if self._is_coordinate_sorted( file_name ):
                return False
            index_name = tempfile.NamedTemporaryFile( prefix = "bam_index" ).name
            stderr_name = tempfile.NamedTemporaryFile( prefix = "bam_index_stderr" ).name
            command = 'samtools index %s %s' % ( file_name, index_name )
            proc = subprocess.Popen( args=command, shell=True, stderr=open( stderr_name, 'wb' ) )
            exit_code = proc.wait()
            stderr = open( stderr_name ).read().strip()
            if stderr:
                try:
                    os.unlink( index_name )
                except OSError:
                    pass
                try:
                    os.unlink( stderr_name )
                except OSError:
                    pass
                # Return True if unsorted error condition is found (find returns -1 if string is not found).
                return stderr.find( "[bam_index_core] the alignment is not sorted" ) != -1
            try:
                os.unlink( index_name )
            except OSError:
                pass
            try:
                os.unlink( stderr_name )
            except OSError:
                pass
            return False
    def groom_dataset_content( self, file_name ):
        """
        Ensures that the Bam file contents are sorted.  This function is called
        on an output dataset after the content is initially generated.
        """
        # Use samtools to sort the Bam file
        ##$ samtools sort
        ##Usage: samtools sort [-on] [-m <maxMem>] <in.bam> <out.prefix>
        ## Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created.
        ## This command may also create temporary files <out.prefix>.%d.bam when the
        ## whole alignment cannot be fitted into memory ( controlled by option -m ).
        #do this in a unique temp directory, because of possible <out.prefix>.%d.bam temp files
        if not self.dataset_content_needs_grooming( file_name ):
            # Don't re-sort if already sorted
            return
        tmp_dir = tempfile.mkdtemp()
        tmp_sorted_dataset_file_name_prefix = os.path.join( tmp_dir, 'sorted' )
        stderr_name = tempfile.NamedTemporaryFile( dir = tmp_dir, prefix = "bam_sort_stderr" ).name
        samtools_created_sorted_file_name = "%s.bam" % tmp_sorted_dataset_file_name_prefix #samtools accepts a prefix, not a filename, it always adds .bam to the prefix
        command = "samtools sort %s %s" % ( file_name, tmp_sorted_dataset_file_name_prefix )
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        #Did sort succeed?
        stderr = open( stderr_name ).read().strip()
        if stderr:
            if exit_code != 0:
                shutil.rmtree( tmp_dir) #clean up 
                raise Exception, "Error Grooming BAM file contents: %s" % stderr
            else:
                print stderr
        # Move samtools_created_sorted_file_name to our output dataset location
        shutil.move( samtools_created_sorted_file_name, file_name )
        # Remove temp file and empty temporary directory
        os.unlink( stderr_name )
        os.rmdir( tmp_dir )
    def init_meta( self, dataset, copy_from=None ):
        Binary.init_meta( self, dataset, copy_from=copy_from )
    def set_meta( self, dataset, overwrite = True, **kwd ):
        """ Creates the index for the BAM file. """
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bam_index
        if not index_file:
            index_file = dataset.metadata.spec['bam_index'].param.new_file( dataset = dataset )
        # Create the Bam index
        ##$ samtools index
        ##Usage: samtools index <in.bam> [<out.index>]
        stderr_name = tempfile.NamedTemporaryFile( prefix = "bam_index_stderr" ).name
        command = 'samtools index %s %s' % ( dataset.file_name, index_file.file_name )
        proc = subprocess.Popen( args=command, shell=True, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        #Did index succeed?
        stderr = open( stderr_name ).read().strip()
        if stderr:
            if exit_code != 0:
                os.unlink( stderr_name ) #clean up 
                raise Exception, "Error Setting BAM Metadata: %s" % stderr
            else:
                print stderr
        dataset.metadata.bam_index = index_file
        # Remove temp file
        os.unlink( stderr_name )
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
    def get_track_type( self ):
        return "ReadTrack", {"data": "bai", "index": "summary_tree"}

class H5( Binary ):
    """Class describing an HDF5 file"""
    file_ext = "h5"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek  = "Binary h5 file" 
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary h5 sequence file (%s)" % ( data.nice_size( dataset.get_size() ) )

class Scf( Binary ):
    """Class describing an scf binary sequence file"""
    file_ext = "scf"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
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
        except:
            return False
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
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

class BigWig(Binary):
    """
    Accessing binary BigWig files from UCSC.
    The supplemental info in the paper has the binary details:
    http://bioinformatics.oxfordjournals.org/cgi/content/abstract/btq351v1
    """
    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )
        self._magic = 0x888FFC26
        self._name = "BigWig"
    def _unpack( self, pattern, handle ):
        return struct.unpack( pattern, handle.read( struct.calcsize( pattern ) ) )
    def sniff( self, filename ):
        try:
            magic = self._unpack( "I", open( filename ) )
            return magic[0] == self._magic
        except:
            return False
    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek  = "Binary UCSC %s file" % self._name
            dataset.blurb = data.nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'
    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary UCSC %s file (%s)" % ( self._name, data.nice_size( dataset.get_size() ) )
    def get_track_type( self ):
        return "LineTrack", {"data_standalone": "bigwig"}

class BigBed(BigWig):
    """BigBed support from UCSC."""
    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )
        self._magic = 0x8789F2EB
        self._name = "BigBed"
    def get_track_type( self ):
        return "LineTrack", {"data_standalone": "bigbed"}

class TwoBit (Binary):
    """Class describing a TwoBit format nucleotide file"""
    
    file_ext = "twobit"
    
    def sniff(self, filename):
        try:
            input = file(filename)
            magic = struct.unpack(">L", input.read(TWOBIT_MAGIC_SIZE))[0]
            if magic == TWOBIT_MAGIC_NUMBER or magic == TWOBIT_MAGIC_NUMBER_SWAP:
                return True
        except IOError:
            return False
    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary TwoBit format nucleotide file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            return super(TwoBit, self).set_peek(dataset, is_multi_byte)
    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary TwoBit format nucleotide file (%s)" % (data.nice_size(dataset.get_size()))
