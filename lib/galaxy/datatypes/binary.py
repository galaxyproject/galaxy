"""Binary classes"""
from __future__ import print_function

import binascii
import gzip
import logging
import os
import shutil
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from collections import OrderedDict
from json import dumps

import h5py
import pysam
import pysam.bcftools
from bx.seq.twobit import TWOBIT_MAGIC_NUMBER, TWOBIT_MAGIC_NUMBER_SWAP, TWOBIT_MAGIC_SIZE

from galaxy import util
from galaxy.datatypes import metadata
from galaxy.datatypes.metadata import DictParameter, ListParameter, MetadataElement, MetadataParameter
from galaxy.util import nice_size, sqlite
from galaxy.util.checkers import is_bz2, is_gzip
from . import data, dataproviders

log = logging.getLogger(__name__)

# Currently these supported binary data types must be manually set on upload


class Binary(data.Data):
    """Binary data"""
    edam_format = "format_2333"

    @staticmethod
    def register_sniffable_binary_format(data_type, ext, type_class):
        """Deprecated method."""
        pass

    @staticmethod
    def register_unsniffable_binary_ext(ext):
        """Deprecated method."""
        pass

    def set_peek(self, dataset, is_multi_byte=False):
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = 'binary data'
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/octet-stream'


class Ab1(Binary):
    """Class describing an ab1 binary sequence file"""
    file_ext = "ab1"
    edam_format = "format_3000"
    edam_data = "data_0924"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary ab1 sequence file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary ab1 sequence file (%s)" % (nice_size(dataset.get_size()))


class Idat(Binary):
    """Binary data in idat format"""
    file_ext = "idat"
    edam_format = "format_2058"
    edam_data = "data_2603"

    def sniff(self, filename):
        try:
            header = open(filename, 'rb').read(4)
            if header == b'IDAT':
                return True
            return False
        except Exception:
            return False


class Cel(Binary):

    """Binary data in CEL format."""
    file_ext = "cel"
    edam_format = "format_1638"
    edam_data = "data_3110"

    def sniff(self, filename):
        """
        Try to guess if the file is a CEL file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.cel')
        >>> Cel().sniff(fname)
        True

        >>> fname = get_test_fname('drugbank_drugs.mz5')
        >>> Cel().sniff(fname)
        False
        """
        try:
            header = open(filename, 'rb').read(4)
            if header == b';\x01\x00\x00':
                return True
            return False
        except Exception:
            return False


class MashSketch(Binary):
    """
        Mash Sketch file.
        Sketches are used by the MinHash algorithm to allow fast distance estimations
        with low storage and memory requirements. To make a sketch, each k-mer in a sequence
        is hashed, which creates a pseudo-random identifier. By sorting these identifiers (hashes),
        a small subset from the top of the sorted list can represent the entire sequence (these are min-hashes).
        The more similar another sequence is, the more min-hashes it is likely to share.
    """
    file_ext = "msh"


class CompressedArchive(Binary):
    """
        Class describing an compressed binary file
        This class can be sublass'ed to implement archive filetypes that will not be unpacked by upload.py.
    """
    file_ext = "compressed_archive"
    compressed = True

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Compressed binary file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Compressed binary file (%s)" % (nice_size(dataset.get_size()))


class DynamicCompressedArchive(CompressedArchive):

    def matches_any(self, target_datatypes):
        """Treat two aspects of compressed datatypes separately.
        """
        compressed_target_datatypes = []
        uncompressed_target_datatypes = []

        for target_datatype in target_datatypes:
            if hasattr(target_datatype, "uncompressed_datatype_instance") and target_datatype.compressed_format == self.compressed_format:
                uncompressed_target_datatypes.append(target_datatype.uncompressed_datatype_instance)
            else:
                compressed_target_datatypes.append(target_datatype)

        # TODO: Add gz and bz2 as proper datatypes and use those instances instead of
        # CompressedArchive() in the following check.
        return self.uncompressed_datatype_instance.matches_any(uncompressed_target_datatypes) or \
            CompressedArchive().matches_any(compressed_target_datatypes)


class GzDynamicCompressedArchive(DynamicCompressedArchive):
    compressed_format = "gzip"


class Bz2DynamicCompressedArchive(DynamicCompressedArchive):
    compressed_format = "bz2"


class CompressedZipArchive(CompressedArchive):
    """
        Class describing an compressed binary file
        This class can be sublass'ed to implement archive filetypes that will not be unpacked by upload.py.
    """
    file_ext = "zip"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Compressed zip file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Compressed zip file (%s)" % (nice_size(dataset.get_size()))


class GenericAsn1Binary(Binary):
    """Class for generic ASN.1 binary format"""
    file_ext = "asn1-binary"
    edam_format = "format_1966"
    edam_data = "data_0849"


class BamNative(CompressedArchive):
    """Class describing a BAM binary file that is not necessarily sorted"""
    edam_format = "format_2572"
    edam_data = "data_0863"
    file_ext = "unsorted.bam"
    sort_flag = None

    MetadataElement(name="bam_version", default=None, desc="BAM Version", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=None)
    MetadataElement(name="sort_order", default=None, desc="Sort Order", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=None)
    MetadataElement(name="read_groups", default=[], desc="Read Groups", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="reference_names", default=[], desc="Chromosome Names", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="reference_lengths", default=[], desc="Chromosome Lengths", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value=[])
    MetadataElement(name="bam_header", default={}, desc="Dictionary of BAM Headers", param=MetadataParameter, readonly=True, visible=False, optional=True, no_value={})
    MetadataElement(name="columns", default=12, desc="Number of columns", readonly=True, visible=False, no_value=0)
    MetadataElement(name="column_types", default=['str', 'int', 'str', 'int', 'int', 'str', 'str', 'int', 'int', 'str', 'str', 'str'], desc="Column types", param=metadata.ColumnTypesParameter, readonly=True, visible=False, no_value=[])
    MetadataElement(name="column_names", default=['QNAME', 'FLAG', 'RNAME', 'POS', 'MAPQ', 'CIGAR', 'MRNM', 'MPOS', 'ISIZE', 'SEQ', 'QUAL', 'OPT'], desc="Column names", readonly=True, visible=False, optional=True, no_value=[])

    @staticmethod
    def merge(split_files, output_file):
        """
        Merges BAM files

        :param split_files: List of bam file paths to merge
        :param output_file: Write merged bam file to this location
        """
        pysam.merge('-O', 'BAM', output_file, *split_files)

    def init_meta(self, dataset, copy_from=None):
        Binary.init_meta(self, dataset, copy_from=copy_from)

    def sniff(self, filename):
        # BAM is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        # The first 4 bytes of any bam file is 'BAM\1', and the file is binary.
        try:
            header = gzip.open(filename).read(4)
            if header == b'BAM\1':
                return True
            return False
        except Exception:
            return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            bam_file = pysam.AlignmentFile(dataset.file_name, mode='rb')
            # TODO: Reference names, lengths, read_groups and headers can become very large, truncate when necessary
            dataset.metadata.reference_names = list(bam_file.references)
            dataset.metadata.reference_lengths = list(bam_file.lengths)
            dataset.metadata.bam_header = OrderedDict((k, v) for k, v in bam_file.header.items())
            dataset.metadata.read_groups = [read_group['ID'] for read_group in dataset.metadata.bam_header.get('RG', []) if 'ID' in read_group]
            dataset.metadata.sort_order = dataset.metadata.bam_header.get('HD', {}).get('SO', None)
            dataset.metadata.bam_version = dataset.metadata.bam_header.get('HD', {}).get('VN', None)
        except Exception:
            # Per Dan, don't log here because doing so will cause datasets that
            # fail metadata to end in the error state
            pass

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary bam alignments file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary bam alignments file (%s)" % (nice_size(dataset.get_size()))

    def to_archive(self, trans, dataset, name=""):
        rel_paths = []
        file_paths = []
        rel_paths.append("%s.%s" % (name or dataset.file_name, dataset.extension))
        file_paths.append(dataset.file_name)
        rel_paths.append("%s.%s.bai" % (name or dataset.file_name, dataset.extension))
        file_paths.append(dataset.metadata.bam_index.file_name)
        return zip(file_paths, rel_paths)

    def groom_dataset_content(self, file_name):
        """
        Ensures that the BAM file contents are coordinate-sorted.  This function is called
        on an output dataset after the content is initially generated.
        """
        # Use pysam to sort the BAM file
        # This command may also creates temporary files <out.prefix>.%d.bam when the
        # whole alignment cannot fit into memory.
        # do this in a unique temp directory, because of possible <out.prefix>.%d.bam temp files
        if not self.dataset_content_needs_grooming(file_name):
            # Don't re-sort if already sorted
            return
        tmp_dir = tempfile.mkdtemp()
        tmp_sorted_dataset_file_name_prefix = os.path.join(tmp_dir, 'sorted')
        sorted_file_name = "%s.bam" % tmp_sorted_dataset_file_name_prefix
        slots = os.environ.get('GALAXY_SLOTS', 1)
        sort_args = []
        if self.sort_flag:
            sort_args = [self.sort_flag]
        sort_args.extend(["-@%s" % slots, file_name, '-T', tmp_sorted_dataset_file_name_prefix, '-O', 'BAM', '-o', sorted_file_name])
        try:
            pysam.sort(*sort_args)
        except Exception:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            raise
        # Move samtools_created_sorted_file_name to our output dataset location
        shutil.move(sorted_file_name, file_name)
        # Remove temp file and empty temporary directory
        os.rmdir(tmp_dir)

    def get_chunk(self, trans, dataset, offset=0, ck_size=None):
        if not offset == -1:
            try:
                with pysam.AlignmentFile(dataset.file_name, "rb") as bamfile:
                    ck_size = 300  # 300 lines
                    ck_data = ""
                    header_line_count = 0
                    if offset == 0:
                        ck_data = bamfile.text.replace('\t', ' ')
                        header_line_count = bamfile.text.count('\n')
                    else:
                        bamfile.seek(offset)
                    for line_number, alignment in enumerate(bamfile):
                        # return only Header lines if 'header_line_count' exceeds 'ck_size'
                        # FIXME: Can be problematic if bam has million lines of header
                        offset = bamfile.tell()
                        if (line_number + header_line_count) > ck_size:
                            break
                        else:
                            bamline = alignment.tostring(bamfile)
                            # Galaxy display each tag as separate column because 'tostring()' funcition put tabs in between each tag of tags column.
                            # Below code will remove spaces between each tag.
                            bamline_modified = ('\t').join(bamline.split()[:11] + [(' ').join(bamline.split()[11:])])
                            ck_data = "%s\n%s" % (ck_data, bamline_modified)
                    else:
                        # Nothing to enumerate; we've either offset to the end
                        # of the bamfile, or there is no data. (possible with
                        # header-only bams)
                        offset = -1
            except Exception as e:
                offset = -1
                ck_data = "Could not display BAM file, error was:\n%s" % e
        else:
            ck_data = ''
            offset = -1
        return dumps({'ck_data': util.unicodify(ck_data),
                      'offset': offset})

    def display_data(self, trans, dataset, preview=False, filename=None, to_ext=None, offset=None, ck_size=None, **kwd):
        preview = util.string_as_bool(preview)
        if offset is not None:
            return self.get_chunk(trans, dataset, offset, ck_size)
        elif to_ext or not preview:
            return super(BamNative, self).display_data(trans, dataset, preview, filename, to_ext, **kwd)
        else:
            column_names = dataset.metadata.column_names
            if not column_names:
                column_names = []
            column_types = dataset.metadata.column_types
            if not column_types:
                column_types = []
            column_number = dataset.metadata.columns
            if column_number is None:
                column_number = 1
            return trans.fill_template("/dataset/tabular_chunked.mako",
                                       dataset=dataset,
                                       chunk=self.get_chunk(trans, dataset, 0),
                                       column_number=column_number,
                                       column_names=column_names,
                                       column_types=column_types)


@dataproviders.decorators.has_dataproviders
class Bam(BamNative):
    """Class describing a BAM binary file"""
    edam_format = "format_2572"
    edam_data = "data_0863"
    file_ext = "bam"
    track_type = "ReadTrack"
    data_sources = {"data": "bai", "index": "bigwig"}

    MetadataElement(name="bam_index", desc="BAM Index File", param=metadata.FileParameter, file_ext="bai", readonly=True, no_value=None, visible=False, optional=True)

    def dataset_content_needs_grooming(self, file_name):
        """
        Check if file_name is a coordinate-sorted BAM file
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        index_name = tempfile.NamedTemporaryFile(prefix="bam_index").name
        try:
            # If pysam fails to index a file it will write to stderr,
            # and this causes the set_meta script to fail. So instead
            # we start another process and discard stderr.
            cmd = ['python', '-c', "import pysam; pysam.index('%s', '%s')" % (file_name, index_name)]
            with open(os.devnull, 'w') as devnull:
                subprocess.check_call(cmd, stderr=devnull, shell=False)
            needs_sorting = False
        except subprocess.CalledProcessError:
            needs_sorting = True
        try:
            os.unlink(index_name)
        except Exception:
            pass
        return needs_sorting

    def set_meta(self, dataset, overwrite=True, **kwd):
        # These metadata values are not accessible by users, always overwrite
        super(Bam, self).set_meta(dataset=dataset, overwrite=overwrite, **kwd)
        index_file = dataset.metadata.bam_index
        if not index_file:
            index_file = dataset.metadata.spec['bam_index'].param.new_file(dataset=dataset)
        pysam.index(dataset.file_name, index_file.file_name)
        dataset.metadata.bam_index = index_file

    def sniff(self, file_name):
        return super(Bam, self).sniff(file_name) and not self.dataset_content_needs_grooming(file_name)

    # ------------- Dataproviders
    # pipe through samtools view
    # ALSO: (as Sam)
    # bam does not use '#' to indicate comments/headers - we need to strip out those headers from the std. providers
    # TODO:?? seems like there should be an easier way to do/inherit this - metadata.comment_char?
    # TODO: incorporate samtools options to control output: regions first, then flags, etc.
    @dataproviders.decorators.dataprovider_factory('line', dataproviders.line.FilteredLineDataProvider.settings)
    def line_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings['comment_char'] = '@'
        return dataproviders.line.FilteredLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory('regex-line', dataproviders.line.RegexLineDataProvider.settings)
    def regex_line_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings['comment_char'] = '@'
        return dataproviders.line.RegexLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory('column', dataproviders.column.ColumnarDataProvider.settings)
    def column_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings['comment_char'] = '@'
        return dataproviders.column.ColumnarDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory('dict', dataproviders.column.DictDataProvider.settings)
    def dict_dataprovider(self, dataset, **settings):
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        settings['comment_char'] = '@'
        return dataproviders.column.DictDataProvider(samtools_source, **settings)

    # these can't be used directly - may need BamColumn, BamDict (Bam metadata -> column/dict)
    # OR - see genomic_region_dataprovider
    # @dataproviders.decorators.dataprovider_factory('dataset-column', dataproviders.column.ColumnarDataProvider.settings)
    # def dataset_column_dataprovider(self, dataset, **settings):
    #    settings['comment_char'] = '@'
    #    return super(Sam, self).dataset_column_dataprovider(dataset, **settings)

    # @dataproviders.decorators.dataprovider_factory('dataset-dict', dataproviders.column.DictDataProvider.settings)
    # def dataset_dict_dataprovider(self, dataset, **settings):
    #    settings['comment_char'] = '@'
    #    return super(Sam, self).dataset_dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory('header', dataproviders.line.RegexLineDataProvider.settings)
    def header_dataprovider(self, dataset, **settings):
        # in this case we can use an option of samtools view to provide just what we need (w/o regex)
        samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset, '-H')
        return dataproviders.line.RegexLineDataProvider(samtools_source, **settings)

    @dataproviders.decorators.dataprovider_factory('id-seq-qual', dataproviders.column.DictDataProvider.settings)
    def id_seq_qual_dataprovider(self, dataset, **settings):
        settings['indeces'] = [0, 9, 10]
        settings['column_types'] = ['str', 'str', 'str']
        settings['column_names'] = ['id', 'seq', 'qual']
        return self.dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory('genomic-region', dataproviders.column.ColumnarDataProvider.settings)
    def genomic_region_dataprovider(self, dataset, **settings):
        # GenomicRegionDataProvider currently requires a dataset as source - may not be necc.
        # TODO:?? consider (at least) the possible use of a kwarg: metadata_source (def. to source.dataset),
        #   or remove altogether...
        # samtools_source = dataproviders.dataset.SamtoolsDataProvider(dataset)
        # return dataproviders.dataset.GenomicRegionDataProvider(samtools_source, metadata_source=dataset,
        #                                                        2, 3, 3, **settings)

        # instead, set manually and use in-class column gen
        settings['indeces'] = [2, 3, 3]
        settings['column_types'] = ['str', 'int', 'int']
        return self.column_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory('genomic-region-dict', dataproviders.column.DictDataProvider.settings)
    def genomic_region_dict_dataprovider(self, dataset, **settings):
        settings['indeces'] = [2, 3, 3]
        settings['column_types'] = ['str', 'int', 'int']
        settings['column_names'] = ['chrom', 'start', 'end']
        return self.dict_dataprovider(dataset, **settings)

    @dataproviders.decorators.dataprovider_factory('samtools')
    def samtools_dataprovider(self, dataset, **settings):
        """Generic samtools interface - all options available through settings."""
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SamtoolsDataProvider(dataset_source, **settings)


class ProBam(Bam):
    """Class describing a BAM binary file - extended for proteomics data"""
    edam_format = "format_3826"
    edam_data = "data_0863"
    file_ext = "probam"


class BamInputSorted(BamNative):

    sort_flag = '-n'
    file_ext = 'qname_input_sorted.bam'

    """
    A class for BAM files that can formally be unsorted or queryname sorted.
    Alignments are either ordered based on the order with which the queries appear when producing the alignment,
    or ordered by their queryname.
    This notaby keeps alignments produced by paired end sequencing adjacent.
    """

    def sniff(self, file_name):
        # We never want to sniff to this datatype
        return False

    def dataset_content_needs_grooming(self, file_name):
        """
        Groom if the file is coordinate sorted
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        with pysam.AlignmentFile(filename=file_name) as f:
            # The only sure thing we know here is that the sort order can't be coordinate
            return f.header.get('HD', {}).get('SO') == 'coordinate'


class BamQuerynameSorted(BamInputSorted):
    """A class for queryname sorted BAM files."""

    sort_flag = '-n'
    file_ext = "qname_sorted.bam"

    def sniff(self, file_name):
        return BamNative().sniff(file_name) and not self.dataset_content_needs_grooming(file_name)

    def dataset_content_needs_grooming(self, file_name):
        """
        Check if file_name is a queryname-sorted BAM file
        """
        # The best way to ensure that BAM files are coordinate-sorted and indexable
        # is to actually index them.
        with pysam.AlignmentFile(filename=file_name) as f:
            return f.header.get('HD', {}).get('SO') != 'queryname'


class CRAM(Binary):
    file_ext = "cram"
    edam_format = "format_3462"
    edam_data = "format_0863"

    MetadataElement(name="cram_version", default=None, desc="CRAM Version", param=MetadataParameter, readonly=True, visible=False, optional=False, no_value=None)
    MetadataElement(name="cram_index", desc="CRAM Index File", param=metadata.FileParameter, file_ext="crai", readonly=True, no_value=None, visible=False, optional=True)

    def set_meta(self, dataset, overwrite=True, **kwd):
        major_version, minor_version = self.get_cram_version(dataset.file_name)
        if major_version != -1:
            dataset.metadata.cram_version = str(major_version) + "." + str(minor_version)

        if not dataset.metadata.cram_index:
            index_file = dataset.metadata.spec['cram_index'].param.new_file(dataset=dataset)
            if self.set_index_file(dataset, index_file):
                dataset.metadata.cram_index = index_file

    def get_cram_version(self, filename):
        try:
            with open(filename, "rb") as fh:
                header = bytearray(fh.read(6))
            return header[4], header[5]
        except Exception as exc:
            log.warning('%s, get_cram_version Exception: %s', self, exc)
            return -1, -1

    def set_index_file(self, dataset, index_file):
        try:
            pysam.index(dataset.file_name, index_file.file_name)
            return True
        except Exception as exc:
            log.warning('%s, set_index_file Exception: %s', self, exc)
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = 'CRAM binary alignment file'
            dataset.blurb = 'binary data'
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, filename):
        try:
            header = open(filename, 'rb').read(4)
            if header == b"CRAM":
                return True
            return False
        except Exception:
            return False


class BaseBcf(CompressedArchive):
    edam_format = "format_3020"
    edam_data = "data_3498"


class Bcf(BaseBcf):
    """
    Class describing a (BGZF-compressed) BCF file

    """
    file_ext = "bcf"

    MetadataElement(name="bcf_index", desc="BCF Index File", param=metadata.FileParameter, file_ext="csi", readonly=True, no_value=None, visible=False, optional=True)

    def sniff(self, filename):
        # BCF is compressed in the BGZF format, and must not be uncompressed in Galaxy.
        try:
            header = gzip.open(filename).read(3)
            # The first 3 bytes of any BCF file are 'BCF', and the file is binary.
            if header == b'BCF':
                return True
            return False
        except Exception:
            return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        """ Creates the index for the BCF file. """
        # These metadata values are not accessible by users, always overwrite
        index_file = dataset.metadata.bcf_index
        if not index_file:
            index_file = dataset.metadata.spec['bcf_index'].param.new_file(dataset=dataset)
        # Create the bcf index
        dataset_symlink = os.path.join(os.path.dirname(index_file.file_name),
                                       '__dataset_%d_%s' % (dataset.id, os.path.basename(index_file.file_name)))
        os.symlink(dataset.file_name, dataset_symlink)
        try:
            cmd = ['python', '-c', "import pysam.bcftools; pysam.bcftools.index('%s')" % (dataset_symlink)]
            subprocess.check_call(cmd)
            shutil.move(dataset_symlink + '.csi', index_file.file_name)
        except Exception as e:
            raise Exception('Error setting BCF metadata: %s' % (str(e)))
        finally:
            # Remove temp file and symlink
            os.remove(dataset_symlink)
        dataset.metadata.bcf_index = index_file


class BcfUncompressed(BaseBcf):
    """
    Class describing an uncompressed BCF file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1.bcf_uncompressed')
    >>> BcfUncompressed().sniff(fname)
    True
    >>> fname = get_test_fname('1.bcf')
    >>> BcfUncompressed().sniff(fname)
    False
    """
    file_ext = "bcf_uncompressed"

    def sniff(self, filename):
        try:
            header = open(filename, mode='rb').read(3)
            # The first 3 bytes of any BCF file are 'BCF', and the file is binary.
            if header == b'BCF':
                return True
            return False
        except Exception:
            return False


class H5(Binary):
    """
    Class describing an HDF5 file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.mz5')
    >>> H5().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> H5().sniff(fname)
    False
    """
    file_ext = "h5"
    edam_format = "format_3590"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = binascii.unhexlify("894844460d0a1a0a")

    def sniff(self, filename):
        # The first 8 bytes of any hdf5 file are 0x894844460d0a1a0a
        try:
            header = open(filename, 'rb').read(8)
            if header == self._magic:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary HDF5 file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary HDF5 file (%s)" % (nice_size(dataset.get_size()))


class Loom(H5):
    """
    Class describing a Loom file: http://loompy.org/

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.loom')
    >>> Loom().sniff(fname)
    True
    >>> fname = get_test_fname('test.mz5')
    >>> Loom().sniff(fname)
    False
    """
    file_ext = "loom"
    edam_format = "format_3590"

    MetadataElement(name="title", default="", desc="title", readonly=True, visible=True, no_value="")
    MetadataElement(name="description", default="", desc="description", readonly=True, visible=True, no_value="")
    MetadataElement(name="url", default="", desc="url", readonly=True, visible=True, no_value="")
    MetadataElement(name="doi", default="", desc="doi", readonly=True, visible=True, no_value="")
    MetadataElement(name="loom_spec_version", default="", desc="loom_spec_version", readonly=True, visible=True, no_value="")
    MetadataElement(name="creation_date", default=None, desc="creation_date", readonly=True, visible=True, no_value=None)
    MetadataElement(name="shape", default=(), desc="shape", param=metadata.ListParameter, readonly=True, visible=True, no_value=())
    MetadataElement(name="layers_count", default=0, desc="layers_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="layers_names", desc="layers_names", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None)
    MetadataElement(name="row_attrs_count", default=0, desc="row_attrs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="row_attrs_names", desc="row_attrs_names", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None)
    MetadataElement(name="col_attrs_count", default=0, desc="col_attrs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="col_attrs_names", desc="col_attrs_names", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None)
    MetadataElement(name="col_graphs_count", default=0, desc="col_graphs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="col_graphs_names", desc="col_graphs_names", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None)
    MetadataElement(name="row_graphs_count", default=0, desc="row_graphs_count", readonly=True, visible=True, no_value=0)
    MetadataElement(name="row_graphs_names", desc="row_graphs_names", default=[], param=metadata.SelectParameter, multiple=True, readonly=True, no_value=None)

    def sniff(self, filename):
        if super(Loom, self).sniff(filename):
            try:
                with h5py.File(filename) as loom_file:
                    return bool(loom_file.attrs.get('LOOM_SPEC_VERSION', False))
            except Exception:
                return False
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary Loom file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary Loom file (%s)" % (nice_size(dataset.get_size()))

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(Loom, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            with h5py.File(dataset.file_name) as loom_file:
                dataset.metadata.title = loom_file.attrs.get('title', None)
                dataset.metadata.description = loom_file.attrs.get('description', None)
                dataset.metadata.url = loom_file.attrs.get('url', None)
                dataset.metadata.doi = loom_file.attrs.get('doi', None)
                dataset.metadata.loom_spec_version = loom_file.attrs.get('LOOM_SPEC_VERSION', None)
                dataset.creation_date = loom_file.attrs.get('creation_date', None)
                dataset.metadata.shape = tuple(loom_file['matrix'].shape)

                tmp = list(loom_file['layers'].keys())
                dataset.metadata.layers_count = len(tmp)
                dataset.metadata.layers_names = tmp

                tmp = list(loom_file['row_attrs'].keys())
                dataset.metadata.row_attrs_count = len(tmp)
                dataset.metadata.row_attrs_names = tmp

                tmp = list(loom_file['col_attrs'].keys())
                dataset.metadata.col_attrs_count = len(tmp)
                dataset.metadata.col_attrs_names = tmp

                tmp = list(loom_file['col_graphs'].keys())
                dataset.metadata.col_graphs_count = len(tmp)
                dataset.metadata.col_graphs_names = tmp

                tmp = list(loom_file['row_graphs'].keys())
                dataset.metadata.row_graphs_count = len(tmp)
                dataset.metadata.row_graphs_names = tmp
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)


class GmxBinary(Binary):
    """
    Base class for GROMACS binary files - xtc, trr, cpt
    """

    magic_number = None  # variables to be overwritten in the child class
    file_ext = ""

    def sniff(self, filename):
        # The first 4 bytes of any GROMACS binary file containing the magic number
        try:
            header = open(filename, 'rb').read(struct.calcsize('>1i'))
            if struct.unpack('>1i', header)[0] == self.magic_number:
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary GROMACS %s file" % (self.file_ext)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary GROMACS %s trajectory file (%s)" % (self.file_ext, nice_size(dataset.get_size()))


class Trr(GmxBinary):
    """
    Class describing an trr file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.trr')
    >>> Trr().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Trr().sniff(fname)
    False
    """

    file_ext = "trr"
    magic_number = 1993  # magic number reference: https://github.com/gromacs/gromacs/blob/1c6639f0636d2ffc3d665686756d77227c8ae6d1/src/gromacs/fileio/trrio.cpp


class Cpt(GmxBinary):
    """
    Class describing a checkpoint (.cpt) file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.cpt')
    >>> Cpt().sniff(fname)
    True
    >>> fname = get_test_fname('md.trr')
    >>> Cpt().sniff(fname)
    False
    """

    file_ext = "cpt"
    magic_number = 171817  # magic number reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/checkpoint.cpp


class Xtc(GmxBinary):
    """
    Class describing an xtc file from the GROMACS suite

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('md.xtc')
    >>> Xtc().sniff(fname)
    True
    >>> fname = get_test_fname('md.trr')
    >>> Xtc().sniff(fname)
    False
    """

    file_ext = "xtc"
    magic_number = 1995  # reference: https://github.com/gromacs/gromacs/blob/cec211b2c835ba6e8ea849fb1bf67d7fc19693a4/src/gromacs/fileio/xtcio.cpp


class Biom2(H5):
    """
    Class describing a biom2 file (http://biom-format.org/documentation/biom_format.html)
    """
    MetadataElement(name="id", default=None, desc="table id", readonly=True, visible=True, no_value=None)
    MetadataElement(name="format_url", default=None, desc="format-url", readonly=True, visible=True, no_value=None)
    MetadataElement(name="format_version", default=None, desc="format-version", readonly=True, visible=True, no_value=None)
    MetadataElement(name="format", default=None, desc="format", readonly=True, visible=True, no_value=None)
    MetadataElement(name="type", default=None, desc="table type", readonly=True, visible=True, no_value=None)
    MetadataElement(name="generated_by", default=None, desc="generated by", readonly=True, visible=True, no_value=None)
    MetadataElement(name="creation_date", default=None, desc="creation date", readonly=True, visible=True, no_value=None)
    MetadataElement(name="nnz", default=-1, desc="nnz: The number of non-zero elements in the table", readonly=True, visible=True, no_value=-1)
    MetadataElement(name="shape", default=(), desc="shape: The number of rows and columns in the dataset", readonly=True, visible=True, no_value=())

    file_ext = "biom2"
    edam_format = "format_3746"

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
        >>> Biom2().sniff(fname)
        True
        >>> fname = get_test_fname('test.mz5')
        >>> Biom2().sniff(fname)
        False
        >>> fname = get_test_fname('wiggle.wig')
        >>> Biom2().sniff(fname)
        False
        """
        if super(Biom2, self).sniff(filename):
            try:
                f = h5py.File(filename)
                attributes = list(dict(f.attrs.items()))
                required_fields = ['id', 'format-url', 'type', 'generated-by', 'creation-date', 'nnz', 'shape']
                return set(required_fields).issubset(attributes)
            except Exception:
                return False
        return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(Biom2, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            f = h5py.File(dataset.file_name)
            attributes = dict(f.attrs.items())

            dataset.metadata.id = attributes['id']
            dataset.metadata.format_url = attributes['format-url']
            if 'format-version' in attributes:  # biom 2.1
                dataset.metadata.format_version = '.'.join(map(str, list(attributes['format-version'])))
            elif 'format' in attributes:  # biom 2.0
                dataset.metadata.format = attributes['format']
            dataset.metadata.type = attributes['type']
            dataset.metadata.shape = tuple(attributes['shape'])
            dataset.metadata.generated_by = attributes['generated-by']
            dataset.metadata.creation_date = attributes['creation-date']
            dataset.metadata.nnz = int(attributes['nnz'])

        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            lines = ['Biom2 (HDF5) file']
            try:
                f = h5py.File(dataset.file_name)
                for k, v in dict(f.attrs).items():
                    lines.append('%s:  %s' % (k, v))
            except Exception as e:
                log.warning('%s, set_peek Exception: %s', self, e)
            dataset.peek = '\n'.join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Biom2 (HDF5) file (%s)" % (nice_size(dataset.get_size()))


class Cool(H5):
    """
    Class describing the cool format (https://github.com/mirnylab/cooler)
    """

    file_ext = "cool"

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('matrix.cool')
        >>> Cool().sniff(fname)
        True
        >>> fname = get_test_fname('test.mz5')
        >>> Cool().sniff(fname)
        False
        >>> fname = get_test_fname('wiggle.wig')
        >>> Cool().sniff(fname)
        False
        >>> fname = get_test_fname('biom2_sparse_otu_table_hdf5.biom2')
        >>> Cool().sniff(fname)
        False
        """

        MAGIC = "HDF5::Cooler"
        URL = "https://github.com/mirnylab/cooler"

        if super(Cool, self).sniff(filename):
            keys = ['chroms', 'bins', 'pixels', 'indexes']
            with h5py.File(filename, 'r') as handle:
                fmt = handle.attrs.get('format', None)
                url = handle.attrs.get('format-url', None)
                if fmt == MAGIC or url == URL:
                    if not all(name in handle.keys() for name in keys):
                        return False
                    return True
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Cool (HDF5) file for storing genomic interaction data."
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Cool (HDF5) file (%s)." % (nice_size(dataset.get_size()))


class Scf(Binary):
    """Class describing an scf binary sequence file"""
    edam_format = "format_1632"
    edam_data = "data_0924"
    file_ext = "scf"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary scf sequence file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary scf sequence file (%s)" % (nice_size(dataset.get_size()))


class Sff(Binary):
    """ Standard Flowgram Format (SFF) """
    edam_format = "format_3284"
    edam_data = "data_0924"
    file_ext = "sff"

    def sniff(self, filename):
        # The first 4 bytes of any sff file is '.sff', and the file is binary. For details
        # about the format, see http://www.ncbi.nlm.nih.gov/Traces/trace.cgi?cmd=show&f=formats&m=doc&s=format
        try:
            header = open(filename, 'rb').read(4)
            if header == b'.sff':
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary sff file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary sff file (%s)" % (nice_size(dataset.get_size()))


class BigWig(Binary):
    """
    Accessing binary BigWig files from UCSC.
    The supplemental info in the paper has the binary details:
    http://bioinformatics.oxfordjournals.org/cgi/content/abstract/btq351v1
    """
    edam_format = "format_3006"
    edam_data = "data_3002"
    file_ext = "bigwig"
    track_type = "LineTrack"
    data_sources = {"data_standalone": "bigwig"}

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = 0x888FFC26
        self._name = "BigWig"

    def _unpack(self, pattern, handle):
        return struct.unpack(pattern, handle.read(struct.calcsize(pattern)))

    def sniff(self, filename):
        try:
            magic = self._unpack("I", open(filename, 'rb'))
            return magic[0] == self._magic
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary UCSC %s file" % self._name
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary UCSC %s file (%s)" % (self._name, nice_size(dataset.get_size()))


class BigBed(BigWig):
    """BigBed support from UCSC."""
    edam_format = "format_3004"
    edam_data = "data_3002"
    file_ext = "bigbed"
    data_sources = {"data_standalone": "bigbed"}

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = 0x8789F2EB
        self._name = "BigBed"


class TwoBit(Binary):
    """Class describing a TwoBit format nucleotide file"""
    edam_format = "format_3009"
    edam_data = "data_0848"
    file_ext = "twobit"

    def sniff(self, filename):
        try:
            # All twobit files start with a 16-byte header. If the file is smaller than 16 bytes, it's obviously not a valid twobit file.
            if os.path.getsize(filename) < 16:
                return False
            header = open(filename, 'rb').read(TWOBIT_MAGIC_SIZE)
            magic = struct.unpack(">L", header)[0]
            if magic == TWOBIT_MAGIC_NUMBER or magic == TWOBIT_MAGIC_NUMBER_SWAP:
                return True
        except IOError:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary TwoBit format nucleotide file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            return super(TwoBit, self).set_peek(dataset)

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary TwoBit format nucleotide file (%s)" % (nice_size(dataset.get_size()))


@dataproviders.decorators.has_dataproviders
class SQlite(Binary):
    """Class describing a Sqlite database """
    MetadataElement(name="tables", default=[], param=ListParameter, desc="Database Tables", readonly=True, visible=True, no_value=[])
    MetadataElement(name="table_columns", default={}, param=DictParameter, desc="Database Table Columns", readonly=True, visible=True, no_value={})
    MetadataElement(name="table_row_count", default={}, param=DictParameter, desc="Database Table Row Count", readonly=True, visible=True, no_value={})
    file_ext = "sqlite"
    edam_format = "format_3621"

    def init_meta(self, dataset, copy_from=None):
        Binary.init_meta(self, dataset, copy_from=copy_from)

    def set_meta(self, dataset, overwrite=True, **kwd):
        try:
            tables = []
            columns = dict()
            rowcounts = dict()
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name"
            rslt = c.execute(tables_query).fetchall()
            for table, _ in rslt:
                tables.append(table)
                try:
                    col_query = 'SELECT * FROM %s LIMIT 0' % table
                    cur = conn.cursor().execute(col_query)
                    cols = [col[0] for col in cur.description]
                    columns[table] = cols
                except Exception as exc:
                    log.warning('%s, set_meta Exception: %s', self, exc)
            for table in tables:
                try:
                    row_query = "SELECT count(*) FROM %s" % table
                    rowcounts[table] = c.execute(row_query).fetchone()[0]
                except Exception as exc:
                    log.warning('%s, set_meta Exception: %s', self, exc)
            dataset.metadata.tables = tables
            dataset.metadata.table_columns = columns
            dataset.metadata.table_row_count = rowcounts
        except Exception as exc:
            log.warning('%s, set_meta Exception: %s', self, exc)

    def sniff(self, filename):
        # The first 16 bytes of any SQLite3 database file is 'SQLite format 3\0', and the file is binary. For details
        # about the format, see http://www.sqlite.org/fileformat.html
        try:
            header = open(filename, 'rb').read(16)
            if header == b'SQLite format 3\0':
                return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "SQLite Database"
            lines = ['SQLite Database']
            if dataset.metadata.tables:
                for table in dataset.metadata.tables:
                    try:
                        lines.append('%s [%s]' % (table, dataset.metadata.table_row_count[table]))
                    except Exception:
                        continue
            dataset.peek = '\n'.join(lines)
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "SQLite Database (%s)" % (nice_size(dataset.get_size()))

    @dataproviders.decorators.dataprovider_factory('sqlite', dataproviders.dataset.SQliteDataProvider.settings)
    def sqlite_dataprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataProvider(dataset_source, **settings)

    @dataproviders.decorators.dataprovider_factory('sqlite-table', dataproviders.dataset.SQliteDataTableProvider.settings)
    def sqlite_datatableprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataTableProvider(dataset_source, **settings)

    @dataproviders.decorators.dataprovider_factory('sqlite-dict', dataproviders.dataset.SQliteDataDictProvider.settings)
    def sqlite_datadictprovider(self, dataset, **settings):
        dataset_source = dataproviders.dataset.DatasetDataProvider(dataset)
        return dataproviders.dataset.SQliteDataDictProvider(dataset_source, **settings)


class GeminiSQLite(SQlite):
    """Class describing a Gemini Sqlite database """
    MetadataElement(name="gemini_version", default='0.10.0', param=MetadataParameter, desc="Gemini Version",
                    readonly=True, visible=True, no_value='0.10.0')
    file_ext = "gemini.sqlite"
    edam_format = "format_3622"
    edam_data = "data_3498"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(GeminiSQLite, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT version FROM version"
            result = c.execute(tables_query).fetchall()
            for version, in result:
                dataset.metadata.gemini_version = version
            # TODO: Can/should we detect even more attributes, such as use of PED file, what was input annotation type, etc.
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        if super(GeminiSQLite, self).sniff(filename):
            gemini_table_names = ["gene_detailed", "gene_summary", "resources", "sample_genotype_counts", "sample_genotypes", "samples",
                                  "variant_impacts", "variants", "version"]
            try:
                conn = sqlite.connect(filename)
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute(tables_query).fetchall()
                result = [_[0] for _ in result]
                for table_name in gemini_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Gemini SQLite Database, version %s" % (dataset.metadata.gemini_version or 'unknown')
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Gemini SQLite Database, version %s" % (dataset.metadata.gemini_version or 'unknown')


class CuffDiffSQlite(SQlite):
    """Class describing a CuffDiff SQLite database """
    MetadataElement(name="cuffdiff_version", default='2.2.1', param=MetadataParameter, desc="CuffDiff Version",
                    readonly=True, visible=True, no_value='2.2.1')
    MetadataElement(name="genes", default=[], param=MetadataParameter, desc="Genes",
                    readonly=True, visible=True, no_value=[])
    MetadataElement(name="samples", default=[], param=MetadataParameter, desc="Samples",
                    readonly=True, visible=True, no_value=[])
    file_ext = "cuffdiff.sqlite"
    # TODO: Update this when/if there is a specific EDAM format for CuffDiff SQLite data.
    edam_format = "format_3621"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(CuffDiffSQlite, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            genes = []
            samples = []
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT value FROM runInfo where param = 'version'"
            result = c.execute(tables_query).fetchall()
            for version, in result:
                dataset.metadata.cuffdiff_version = version
            genes_query = 'SELECT gene_id, gene_short_name FROM genes ORDER BY gene_short_name'
            result = c.execute(genes_query).fetchall()
            for gene_id, gene_name in result:
                if gene_name is None:
                    continue
                gene = '%s: %s' % (gene_id, gene_name)
                if gene not in genes:
                    genes.append(gene)
            samples_query = 'SELECT DISTINCT(sample_name) as sample_name FROM samples ORDER BY sample_name'
            result = c.execute(samples_query).fetchall()
            for sample_name, in result:
                if sample_name not in samples:
                    samples.append(sample_name)
            dataset.metadata.genes = genes
            dataset.metadata.samples = samples
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        if super(CuffDiffSQlite, self).sniff(filename):
            # These tables should be in any CuffDiff SQLite output.
            cuffdiff_table_names = ['CDS', 'genes', 'isoforms', 'replicates',
                                    'runInfo', 'samples', 'TSS']
            try:
                conn = sqlite.connect(filename)
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute(tables_query).fetchall()
                result = [_[0] for _ in result]
                for table_name in cuffdiff_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "CuffDiff SQLite Database, version %s" % (dataset.metadata.cuffdiff_version or 'unknown')
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "CuffDiff SQLite Database, version %s" % (dataset.metadata.gemini_version or 'unknown')


class MzSQlite(SQlite):
    """Class describing a Proteomics Sqlite database """
    file_ext = "mz.sqlite"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(MzSQlite, self).set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super(MzSQlite, self).sniff(filename):
            mz_table_names = ["DBSequence", "Modification", "Peaks", "Peptide", "PeptideEvidence", "Score", "SearchDatabase", "Source", "SpectraData", "Spectrum", "SpectrumIdentification"]
            try:
                conn = sqlite.connect(filename)
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute(tables_query).fetchall()
                result = [_[0] for _ in result]
                for table_name in mz_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False


class BlibSQlite(SQlite):
    """Class describing a Proteomics Spectral Library Sqlite database """
    MetadataElement(name="blib_version", default='1.8', param=MetadataParameter, desc="Blib Version",
                    readonly=True, visible=True, no_value='1.8')
    file_ext = "blib"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(BlibSQlite, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            tables_query = "SELECT majorVersion,minorVersion FROM LibInfo"
            (majorVersion, minorVersion) = c.execute(tables_query).fetchall()[0]
            dataset.metadata.blib_version = '%s.%s' % (majorVersion, minorVersion)
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        if super(BlibSQlite, self).sniff(filename):
            blib_table_names = ['IonMobilityTypes', 'LibInfo', 'Modifications', 'RefSpectra', 'RefSpectraPeakAnnotations', 'RefSpectraPeaks', 'ScoreTypes', 'SpectrumSourceFiles']
            try:
                conn = sqlite.connect(filename)
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute(tables_query).fetchall()
                result = [_[0] for _ in result]
                for table_name in blib_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False


class IdpDB(SQlite):
    """
    Class describing an IDPicker 3 idpDB (sqlite) database

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.idpdb')
    >>> IdpDB().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> IdpDB().sniff(fname)
    False
    """
    file_ext = "idpdb"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(IdpDB, self).set_meta(dataset, overwrite=overwrite, **kwd)

    def sniff(self, filename):
        if super(IdpDB, self).sniff(filename):
            mz_table_names = ["About", "Analysis", "AnalysisParameter", "PeptideSpectrumMatch", "Spectrum", "SpectrumSource"]
            try:
                conn = sqlite.connect(filename)
                c = conn.cursor()
                tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                result = c.execute(tables_query).fetchall()
                result = [_[0] for _ in result]
                for table_name in mz_table_names:
                    if table_name not in result:
                        return False
                return True
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "IDPickerDB SQLite file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "IDPickerDB SQLite file (%s)" % (nice_size(dataset.get_size()))


class GAFASQLite(SQlite):
    """Class describing a GAFA SQLite database"""
    MetadataElement(name='gafa_schema_version', default='0.3.0', param=MetadataParameter, desc='GAFA schema version',
                    readonly=True, visible=True, no_value='0.3.0')
    file_ext = 'gafa.sqlite'

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(GAFASQLite, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            conn = sqlite.connect(dataset.file_name)
            c = conn.cursor()
            version_query = 'SELECT version FROM meta'
            results = c.execute(version_query).fetchall()
            if len(results) == 0:
                raise Exception('version not found in meta table')
            elif len(results) > 1:
                raise Exception('Multiple versions found in meta table')
            dataset.metadata.gafa_schema_version = results[0][0]
        except Exception as e:
            log.warn("%s, set_meta Exception: %s", self, e)

    def sniff(self, filename):
        if super(GAFASQLite, self).sniff(filename):
            gafa_table_names = frozenset(['gene', 'gene_family', 'gene_family_member', 'meta', 'transcript'])
            conn = sqlite.connect(filename)
            c = conn.cursor()
            tables_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            results = c.execute(tables_query).fetchall()
            found_table_names = frozenset(_[0] for _ in results)
            return gafa_table_names <= found_table_names
        return False


class Xlsx(Binary):
    """Class for Excel 2007 (xlsx) files"""
    file_ext = "xlsx"
    compressed = True

    def sniff(self, filename):
        # Xlsx is compressed in zip format and must not be uncompressed in Galaxy.
        try:
            if zipfile.is_zipfile(filename):
                tempzip = zipfile.ZipFile(filename)
                if "[Content_Types].xml" in tempzip.namelist() and tempzip.read("[Content_Types].xml").find(b'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml') != -1:
                    return True
            return False
        except Exception:
            return False


class ExcelXls(Binary):
    """Class describing an Excel (xls) file"""
    file_ext = "excel.xls"
    edam_format = "format_3468"

    def sniff(self, filename):
        mime_type = subprocess.check_output(['file', '--mime-type', filename])
        return b"application/vnd.ms-excel" in mime_type

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'application/vnd.ms-excel'

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Microsoft Excel XLS file"
            dataset.blurb = data.nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Microsoft Excel XLS file (%s)" % (data.nice_size(dataset.get_size()))


class Sra(Binary):
    """ Sequence Read Archive (SRA) datatype originally from mdshw5/sra-tools-galaxy"""
    file_ext = 'sra'

    def sniff(self, filename):
        """ The first 8 bytes of any NCBI sra file is 'NCBI.sra', and the file is binary.
        For details about the format, see http://www.ncbi.nlm.nih.gov/books/n/helpsra/SRA_Overview_BK/#SRA_Overview_BK.4_SRA_Data_Structure
        """
        try:
            header = open(filename, 'rb').read(8)
            if header == b'NCBI.sra':
                return True
            else:
                return False
        except Exception:
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
        except Exception:
            return 'Binary sra file (%s)' % (nice_size(dataset.get_size()))


class RData(Binary):
    """Generic R Data file datatype implementation"""
    file_ext = 'rdata'

    def sniff(self, filename):
        rdata_header = b'RDX2\nX\n'
        try:
            header = open(filename, 'rb').read(7)
            if header == rdata_header:
                return True

            header = gzip.open(filename).read(7)
            if header == rdata_header:
                return True
        except Exception:
            return False


class OxliBinary(Binary):

    @staticmethod
    def _sniff(filename, oxlitype):
        try:
            with open(filename, 'rb') as fileobj:
                header = fileobj.read(4)
                if header == b'OXLI':
                    fileobj.read(1)  # skip the version number
                    ftype = fileobj.read(1)
                    if binascii.hexlify(ftype) == oxlitype:
                        return True
            return False
        except IOError:
            return False


class OxliCountGraph(OxliBinary):
    """
    OxliCountGraph starts with "OXLI" + one byte version number +
    8-bit binary '1'
    Test file generated via::

        load-into-counting.py --n_tables 1 --max-tablesize 1 \\
            oxli_countgraph.oxlicg khmer/tests/test-data/100-reads.fq.bz2

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliCountGraph().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_countgraph.oxlicg")
    >>> OxliCountGraph().sniff(fname)
    True
    """
    file_ext = 'oxlicg'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"01")


class OxliNodeGraph(OxliBinary):
    """
    OxliNodeGraph starts with "OXLI" + one byte version number +
    8-bit binary '2'
    Test file generated via::

        load-graph.py --n_tables 1 --max-tablesize 1 oxli_nodegraph.oxling \\
            khmer/tests/test-data/100-reads.fq.bz2

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliNodeGraph().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_nodegraph.oxling")
    >>> OxliNodeGraph().sniff(fname)
    True
    """
    file_ext = 'oxling'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"02")


class OxliTagSet(OxliBinary):
    """
    OxliTagSet starts with "OXLI" + one byte version number +
    8-bit binary '3'
    Test file generated via::

        load-graph.py --n_tables 1 --max-tablesize 1 oxli_nodegraph.oxling \\
            khmer/tests/test-data/100-reads.fq.bz2;
        mv oxli_nodegraph.oxling.tagset oxli_tagset.oxlits

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliTagSet().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_tagset.oxlits")
    >>> OxliTagSet().sniff(fname)
    True
    """
    file_ext = 'oxlits'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"03")


class OxliStopTags(OxliBinary):
    """
    OxliStopTags starts with "OXLI" + one byte version number +
    8-bit binary '4'
    Test file adapted from khmer 2.0's
    "khmer/tests/test-data/goodversion-k32.stoptags"

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliStopTags().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_stoptags.oxlist")
    >>> OxliStopTags().sniff(fname)
    True
    """
    file_ext = 'oxlist'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"04")


class OxliSubset(OxliBinary):
    """
    OxliSubset starts with "OXLI" + one byte version number +
    8-bit binary '5'
    Test file generated via::

        load-graph.py -k 20 example tests/test-data/random-20-a.fa;
        partition-graph.py example;
        mv example.subset.0.pmap oxli_subset.oxliss

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliSubset().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_subset.oxliss")
    >>> OxliSubset().sniff(fname)
    True
    """
    file_ext = 'oxliss'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"05")


class OxliGraphLabels(OxliBinary):
    """
    OxliGraphLabels starts with "OXLI" + one byte version number +
    8-bit binary '6'
    Test file generated via::

        python -c "from khmer import GraphLabels; \\
            gl = GraphLabels(20, 1e7, 4); \\
            gl.consume_fasta_and_tag_with_labels('tests/test-data/test-labels.fa'); \\
            gl.save_labels_and_tags('oxli_graphlabels.oxligl')"

    using khmer 2.0

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('sequence.csfasta')
    >>> OxliGraphLabels().sniff(fname)
    False
    >>> fname = get_test_fname("oxli_graphlabels.oxligl")
    >>> OxliGraphLabels().sniff(fname)
    True
    """
    file_ext = 'oxligl'

    def sniff(self, filename):
        return OxliBinary._sniff(filename, b"06")


class PostgresqlArchive(CompressedArchive):
    """
    Class describing a Postgresql database packed into a tar archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('postgresql_fake.tar.bz2')
    >>> PostgresqlArchive().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar')
    >>> PostgresqlArchive().sniff(fname)
    False
    """
    MetadataElement(name="version", default=None, param=MetadataParameter, desc="PostgreSQL database version",
                    readonly=True, visible=True, no_value=None)
    file_ext = "postgresql"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(PostgresqlArchive, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and tarfile.is_tarfile(dataset.file_name):
                with tarfile.open(dataset.file_name, 'r') as temptar:
                    pg_version_file = temptar.extractfile('postgresql/db/PG_VERSION')
                    dataset.metadata.version = pg_version_file.read().strip()
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        if filename and tarfile.is_tarfile(filename):
            try:
                with tarfile.open(filename, 'r') as temptar:
                    return 'postgresql/db/PG_VERSION' in temptar.getnames()
            except Exception as e:
                log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "PostgreSQL Archive (%s)" % (nice_size(dataset.get_size()))
            dataset.blurb = "PostgreSQL version %s" % (dataset.metadata.version or 'unknown')
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "PostgreSQL Archive (%s)" % (nice_size(dataset.get_size()))


class Fast5Archive(CompressedArchive):
    """
    Class describing a FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5Archive().sniff(fname)
    True
    """
    MetadataElement(name="fast5_count", default='0', param=MetadataParameter, desc="Read Count",
                    readonly=True, visible=True, no_value=None)
    file_ext = "fast5.tar"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(Fast5Archive, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and tarfile.is_tarfile(dataset.file_name):
                with tarfile.open(dataset.file_name, 'r') as temptar:
                    dataset.metadata.fast5_count = sum(
                        1 for f in temptar if f.name.endswith('.fast5')
                    )
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        try:
            if filename and tarfile.is_tarfile(filename):
                with tarfile.open(filename, 'r') as temptar:
                    for f in temptar:
                        if not f.isfile():
                            continue
                        if f.name.endswith('.fast5'):
                            return True
                        else:
                            return False
        except Exception as e:
            log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "FAST5 Archive (%s)" % (nice_size(dataset.get_size()))
            dataset.blurb = "%s sequences" % (dataset.metadata.fast5_count or 'unknown')
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "FAST5 Archive (%s)" % (nice_size(dataset.get_size()))


class Fast5ArchiveGz(Fast5Archive):
    """
    Class describing a gzip-compressed FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar.gz')
    >>> Fast5ArchiveGz().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar.bz2')
    >>> Fast5ArchiveGz().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5ArchiveGz().sniff(fname)
    False
    """
    file_ext = "fast5.tar.gz"

    def sniff(self, filename):
        if not is_gzip(filename):
            return False
        return Fast5Archive.sniff(self, filename)


class Fast5ArchiveBz2(Fast5Archive):
    """
    Class describing a bzip2-compressed FAST5 archive

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.fast5.tar.bz2')
    >>> Fast5ArchiveBz2().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar.gz')
    >>> Fast5ArchiveBz2().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> Fast5ArchiveBz2().sniff(fname)
    False
    """
    file_ext = "fast5.tar.bz2"

    def sniff(self, filename):
        if not is_bz2(filename):
            return False
        return Fast5Archive.sniff(self, filename)


class SearchGuiArchive(CompressedArchive):
    """Class describing a SearchGUI archive """
    MetadataElement(name="searchgui_version", default='1.28.0', param=MetadataParameter, desc="SearchGui Version",
                    readonly=True, visible=True, no_value=None)
    MetadataElement(name="searchgui_major_version", default='1', param=MetadataParameter, desc="SearchGui Major Version",
                    readonly=True, visible=True, no_value=None)
    file_ext = "searchgui_archive"

    def set_meta(self, dataset, overwrite=True, **kwd):
        super(SearchGuiArchive, self).set_meta(dataset, overwrite=overwrite, **kwd)
        try:
            if dataset and zipfile.is_zipfile(dataset.file_name):
                with zipfile.ZipFile(dataset.file_name) as tempzip:
                    if 'searchgui.properties' in tempzip.namelist():
                        with tempzip.open('searchgui.properties') as fh:
                            for line in fh:
                                if line.startswith('searchgui.version'):
                                    version = line.split('=')[1].strip()
                                    dataset.metadata.searchgui_version = version
                                    dataset.metadata.searchgui_major_version = version.split('.')[0]
        except Exception as e:
            log.warning('%s, set_meta Exception: %s', self, e)

    def sniff(self, filename):
        try:
            if filename and zipfile.is_zipfile(filename):
                with zipfile.ZipFile(filename, 'r') as tempzip:
                    is_searchgui = 'searchgui.properties' in tempzip.namelist()
                return is_searchgui
        except Exception as e:
            log.warning('%s, sniff Exception: %s', self, e)
        return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "SearchGUI Archive, version %s" % (dataset.metadata.searchgui_version or 'unknown')
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "SearchGUI Archive, version %s" % (dataset.metadata.searchgui_version or 'unknown')


class NetCDF(Binary):
    """Binary data in netCDF format"""
    file_ext = "netcdf"
    edam_format = "format_3650"
    edam_data = "data_0943"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary netCDF file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary netCDF file (%s)" % (nice_size(dataset.get_size()))

    def sniff(self, filename):
        try:
            with open(filename, 'rb') as f:
                header = f.read(3)
            if header == b'CDF':
                return True
            return False
        except Exception:
            return False


class Dcd(Binary):
    """
    Class describing a dcd file from the CHARMM molecular simulation program

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test_glucose_vacuum.dcd')
    >>> Dcd().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Dcd().sniff(fname)
    False
    """
    file_ext = "dcd"
    edam_data = "data_3842"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic_number = b'CORD'

    def sniff(self, filename):
        # Match the keyword 'CORD' at position 4 or 8 - intsize dependent
        # Not checking for endianness
        try:
            with open(filename, 'rb') as header:
                intsize = 4
                header.seek(intsize)
                if header.read(intsize) == self._magic_number:
                    return True
                else:
                    intsize = 8
                    header.seek(intsize)
                    if header.read(intsize) == self._magic_number:
                        return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary CHARMM/NAMD dcd file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary CHARMM/NAMD dcd file (%s)" % (nice_size(dataset.get_size()))


class Vel(Binary):
    """
    Class describing a velocity file from the CHARMM molecular simulation program

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test_charmm.vel')
    >>> Vel().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> Vel().sniff(fname)
    False
    """
    file_ext = "vel"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic_number = b'VELD'

    def sniff(self, filename):
        # Match the keyword 'VELD' at position 4 or 8 - intsize dependent
        # Not checking for endianness
        try:
            with open(filename, 'rb') as header:
                intsize = 4
                header.seek(intsize)
                if header.read(intsize) == self._magic_number:
                    return True
                else:
                    intsize = 8
                    header.seek(intsize)
                    if header.read(intsize) == self._magic_number:
                        return True
            return False
        except Exception:
            return False

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary CHARMM velocity file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "Binary CHARMM velocity file (%s)" % (nice_size(dataset.get_size()))


class DAA(Binary):
    """
    Class describing an DAA (diamond alignment archive) file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond.daa')
    >>> DAA().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> DAA().sniff(fname)
    False
    """
    file_ext = "daa"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = binascii.unhexlify("6be33e6d47530e3c")

    def sniff(self, filename):
        # The first 8 bytes of any daa file are 0x3c0e53476d3ee36b
        with open(filename, 'rb') as f:
            return f.read(8) == self._magic


class RMA6(Binary):
    """
    Class describing an RMA6 (MEGAN6 read-match archive) file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond.rma6')
    >>> RMA6().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> RMA6().sniff(fname)
    False
    """
    file_ext = "rma6"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = binascii.unhexlify("000003f600000006")

    def sniff(self, filename):
        # The first 8 bytes of any daa file are 0x3c0e53476d3ee36b
        with open(filename, 'rb') as f:
            return f.read(8) == self._magic


class DMND(Binary):
    """
    Class describing an DMND file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('diamond_db.dmnd')
    >>> DMND().sniff(fname)
    True
    >>> fname = get_test_fname('interval.interval')
    >>> DMND().sniff(fname)
    False
    """
    file_ext = "dmnd"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)
        self._magic = binascii.unhexlify("6d18ee15a4f84a02")

    def sniff(self, filename):
        # The first 8 bytes of any dmnd file are 0x24af8a415ee186d
        with open(filename, 'rb') as f:
            return f.read(8) == self._magic


class ICM(Binary):
    """
    Class describing an ICM (interpolated context model) file, used by Glimmer
    """
    file_ext = "icm"
    edam_data = "data_0950"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "Binary ICM (interpolated context model) file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def sniff(self, dataset):
        line = open(dataset).read(100)
        if '>ver = ' in line and 'len = ' in line and 'depth = ' in line and 'periodicity =' in line and 'nodes = ' in line:
            return True

        return False


class BafTar(CompressedArchive):
    """
    Base class for common behavior of tar files of directory-based raw file formats
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('brukerbaf.d.tar')
    >>> BafTar().sniff(fname)
    True
    >>> fname = get_test_fname('test.fast5.tar')
    >>> BafTar().sniff(fname)
    False
    """
    edam_data = "data_2536"  # mass spectrometry data
    edam_format = "format_3712"  # TODO: add more raw formats to EDAM?
    file_ext = "brukerbaf.d.tar"

    def get_signature_file(self):
        return "analysis.baf"

    def sniff(self, filename):
        if tarfile.is_tarfile(filename):
            with tarfile.open(filename) as rawtar:
                return self.get_signature_file() in [os.path.basename(f).lower() for f in rawtar.getnames()]
        return False

    def get_type(self):
        return "Bruker BAF directory archive"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = self.get_type()
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "%s (%s)" % (self.get_type(), nice_size(dataset.get_size()))


class YepTar(BafTar):
    """ A tar'd up .d directory containing Agilent/Bruker YEP format data """
    file_ext = "agilentbrukeryep.d.tar"

    def get_signature_file(self):
        return "analysis.yep"

    def get_type(self):
        return "Agilent/Bruker YEP directory archive"


class TdfTar(BafTar):
    """ A tar'd up .d directory containing Bruker TDF format data """
    file_ext = "brukertdf.d.tar"

    def get_signature_file(self):
        return "analysis.tdf"

    def get_type(self):
        return "Bruker TDF directory archive"


class MassHunterTar(BafTar):
    """ A tar'd up .d directory containing Agilent MassHunter format data """
    file_ext = "agilentmasshunter.d.tar"

    def get_signature_file(self):
        return "msscan.bin"

    def get_type(self):
        return "Agilent MassHunter directory archive"


class MassLynxTar(BafTar):
    """ A tar'd up .d directory containing Waters MassLynx format data """
    file_ext = "watersmasslynx.raw.tar"

    def get_signature_file(self):
        return "_func001.dat"

    def get_type(self):
        return "Waters MassLynx RAW directory archive"


class WiffTar(BafTar):
    """
    A tar'd up .wiff/.scan pair containing Sciex WIFF format data
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('some.wiff.tar')
    >>> WiffTar().sniff(fname)
    True
    >>> fname = get_test_fname('brukerbaf.d.tar')
    >>> WiffTar().sniff(fname)
    False
    >>> fname = get_test_fname('test.fast5.tar')
    >>> WiffTar().sniff(fname)
    False
    """
    file_ext = "wiff.tar"

    def sniff(self, filename):
        if tarfile.is_tarfile(filename):
            with tarfile.open(filename) as rawtar:
                return ".wiff" in [os.path.splitext(os.path.basename(f).lower())[1] for f in rawtar.getnames()]
        return False

    def get_type(self):
        return "Sciex WIFF/SCAN archive"


if __name__ == '__main__':
    import doctest
    doctest.testmod(sys.modules[__name__])
