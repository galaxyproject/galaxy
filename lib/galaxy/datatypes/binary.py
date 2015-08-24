"""Binary classes"""

import binascii
import gzip
import logging
import os
import shutil
import struct
import subprocess
import tempfile
import warnings
import zipfile

from galaxy import eggs
eggs.require( "bx-python" )
from bx.seq.twobit import TWOBIT_MAGIC_NUMBER, TWOBIT_MAGIC_NUMBER_SWAP, TWOBIT_MAGIC_SIZE

from galaxy.datatypes.metadata import MetadataElement, MetadataParameter, ListParameter, DictParameter
from galaxy.datatypes import metadata
from galaxy.util import nice_size, sqlite
from . import data, dataproviders

with warnings.catch_warnings():
    warnings.simplefilter( "ignore" )
    eggs.require( "pysam" )
    from pysam import csamtools


log = logging.getLogger(__name__)

# Currently these supported binary data types must be manually set on upload


class Binary( data.Data ):
    """Binary data"""
    edam_format = "format_2333"
    sniffable_binary_formats = []
    unsniffable_binary_formats = []

    @staticmethod
    def register_sniffable_binary_format(data_type, ext, type_class):
        Binary.sniffable_binary_formats.append({"type": data_type, "ext": ext, "class": type_class})

    @staticmethod
    def register_unsniffable_binary_ext(ext):
        Binary.unsniffable_binary_formats.append(ext)

    @staticmethod
    def is_sniffable_binary( filename ):
        format_information = None
        for format in Binary.sniffable_binary_formats:
            format_instance = format[ "class" ]()
            try:
                if format_instance.sniff(filename):
                    format_information = ( format["type"], format[ "ext" ] )
                    break
            except Exception:
                # Sniffer raised exception, could be any number of
                # reasons for this so there is not much to do besides
                # trying next sniffer.
                pass
        return format_information

    @staticmethod
    def is_ext_unsniffable(ext):
        return ext in Binary.unsniffable_binary_formats

    def set_peek( self, dataset, is_multi_byte=False ):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = nice_size( dataset.get_size() )
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
        trans.response.set_content_type( "application/octet-stream" )  # force octet-stream so Safari doesn't append mime extensions to filename
        trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy%s-[%s].%s"' % (dataset.hid, fname, to_ext)
        return open( dataset.file_name )


class Ab1( Binary ):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "Binary ab1 sequence file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary ab1 sequence file (%s)" % ( nice_size( dataset.get_size() ) )

Binary.register_unsniffable_binary_ext("ab1")


class Idat( Binary ):
    """Binary data in idat format"""
    file_ext = "idat"

    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )

    def sniff( self, filename ):
        try:
            header = open( filename ).read(4)
            if binascii.b2a_hex( header ) == binascii.hexlify( 'IDAT' ):
                return True
            return False
        except:
            return False

Binary.register_sniffable_binary_format("idat", "idat", Idat)


class CompressedArchive( Binary ):
    """
        Class describing an compressed binary file
        This class can be sublass'ed to implement archive filetypes that will not be unpacked by upload.py.
    """
    file_ext = "compressed_archive"
    compressed = True

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "Compressed binary file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Compressed binary file (%s)" % ( nice_size( dataset.get_size() ) )

Binary.register_unsniffable_binary_ext("compressed_archive")


class GenericAsn1Binary( Binary ):
    """Class for generic ASN.1 binary format"""
    file_ext = "asn1-binary"

Binary.register_unsniffable_binary_ext("asn1-binary")


@dataproviders.decorators.has_dataproviders
class Bam( Binary ):
    """Class describing a BAM binary file"""
    edam_format = "format_2572"
    file_ext = "bam"
    track_type = "ReadTrack"
    data_sources = { "data": "bai", "index": "bigwig" }

    MetadataElement( name="bam_index", desc="BAM Index File", param=metadata.FileParameter, file_ext="bai", readonly=True, no_value=None, visible=False, optional=True )
    MetadataElement( name="bam_version", default=None, desc="BAM Version", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=None )
    MetadataElement( name="sort_order", default=None, desc="Sort Order", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=None )
    MetadataElement( name="read_groups", default=[], desc="Read Groups", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="reference_names", default=[], desc="Chromosome Names", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="reference_lengths", default=[], desc="Chromosome Lengths", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[] )
    MetadataElement( name="bam_header", default={}, desc="Dictionary of BAM Headers", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value={} )

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

    @staticmethod
    def merge(split_files, output_file):

        tmp_dir = tempfile.mkdtemp()
        stderr_name = tempfile.NamedTemporaryFile(dir=tmp_dir, prefix="bam_merge_stderr").name
        command = ["samtools", "merge", "-f", output_file] + split_files
        proc = subprocess.Popen( args=command, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        # Did merge succeed?
        stderr = open(stderr_name).read().strip()
        if stderr:
            if exit_code != 0:
                shutil.rmtree(tmp_dir)  # clean up
                raise Exception( "Error merging BAM files: %s" % stderr )
            else:
                print stderr
        os.unlink(stderr_name)
        os.rmdir(tmp_dir)

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
            index_name = tempfile.NamedTemporaryFile( prefix="bam_index" ).name
            stderr_name = tempfile.NamedTemporaryFile( prefix="bam_index_stderr" ).name
            command = 'samtools index %s %s' % ( file_name, index_name )
            proc = subprocess.Popen( args=command, shell=True, stderr=open( stderr_name, 'wb' ) )
            proc.wait()
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
        # $ samtools sort
        # Usage: samtools sort [-on] [-m <maxMem>] <in.bam> <out.prefix>
        # Sort alignments by leftmost coordinates. File <out.prefix>.bam will be created.
        # This command may also create temporary files <out.prefix>.%d.bam when the
        # whole alignment cannot be fitted into memory ( controlled by option -m ).
        # do this in a unique temp directory, because of possible <out.prefix>.%d.bam temp files
        if not self.dataset_content_needs_grooming( file_name ):
            # Don't re-sort if already sorted
            return
        tmp_dir = tempfile.mkdtemp()
        tmp_sorted_dataset_file_name_prefix = os.path.join( tmp_dir, 'sorted' )
        stderr_name = tempfile.NamedTemporaryFile( dir=tmp_dir, prefix="bam_sort_stderr" ).name
        samtools_created_sorted_file_name = "%s.bam" % tmp_sorted_dataset_file_name_prefix  # samtools accepts a prefix, not a filename, it always adds .bam to the prefix
        command = "samtools sort %s %s" % ( file_name, tmp_sorted_dataset_file_name_prefix )
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        # Did sort succeed?
        stderr = open( stderr_name ).read().strip()
        if stderr:
            if exit_code != 0:
                shutil.rmtree( tmp_dir)  # clean up
                raise Exception( "Error Grooming BAM file contents: %s" % stderr )
            else:
                print stderr
        # Move samtools_created_sorted_file_name to our output dataset location
        shutil.move( samtools_created_sorted_file_name, file_name )
        # Remove temp file and empty temporary directory
        os.unlink( stderr_name )
        os.rmdir( tmp_dir )

    def init_meta( self, dataset, copy_from=None ):
        Binary.init_meta( self, dataset, copy_from=copy_from )

    def set_meta( self, dataset, overwrite=True, **kwd ):
        """ Creates the index for the BAM file. """
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bam_index
        if not index_file:
            index_file = dataset.metadata.spec['bam_index'].param.new_file( dataset=dataset )
        # Create the Bam index
        # $ samtools index
        # Usage: samtools index <in.bam> [<out.index>]
        stderr_name = tempfile.NamedTemporaryFile( prefix="bam_index_stderr" ).name
        command = [ 'samtools', 'index', dataset.file_name, index_file.file_name ]
        proc = subprocess.Popen( args=command, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        # Did index succeed?
        if exit_code == -6:
            # SIGABRT, most likely samtools 1.0+ which does not accept the index name parameter.
            dataset_symlink = os.path.join( os.path.dirname( index_file.file_name ),
                                            '__dataset_%d_%s' % ( dataset.id, os.path.basename( index_file.file_name ) ) )
            os.symlink( dataset.file_name, dataset_symlink )
            try:
                command = [ 'samtools', 'index', dataset_symlink ]
                exit_code = subprocess.call( args=command, stderr=open( stderr_name, 'wb' ) )
                shutil.move( dataset_symlink + '.bai', index_file.file_name )
            except Exception as e:
                open( stderr_name, 'ab+' ).write( 'Galaxy attempted to build the BAM index with samtools 1.0+ but failed: %s\n' % e)
            finally:
                os.unlink( dataset_symlink )
        stderr = open( stderr_name ).read().strip()
        if stderr:
            if exit_code != 0:
                os.unlink( stderr_name )  # clean up
                raise Exception( "Error Setting BAM Metadata: %s" % stderr )
            else:
                print stderr
        dataset.metadata.bam_index = index_file
        # Remove temp file
        os.unlink( stderr_name )
        # Now use pysam with BAI index to determine additional metadata
        try:
            bam_file = csamtools.Samfile( filename=dataset.file_name, mode='rb', index_filename=index_file.file_name )
            dataset.metadata.reference_names = list( bam_file.references )
            dataset.metadata.reference_lengths = list( bam_file.lengths )
            dataset.metadata.bam_header = bam_file.header
            dataset.metadata.read_groups = [ read_group['ID'] for read_group in dataset.metadata.bam_header.get( 'RG', [] ) if 'ID' in read_group ]
            dataset.metadata.sort_order = dataset.metadata.bam_header.get( 'HD', {} ).get( 'SO', None )
            dataset.metadata.bam_version = dataset.metadata.bam_header.get( 'HD', {} ).get( 'VN', None )
        except:
            pass

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
            dataset.peek = "Binary bam alignments file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary bam alignments file (%s)" % ( nice_size( dataset.get_size() ) )

    # ------------- Dataproviders
    # pipe through samtools view
    # ALSO: (as Sam)
    # bam does not use '#' to indicate comments/headers - we need to strip out those headers from the std. providers
    # TODO:?? seems like there should be an easier way to do/inherit this - metadata.comment_char?
    # TODO: incorporate samtools options to control output: regions first, then flags, etc.
    @dataproviders.decorators.dataprovider_factory( 'line', dataproviders.line.FilteredLineDataProvider.settings )
    def line_dataprovider( self, dataset, **settings ):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset )
        settings[ 'comment_char' ] = '@'
        return dataproviders.line.FilteredLineDataProvider( samtools_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'regex-line', dataproviders.line.RegexLineDataProvider.settings )
    def regex_line_dataprovider( self, dataset, **settings ):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset )
        settings[ 'comment_char' ] = '@'
        return dataproviders.line.RegexLineDataProvider( samtools_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'column', dataproviders.column.ColumnarDataProvider.settings )
    def column_dataprovider( self, dataset, **settings ):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset )
        settings[ 'comment_char' ] = '@'
        return dataproviders.column.ColumnarDataProvider( samtools_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'dict', dataproviders.column.DictDataProvider.settings )
    def dict_dataprovider( self, dataset, **settings ):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset )
        settings[ 'comment_char' ] = '@'
        return dataproviders.column.DictDataProvider( samtools_source, **settings )

    # these can't be used directly - may need BamColumn, BamDict (Bam metadata -> column/dict)
    # OR - see genomic_region_dataprovider
    # @dataproviders.decorators.dataprovider_factory( 'dataset-column', dataproviders.column.ColumnarDataProvider.settings )
    # def dataset_column_dataprovider( self, dataset, **settings ):
    #    settings[ 'comment_char' ] = '@'
    #    return super( Sam, self ).dataset_column_dataprovider( dataset, **settings )

    # @dataproviders.decorators.dataprovider_factory( 'dataset-dict', dataproviders.column.DictDataProvider.settings )
    # def dataset_dict_dataprovider( self, dataset, **settings ):
    #    settings[ 'comment_char' ] = '@'
    #    return super( Sam, self ).dataset_dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'header', dataproviders.line.RegexLineDataProvider.settings )
    def header_dataprovider( self, dataset, **settings ):
        # in this case we can use an option of samtools view to provide just what we need (w/o regex)
        samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset, '-H' )
        return dataproviders.line.RegexLineDataProvider( samtools_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'id-seq-qual', dataproviders.column.DictDataProvider.settings )
    def id_seq_qual_dataprovider( self, dataset, **settings ):
        settings[ 'indeces' ] = [ 0, 9, 10 ]
        settings[ 'column_types' ] = [ 'str', 'str', 'str' ]
        settings[ 'column_names' ] = [ 'id', 'seq', 'qual' ]
        return self.dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region', dataproviders.column.ColumnarDataProvider.settings )
    def genomic_region_dataprovider( self, dataset, **settings ):
        # GenomicRegionDataProvider currently requires a dataset as source - may not be necc.
        # TODO:?? consider (at least) the possible use of a kwarg: metadata_source (def. to source.dataset),
        #   or remove altogether...
        # samtools_source = dataproviders.dataset.SamtoolsDataProvider( dataset )
        # return dataproviders.dataset.GenomicRegionDataProvider( samtools_source, metadata_source=dataset,
        #                                                        2, 3, 3, **settings )

        # instead, set manually and use in-class column gen
        settings[ 'indeces' ] = [ 2, 3, 3 ]
        settings[ 'column_types' ] = [ 'str', 'int', 'int' ]
        return self.column_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'genomic-region-dict', dataproviders.column.DictDataProvider.settings )
    def genomic_region_dict_dataprovider( self, dataset, **settings ):
        settings[ 'indeces' ] = [ 2, 3, 3 ]
        settings[ 'column_types' ] = [ 'str', 'int', 'int' ]
        settings[ 'column_names' ] = [ 'chrom', 'start', 'end' ]
        return self.dict_dataprovider( dataset, **settings )

    @dataproviders.decorators.dataprovider_factory( 'samtools' )
    def samtools_dataprovider( self, dataset, **settings ):
        """Generic samtools interface - all options available through settings."""
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        return dataproviders.dataset.SamtoolsDataProvider( dataset_source, **settings )

Binary.register_sniffable_binary_format("bam", "bam", Bam)


class Bcf( Binary):
    """Class describing a BCF file"""
    edam_format = "format_3020"
    file_ext = "bcf"

    MetadataElement( name="bcf_index", desc="BCF Index File", param=metadata.FileParameter, file_ext="csi", readonly=True, no_value=None, visible=False, optional=True )

    def sniff( self, filename ):
        # BCF is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        # The first 3 bytes of any bcf file is 'BCF', and the file is binary.
        try:
            header = gzip.open( filename ).read(3)
            if binascii.b2a_hex( header ) == binascii.hexlify( 'BCF' ):
                return True
            return False
        except:
            return False

    def set_meta( self, dataset, overwrite=True, **kwd ):
        """ Creates the index for the BCF file. """
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bcf_index
        if not index_file:
            index_file = dataset.metadata.spec['bcf_index'].param.new_file( dataset=dataset )
        # Create the bcf index
        # $ bcftools index
        # Usage: bcftools index <in.bcf>

        dataset_symlink = os.path.join( os.path.dirname( index_file.file_name ),
                                        '__dataset_%d_%s' % ( dataset.id, os.path.basename( index_file.file_name ) ) )
        os.symlink( dataset.file_name, dataset_symlink )

        stderr_name = tempfile.NamedTemporaryFile( prefix="bcf_index_stderr" ).name
        command = [ 'bcftools', 'index', dataset_symlink ]
        proc = subprocess.Popen( args=command, stderr=open( stderr_name, 'wb' ) )
        exit_code = proc.wait()
        shutil.move( dataset_symlink + '.csi', index_file.file_name )

        stderr = open( stderr_name ).read().strip()
        if stderr:
            if exit_code != 0:
                os.unlink( stderr_name )  # clean up
                raise Exception( "Error Setting BCF Metadata: %s" % stderr )
            else:
                print stderr
        dataset.metadata.bcf_index = index_file
        # Remove temp file
        os.unlink( stderr_name )

Binary.register_sniffable_binary_format("bcf", "bcf", Bcf)


class H5( Binary ):
    """Class describing an HDF5 file"""
    file_ext = "h5"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "Binary h5 file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary h5 sequence file (%s)" % ( nice_size( dataset.get_size() ) )

Binary.register_unsniffable_binary_ext("h5")


class Scf( Binary ):
    """Class describing an scf binary sequence file"""
    edam_format = "format_1632"
    file_ext = "scf"

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "Binary scf sequence file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary scf sequence file (%s)" % ( nice_size( dataset.get_size() ) )

Binary.register_unsniffable_binary_ext("scf")


class Sff( Binary ):
    """ Standard Flowgram Format (SFF) """
    edam_format = "format_3284"
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
            dataset.peek = "Binary sff file"
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary sff file (%s)" % ( nice_size( dataset.get_size() ) )

Binary.register_sniffable_binary_format("sff", "sff", Sff)


class BigWig(Binary):
    """
    Accessing binary BigWig files from UCSC.
    The supplemental info in the paper has the binary details:
    http://bioinformatics.oxfordjournals.org/cgi/content/abstract/btq351v1
    """
    edam_format = "format_3006"
    track_type = "LineTrack"
    data_sources = { "data_standalone": "bigwig" }

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
            dataset.peek = "Binary UCSC %s file" % self._name
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Binary UCSC %s file (%s)" % ( self._name, nice_size( dataset.get_size() ) )

Binary.register_sniffable_binary_format("bigwig", "bigwig", BigWig)


class BigBed(BigWig):
    """BigBed support from UCSC."""
    edam_format = "format_3004"
    data_sources = { "data_standalone": "bigbed" }

    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )
        self._magic = 0x8789F2EB
        self._name = "BigBed"

Binary.register_sniffable_binary_format("bigbed", "bigbed", BigBed)


class TwoBit (Binary):
    """Class describing a TwoBit format nucleotide file"""
    edam_format = "format_3009"
    file_ext = "twobit"

    def sniff(self, filename):
        try:
            # All twobit files start with a 16-byte header. If the file is smaller than 16 bytes, it's obviously not a valid twobit file.
            if os.path.getsize(filename) < 16:
                return False
            input = file(filename)
            magic = struct.unpack(">L", input.read(TWOBIT_MAGIC_SIZE))[0]
            if magic == TWOBIT_MAGIC_NUMBER or magic == TWOBIT_MAGIC_NUMBER_SWAP:
                return True
        except IOError:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary TwoBit format nucleotide file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            return super(TwoBit, self).set_peek(dataset, is_multi_byte)

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return "Binary TwoBit format nucleotide file (%s)" % (nice_size(dataset.get_size()))

Binary.register_sniffable_binary_format("twobit", "twobit", TwoBit)


@dataproviders.decorators.has_dataproviders
class SQlite ( Binary ):
    """Class describing a Sqlite database """
    MetadataElement( name="tables", default=[], param=ListParameter, desc="Database Tables", readonly=True, visible=True, no_value=[] )
    MetadataElement( name="table_columns", default={}, param=DictParameter, desc="Database Table Columns", readonly=True, visible=True, no_value={} )
    MetadataElement( name="table_row_count", default={}, param=DictParameter, desc="Database Table Row Count", readonly=True, visible=True, no_value={} )
    file_ext = "sqlite"

    def init_meta( self, dataset, copy_from=None ):
        Binary.init_meta( self, dataset, copy_from=copy_from )

    def set_meta( self, dataset, overwrite=True, **kwd ):
        try:
            tables = []
            columns = dict()
            rowcounts = dict()
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"
            rslt = c.execute(tables_query).fetchall()
            for table, sql in rslt:
                tables.append(table)
                try:
                    col_query = 'SELECT * FROM %s LIMIT 0' % table
                    cur = conn.cursor().execute(col_query)
                    cols = [col[0] for col in cur.description]
                    columns[table] = cols
                except Exception as exc:
                    log.warn( '%s, set_meta Exception: %s', self, exc )
            for table in tables:
                try:
                    row_query = "SELECT count(*) FROM %s" % table
                    rowcounts[table] = c.execute(row_query).fetchone()[0]
                except Exception as exc:
                    log.warn( '%s, set_meta Exception: %s', self, exc )
            dataset.metadata.tables = tables
            dataset.metadata.table_columns = columns
            dataset.metadata.table_row_count = rowcounts
        except Exception as exc:
            log.warn( '%s, set_meta Exception: %s', self, exc )

    def sniff( self, filename ):
        # The first 16 bytes of any SQLite3 database file is 'SQLite format 3\0', and the file is binary. For details
        # about the format, see http://www.sqlite.org/fileformat.html
        try:
            header = open(filename).read(16)
            if binascii.b2a_hex(header) == binascii.hexlify('SQLite format 3\0'):
                return True
            return False
        except:
            return False

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "SQLite Database"
            lines = ['SQLite Database']
            if dataset.metadata.tables:
                for table in dataset.metadata.tables:
                    try:
                        lines.append('%s [%s]' % (table, dataset.metadata.table_row_count[table]))
                    except:
                        continue
            dataset.peek = '\n'.join(lines)
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "SQLite Database (%s)" % ( nice_size( dataset.get_size() ) )

    @dataproviders.decorators.dataprovider_factory( 'sqlite', dataproviders.dataset.SQliteDataProvider.settings )
    def sqlite_dataprovider( self, dataset, **settings ):
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        return dataproviders.dataset.SQliteDataProvider( dataset_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'sqlite-table', dataproviders.dataset.SQliteDataTableProvider.settings )
    def sqlite_datatableprovider( self, dataset, **settings ):
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        return dataproviders.dataset.SQliteDataTableProvider( dataset_source, **settings )

    @dataproviders.decorators.dataprovider_factory( 'sqlite-dict', dataproviders.dataset.SQliteDataDictProvider.settings )
    def sqlite_datadictprovider( self, dataset, **settings ):
        dataset_source = dataproviders.dataset.DatasetDataProvider( dataset )
        return dataproviders.dataset.SQliteDataDictProvider( dataset_source, **settings )


# Binary.register_sniffable_binary_format("sqlite", "sqlite", SQlite)


class GeminiSQLite( SQlite ):
    """Class describing a Gemini Sqlite database """
    MetadataElement( name="gemini_version", default='0.10.0' , param=MetadataParameter, desc="Gemini Version",
                     readonly=True, visible=True, no_value='0.10.0' )
    file_ext = "gemini.sqlite"

    def set_meta( self, dataset, overwrite=True, **kwd ):
        super( GeminiSQLite, self ).set_meta( dataset, overwrite=overwrite, **kwd )
        try:
            conn = sqlite.connect( dataset.file_name )
            c = conn.cursor()
            tables_query = "SELECT version FROM version"
            result = c.execute( tables_query ).fetchall()
            for version, in result:
                dataset.metadata.gemini_version = version
            # TODO: Can/should we detect even more attributes, such as use of PED file, what was input annotation type, etc.
        except Exception as e:
            log.warn( '%s, set_meta Exception: %s', self, e )

    def sniff( self, filename ):
        if super( GeminiSQLite, self ).sniff( filename ):
            gemini_table_names = [ "gene_detailed", "gene_summary", "resources", "sample_genotype_counts", "sample_genotypes", "samples",
                                   "variant_impacts", "variants", "version" ]
            try:
                conn = sqlite.connect( filename )
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute( tables_query ).fetchall()
                result = map( lambda x: x[0], result )
                for table_name in gemini_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warn( '%s, sniff Exception: %s', self, e )
        return False

    def set_peek( self, dataset, is_multi_byte=False ):
        if not dataset.dataset.purged:
            dataset.peek = "Gemini SQLite Database, version %s" % ( dataset.metadata.gemini_version or 'unknown' )
            dataset.blurb = nice_size( dataset.get_size() )
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek( self, dataset ):
        try:
            return dataset.peek
        except:
            return "Gemini SQLite Database, version %s" % ( dataset.metadata.gemini_version or 'unknown' )

Binary.register_sniffable_binary_format( "gemini.sqlite", "gemini.sqlite", GeminiSQLite )
# FIXME: We need to register gemini.sqlite before sqlite, since register_sniffable_binary_format and is_sniffable_binary called in upload.py
# ignores sniff order declared in datatypes_conf.xml
Binary.register_sniffable_binary_format("sqlite", "sqlite", SQlite)


class Xlsx(Binary):
    """Class for Excel 2007 (xlsx) files"""
    file_ext = "xlsx"

    def sniff( self, filename ):
        # Xlsx is compressed in zip format and must not be uncompressed in Galaxy.
        try:
            if zipfile.is_zipfile( filename ):
                tempzip = zipfile.ZipFile( filename )
                if "[Content_Types].xml" in tempzip.namelist() and tempzip.read("[Content_Types].xml").find(b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml') != -1:
                    return True
            return False
        except:
            return False

Binary.register_sniffable_binary_format("xlsx", "xlsx", Xlsx)


class Sra( Binary ):
    """ Sequence Read Archive (SRA) datatype originally from mdshw5/sra-tools-galaxy"""
    file_ext = 'sra'

    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )

    def sniff( self, filename ):
        """ The first 8 bytes of any NCBI sra file is 'NCBI.sra', and the file is binary.
        For details about the format, see http://www.ncbi.nlm.nih.gov/books/n/helpsra/SRA_Overview_BK/#SRA_Overview_BK.4_SRA_Data_Structure
        """
        try:
            header = open(filename).read(8)
            if binascii.b2a_hex(header) == binascii.hexlify('NCBI.sra'):
                return True
            else:
                return False
        except:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = 'Binary sra file'
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except:
            return 'Binary sra file (%s)' % (nice_size(dataset.get_size()))

Binary.register_sniffable_binary_format('sra', 'sra', Sra)


class RData( Binary ):
    """Generic R Data file datatype implementation"""
    file_ext = 'RData'

    def __init__( self, **kwd ):
        Binary.__init__( self, **kwd )

    def sniff( self, filename ):
        rdata_header = binascii.hexlify('RDX2\nX\n')
        try:
            header = open(filename).read(7)
            if binascii.b2a_hex(header) == rdata_header:
                return True

            header = gzip.open( filename ).read(7)
            if binascii.b2a_hex(header) == rdata_header:
                return True
        except:
            return False

Binary.register_sniffable_binary_format('RData', 'RData', RData)
